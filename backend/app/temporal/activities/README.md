# backend/app/temporal/activities/

Temporal activities, split into focused per-concern modules (was a
single 948-LOC `activities.py` pre-E1).

## Modules

| Module | Owns | Key activities |
|---|---|---|
| `analysis.py` | Repo-health calculation + structure scanning | `analyze_repo_health`, `analyze_codebase_activity`, `deep_scan_repo`, `portfolio_deep_scan_activity` |
| `github.py` | GitHub API interactions (PRs, repo listing, status sync) | `fetch_repo_list_activity`, `fetch_repos_extended_activity`, `sync_pr_status_activity`, `create_pull_request_activity`, `create_docs_pull_request_activity`, `create_or_update_profile_repo_activity` |
| `generation.py` | LLM-driven content generation (READMEs, docs) | `generate_readme_activity`, `generate_deep_readme_activity`, `generate_doc_activity`, `generate_profile_readme_activity` |
| `persistence.py` | Database writes for activity state | `save_draft_proposal_activity`, `set_repo_status_activity`, `say_hello` (demo) |
| `portfolio.py` | Portfolio-specific scanning + framework detection | various portfolio activities |

## Backward compatibility

`__init__.py` re-exports every activity name, so callers that did
`from app.temporal.activities import analyze_repo_health` still work
exactly as before the split.

## Adding a new activity

1. Pick the right module (or create a new one for a new domain — e.g. `activities/notifications.py`).
2. Decorate with `@activity.defn` (from `temporalio import activity`).
3. Wrap the work body in `temporal_activity_context(workflow_id, "<activity_name>", repo_id=…, user_id=…)` so logs carry the context (see [`backend/README.md`](../../../README.md#logging)).
4. Add to `__init__.py`'s re-export list.
5. Register in `app/temporal/worker.py`'s `activities=[…]` list.
6. Reference from the workflow via `workflow.execute_activity(<name>, …)`.

## PyGithub is sync

GitHub API calls in `github.py` use PyGithub which is synchronous.
Always wrap them in `asyncio.to_thread()` to avoid blocking the
Temporal worker's event loop:

```python
import asyncio
from github import Github

async def my_github_activity(token: str, repo_id: int):
    g = Github(token)
    repo = await asyncio.to_thread(g.get_repo, repo_id)
    contents = await asyncio.to_thread(repo.get_contents, "README.md")
    return contents.decoded_content.decode()
```

## LiteLLM provider configuration

`generation.py` uses `llm_service.complete()` (defined in
`app/services/llm_service.py`). The model + provider are configurable
via env (`LITELLM_API_KEY`, `LITELLM_API_BASE`, `LLM_MODEL`) — don't
hardcode model names in activity code.
