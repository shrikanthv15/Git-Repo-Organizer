import asyncio
import json

from temporalio import activity

from app.services import llm_service


# ---------------------------------------------------------------------------
# Phase 6: README Generation (legacy shallow mode)
# ---------------------------------------------------------------------------

@activity.defn
async def generate_readme_activity(repo_name: str, file_structure: list[str], description: str) -> str:
    """Generate a README.md using LiteLLM (legacy shallow mode)."""
    return await llm_service.generate_readme(repo_name, file_structure, description)


@activity.defn
async def generate_deep_readme_activity(
    repo_name: str,
    description: str,
    file_tree: list[dict],
    tech_stack_files: dict[str, str],
) -> str:
    """Generate a README.md using deep code context."""
    return await llm_service.generate_deep_readme(
        repo_name, description, file_tree, tech_stack_files
    )


# ---------------------------------------------------------------------------
# Phase 12: Multi-Agent Documentation Squad
# ---------------------------------------------------------------------------

@activity.defn
async def analyze_codebase_activity(
    repo_name: str,
    description: str,
    file_tree: list[dict],
    tech_stack_files: dict[str, str],
) -> str:
    """Analyze codebase and return a JSON summary string."""
    return await llm_service.analyze_codebase(
        repo_name, description, file_tree, tech_stack_files
    )


@activity.defn
async def generate_doc_activity(
    summary_json: str,
    doc_type: str,
    repo_name: str,
    file_tree: list[dict],
    tech_stack_files: dict[str, str],
) -> dict:
    """Generate a single doc file. Returns dict with filename, content, doc_type, error."""
    filename = llm_service.DOC_TYPE_FILENAMES[doc_type]
    try:
        content = await llm_service.generate_doc(
            summary_json, doc_type, repo_name, file_tree, tech_stack_files
        )
        return {
            "filename": filename,
            "content": content,
            "doc_type": doc_type,
            "error": None,
        }
    except Exception as exc:
        activity.logger.error("generate_doc_activity failed for %s: %s", doc_type, exc)
        return {
            "filename": filename,
            "content": "",
            "doc_type": doc_type,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Phase 19: Profile README Generation
# ---------------------------------------------------------------------------

@activity.defn
async def generate_profile_readme_activity(
    top_repos_json: str,
    username: str,
    bio: str = "",
    links_json: str = "{}",
) -> str:
    """Generate a GitHub Profile README from the top repos."""
    top_repos: list[dict] = json.loads(top_repos_json)
    links: dict = json.loads(links_json) if links_json else {}
    return await llm_service.generate_profile_readme(top_repos, username, bio=bio, links=links)
