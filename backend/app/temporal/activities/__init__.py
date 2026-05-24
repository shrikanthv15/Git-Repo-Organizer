# Re-export all activities for backwards compatibility.
# This allows callers to continue using:
#   from app.temporal.activities import analyze_repo_health
# instead of:
#   from app.temporal.activities.analysis import analyze_repo_health

from app.temporal.activities.analysis import (
    analyze_repo_health,
    deep_scan_repo,
    get_repo_context_activity,
    say_hello,
)
from app.temporal.activities.github import (
    create_or_update_profile_repo_activity,
    create_pull_request_activity,
    fetch_repo_list_activity,
    fetch_repos_extended_activity,
    sync_pr_status_activity,
)
from app.temporal.activities.generation import (
    analyze_codebase_activity,
    generate_deep_readme_activity,
    generate_doc_activity,
    generate_profile_readme_activity,
    generate_readme_activity,
)
from app.temporal.activities.persistence import (
    save_draft_proposal_activity,
    set_repo_status_activity,
)
from app.temporal.activities.portfolio import (
    create_docs_pull_request_activity,
    portfolio_deep_scan_activity,
)

__all__ = [
    # analysis.py
    "say_hello",
    "analyze_repo_health",
    "deep_scan_repo",
    "get_repo_context_activity",
    # github.py
    "fetch_repo_list_activity",
    "create_pull_request_activity",
    "sync_pr_status_activity",
    "fetch_repos_extended_activity",
    "create_or_update_profile_repo_activity",
    # generation.py
    "generate_readme_activity",
    "generate_deep_readme_activity",
    "analyze_codebase_activity",
    "generate_doc_activity",
    "generate_profile_readme_activity",
    # persistence.py
    "save_draft_proposal_activity",
    "set_repo_status_activity",
    # portfolio.py
    "create_docs_pull_request_activity",
    "portfolio_deep_scan_activity",
]
