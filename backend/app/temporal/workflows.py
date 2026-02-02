import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        analyze_codebase_activity,
        analyze_repo_health,
        create_docs_pull_request_activity,
        create_or_update_profile_repo_activity,
        create_pull_request_activity,
        deep_scan_repo,
        fetch_repo_list_activity,
        fetch_repos_extended_activity,
        generate_deep_readme_activity,
        generate_doc_activity,
        generate_profile_readme_activity,
        generate_readme_activity,
        get_repo_context_activity,
        save_draft_proposal_activity,
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
    github_repo_id: int = 0


@workflow.defn
class JanitorWorkflow:
    @workflow.run
    async def run(self, input: JanitorInput) -> dict:
        import json as _json

        repo_url = f"https://github.com/{input.repo_full_name}"

        # Step 1: Deep Scan — clone repo, map files, read key configs
        scan_result = await workflow.execute_activity(
            deep_scan_repo,
            args=[repo_url, input.access_token, input.github_repo_id],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
            ),
        )

        file_tree = scan_result["file_tree"]
        tech_stack_files = scan_result["tech_stack_files"]

        # Step 2: Analyze — produce a structured JSON summary of the codebase
        summary_json = await workflow.execute_activity(
            analyze_codebase_activity,
            args=[
                input.repo_full_name,
                input.description,
                file_tree,
                tech_stack_files,
            ],
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
            ),
        )

        # Step 3: Generate README
        doc_types = ["README"]
        doc_tasks = []
        for doc_type in doc_types:
            task = workflow.execute_activity(
                generate_doc_activity,
                args=[
                    summary_json,
                    doc_type,
                    input.repo_full_name,
                    file_tree,
                    tech_stack_files,
                ],
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=5),
                ),
            )
            doc_tasks.append(task)

        doc_results = await asyncio.gather(*doc_tasks)

        # Step 4: Aggregate — collect successes and failures
        files: dict[str, str] = {}
        errors: list[str] = []
        docs_generated: list[str] = []

        for result in doc_results:
            if result["error"]:
                errors.append(f"{result['doc_type']}: {result['error']}")
            else:
                files[result["filename"]] = result["content"]
                docs_generated.append(result["doc_type"])

        if not files:
            return {
                "status": "failure",
                "pr_url": None,
                "docs_generated": [],
                "errors": errors,
            }

        # Step 5: Save draft — persist to DB for human review (no auto-commit)
        files_json = _json.dumps(files)
        await workflow.execute_activity(
            save_draft_proposal_activity,
            args=[input.github_repo_id, files_json],
            start_to_close_timeout=timedelta(seconds=30),
        )

        status = "review_ready" if not errors else "partial_review_ready"
        return {
            "status": status,
            "docs_generated": docs_generated,
            "errors": errors,
        }


# ---------------------------------------------------------------------------
# Phase 14: Portfolio Architect
# ---------------------------------------------------------------------------

@dataclass
class PortfolioInput:
    access_token: str
    username: str


@workflow.defn
class PortfolioWorkflow:
    def __init__(self) -> None:
        self._stage: str = "starting"
        self._total_repos: int = 0
        self._analyzed: int = 0
        self._top_repos: list[dict] = []
        self._profile_url: str | None = None
        self._pr_url: str | None = None
        self._errors: list[str] = []

    @workflow.query
    def get_status(self) -> dict:
        return {
            "stage": self._stage,
            "total_repos": self._total_repos,
            "analyzed": self._analyzed,
            "top_repos": list(self._top_repos),
            "profile_url": self._profile_url,
            "pr_url": self._pr_url,
            "errors": list(self._errors),
        }

    @workflow.run
    async def run(self, input: PortfolioInput) -> dict:
        import json as _json

        # Step 1: Fetch all repos with extended metadata
        self._stage = "scanning"
        all_repos = await workflow.execute_activity(
            fetch_repos_extended_activity,
            args=[input.access_token],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
            ),
        )
        self._total_repos = len(all_repos)

        # Step 2: Batch health analysis in groups of 5
        self._stage = "analyzing"
        health_scores: dict[int, int] = {}
        batch_size = 5

        for i in range(0, len(all_repos), batch_size):
            batch = all_repos[i : i + batch_size]
            tasks = []
            for repo in batch:
                task = workflow.execute_activity(
                    analyze_repo_health,
                    args=[repo["full_name"], input.access_token],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(
                        maximum_attempts=2,
                        initial_interval=timedelta(seconds=3),
                    ),
                )
                tasks.append((repo["id"], task))

            for repo_id, task in tasks:
                try:
                    result = await task
                    health_scores[repo_id] = result.get("health_score", 0)
                except Exception as exc:
                    health_scores[repo_id] = 0
                    self._errors.append(f"Analysis failed for repo {repo_id}: {str(exc)}")
                self._analyzed += 1

        # Step 3: Selection algorithm — filter forks, sort, pick top 4
        self._stage = "selecting"
        candidates = [r for r in all_repos if not r.get("fork", False)]

        # Sort descending by: health_score, stargazers, recency
        candidates.sort(key=lambda r: (
            health_scores.get(r["id"], 0),
            r.get("stargazers_count", 0),
            r.get("pushed_at") or "",
        ), reverse=True)

        top_4 = candidates[:4]
        # Enrich with health scores
        for repo in top_4:
            repo["health_score"] = health_scores.get(repo["id"], 0)
        self._top_repos = top_4

        if not top_4:
            self._stage = "failed"
            return {
                "status": "failure",
                "profile_url": None,
                "pr_url": None,
                "top_repos": [],
                "errors": ["No eligible repositories found"],
            }

        # Step 4: Generate profile README
        self._stage = "generating"
        top_repos_json = _json.dumps(top_4, default=str)
        readme_content = await workflow.execute_activity(
            generate_profile_readme_activity,
            args=[top_repos_json, input.username],
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
            ),
        )

        # Step 5: Create or update the profile repo
        self._stage = "publishing"
        result = await workflow.execute_activity(
            create_or_update_profile_repo_activity,
            args=[input.username, readme_content, input.access_token],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
            ),
        )

        self._profile_url = result["profile_url"]
        self._pr_url = result.get("pr_url")
        self._stage = "complete"

        return {
            "status": "success",
            "profile_url": result["profile_url"],
            "pr_url": result.get("pr_url"),
            "top_repos": [r["full_name"] for r in top_4],
            "errors": self._errors,
        }
