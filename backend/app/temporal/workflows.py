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
        portfolio_deep_scan_activity,
        save_draft_proposal_activity,
        set_repo_status_activity,
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

        # Step 0: Mark repo as "drafting_docs" in DB (persistent state)
        if input.github_repo_id:
            await workflow.execute_activity(
                set_repo_status_activity,
                args=[input.github_repo_id, "drafting_docs"],
                start_to_close_timeout=timedelta(seconds=10),
            )

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

        # Step 6: Mark repo as "review_ready" in DB
        if input.github_repo_id:
            await workflow.execute_activity(
                set_repo_status_activity,
                args=[input.github_repo_id, "review_ready"],
                start_to_close_timeout=timedelta(seconds=10),
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
    repo_ids: list[int] | None = None
    bio: str = ""
    links_json: str = "{}"


@workflow.defn
class PortfolioWorkflow:
    def __init__(self) -> None:
        self._stage: str = "starting"
        self._total_repos: int = 0
        self._scanned: int = 0
        self._draft_readme: str | None = None
        self._errors: list[str] = []

    @workflow.query
    def get_status(self) -> dict:
        return {
            "stage": self._stage,
            "total_repos": self._total_repos,
            "scanned": self._scanned,
            "draft_readme": self._draft_readme,
            "errors": list(self._errors),
        }

    @workflow.run
    async def run(self, input: PortfolioInput) -> dict:
        import json as _json

        # Step 1: Resolving — fetch all repos, filter to selected IDs
        self._stage = "resolving"
        all_repos = await workflow.execute_activity(
            fetch_repos_extended_activity,
            args=[input.access_token],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
            ),
        )

        if input.repo_ids:
            selected_ids = set(input.repo_ids)
            selected_repos = [r for r in all_repos if r["id"] in selected_ids]
        else:
            # Fallback: auto-select top 4 non-fork repos by stars
            candidates = [r for r in all_repos if not r.get("fork", False)]
            candidates.sort(key=lambda r: (
                r.get("stargazers_count", 0),
                r.get("pushed_at") or "",
            ), reverse=True)
            selected_repos = candidates[:4]

        self._total_repos = len(selected_repos)

        if not selected_repos:
            self._stage = "failed"
            self._errors.append("No eligible repositories found")
            return {
                "status": "failure",
                "draft_readme": None,
                "errors": self._errors,
            }

        # Step 2: Scanning — deep scan each selected repo
        self._stage = "scanning"
        scanned_repos: list[dict] = []

        for repo in selected_repos:
            try:
                scan_result = await workflow.execute_activity(
                    portfolio_deep_scan_activity,
                    args=[repo["full_name"], input.access_token],
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(
                        maximum_attempts=2,
                        initial_interval=timedelta(seconds=5),
                    ),
                )
                scanned_repos.append(scan_result)
            except Exception as exc:
                self._errors.append(f"Scan failed for {repo['full_name']}: {str(exc)}")
                # Still include basic info so the repo shows up in the profile
                scanned_repos.append({
                    "full_name": repo["full_name"],
                    "name": repo.get("name", ""),
                    "description": repo.get("description", ""),
                    "html_url": repo.get("html_url", ""),
                    "language": repo.get("language", ""),
                    "stargazers_count": repo.get("stargazers_count", 0),
                    "forks_count": 0,
                    "topics": [],
                    "readme_content": "",
                    "dependencies": {},
                    "frameworks": [],
                })
            self._scanned += 1

        # Step 3: Generating — produce profile README with rich context
        self._stage = "generating"
        top_repos_json = _json.dumps(scanned_repos, default=str)
        readme_content = await workflow.execute_activity(
            generate_profile_readme_activity,
            args=[top_repos_json, input.username, input.bio, input.links_json],
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
            ),
        )

        # Step 4: Draft ready — store in workflow state, do NOT auto-publish
        self._stage = "draft_ready"
        self._draft_readme = readme_content

        return {
            "status": "draft_ready",
            "draft_readme": readme_content,
            "errors": self._errors,
        }
