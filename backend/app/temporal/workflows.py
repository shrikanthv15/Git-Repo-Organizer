import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        analyze_repo_health,
        create_pull_request_activity,
        fetch_repo_list_activity,
        generate_readme_activity,
        get_repo_context_activity,
        say_hello,
    )


# ---------------------------------------------------------------------------
# Phase 2: Greeting
# ---------------------------------------------------------------------------

@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            say_hello,
            name,
            start_to_close_timeout=timedelta(seconds=5),
        )


# ---------------------------------------------------------------------------
# Phase 4: Single Repo Analysis
# ---------------------------------------------------------------------------

@dataclass
class AnalysisInput:
    repo_full_name: str
    access_token: str


@workflow.defn
class AnalysisWorkflow:
    @workflow.run
    async def run(self, input: AnalysisInput) -> dict:
        return await workflow.execute_activity(
            analyze_repo_health,
            args=[input.repo_full_name, input.access_token],
            start_to_close_timeout=timedelta(seconds=30),
        )


# ---------------------------------------------------------------------------
# Phase 5: Batch Gardening
# ---------------------------------------------------------------------------

@dataclass
class BatchGardeningInput:
    access_token: str
    limit: int = 5


@workflow.defn
class BatchGardeningWorkflow:
    def __init__(self) -> None:
        self._total: int = 0
        self._completed: int = 0
        self._results: list[dict] = []

    @workflow.query
    def get_status(self) -> dict:
        return {
            "total": self._total,
            "completed": self._completed,
            "results": list(self._results),
        }

    async def _run_child(self, repo_full_name: str, access_token: str) -> None:
        try:
            result = await workflow.execute_child_workflow(
                AnalysisWorkflow.run,
                AnalysisInput(
                    repo_full_name=repo_full_name,
                    access_token=access_token,
                ),
                id=f"batch-child-{repo_full_name}-{workflow.uuid4()}",
            )
            self._results.append(result)
        except Exception:
            self._results.append({
                "repo_name": repo_full_name,
                "health_score": 0,
                "issues": ["Analysis failed"],
                "last_commit_date": datetime.now(timezone.utc).isoformat(),
            })
        finally:
            self._completed += 1

    @workflow.run
    async def run(self, input: BatchGardeningInput) -> list[dict]:
        repos = await workflow.execute_activity(
            fetch_repo_list_activity,
            args=[input.access_token, input.limit],
            start_to_close_timeout=timedelta(seconds=30),
        )

        self._total = len(repos)

        tasks = [
            self._run_child(repo["full_name"], input.access_token)
            for repo in repos
        ]
        await asyncio.gather(*tasks)

        return list(self._results)


# ---------------------------------------------------------------------------
# Phase 6: Janitor (README generation + PR)
# ---------------------------------------------------------------------------

@dataclass
class JanitorInput:
    repo_full_name: str
    access_token: str
    description: str = ""


@workflow.defn
class JanitorWorkflow:
    @workflow.run
    async def run(self, input: JanitorInput) -> dict:
        # Step 1: Read — get the file tree
        file_structure = await workflow.execute_activity(
            get_repo_context_activity,
            args=[input.repo_full_name, input.access_token],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Step 2: Think — generate README via LLM
        readme_content = await workflow.execute_activity(
            generate_readme_activity,
            args=[input.repo_full_name, file_structure, input.description],
            start_to_close_timeout=timedelta(seconds=60),
        )

        # Step 3: Act — create branch, commit, and open PR
        pr_url = await workflow.execute_activity(
            create_pull_request_activity,
            args=[input.repo_full_name, readme_content, input.access_token],
            start_to_close_timeout=timedelta(seconds=30),
        )

        return {"status": "success", "pr_url": pr_url}
