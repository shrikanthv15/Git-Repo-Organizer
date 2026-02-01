import json

from litellm import acompletion

from app.core.config import settings

SYSTEM_PROMPT = (
    "You are a technical documentarian. "
    "Write a professional, concise README.md in Markdown format. "
    "Include sections for: project title, description, installation, "
    "usage, and contributing. Only output the Markdown content, nothing else."
)

DEEP_SYSTEM_PROMPT = (
    "You are a senior technical documentarian with access to actual source code context. "
    "Write a professional README.md in Markdown format.\n\n"
    "Required sections:\n"
    "1. **Project Title & Description** — infer purpose from the code.\n"
    "2. **Architecture Overview** — generate a Mermaid.js diagram of the provided file "
    "structure using ```mermaid graph TD``` syntax. Show top-level directories and key files.\n"
    "3. **Tech Stack** — list languages, frameworks, and tools detected from the config files.\n"
    "4. **Getting Started / How to Run** — write concrete commands based on the "
    "package.json scripts, pyproject.toml, requirements.txt, Dockerfile, or Makefile you see. "
    "Do NOT guess — only document what the config files actually support.\n"
    "5. **Project Structure** — brief description of key directories.\n"
    "6. **Contributing** — standard contribution guidelines.\n\n"
    "Only output the Markdown content, nothing else."
)


async def generate_readme(
    repo_name: str,
    file_structure: list[str],
    description: str | None,
) -> str:
    """Generate a README.md using LiteLLM (legacy shallow mode)."""
    user_prompt = (
        f"Repository: {repo_name}\n"
        f"Description: {description or 'No description provided.'}\n"
        f"File structure:\n{chr(10).join(file_structure)}\n\n"
        "Write a README.md for this project. Keep it concise and use Markdown."
    )

    kwargs: dict = {
        "model": settings.LLM_MODEL,
        "api_key": settings.LITELLM_API_KEY,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    if settings.LITELLM_API_BASE:
        kwargs["api_base"] = settings.LITELLM_API_BASE

    response = await acompletion(**kwargs)
    return response.choices[0].message.content


def _format_tree_for_prompt(tree: list[dict], indent: int = 0) -> str:
    """Flatten a nested file tree into an indented string for the LLM prompt."""
    lines: list[str] = []
    for node in tree:
        prefix = "  " * indent
        if node["type"] == "dir":
            lines.append(f"{prefix}{node['name']}/")
            lines.append(_format_tree_for_prompt(node.get("children", []), indent + 1))
        else:
            lines.append(f"{prefix}{node['name']}")
    return "\n".join(lines)


async def generate_deep_readme(
    repo_name: str,
    description: str | None,
    file_tree: list[dict],
    tech_stack_files: dict[str, str],
) -> str:
    """Generate a README.md using deep code context (file tree + actual file contents)."""
    tree_text = _format_tree_for_prompt(file_tree)

    tech_sections: list[str] = []
    for filename, content in tech_stack_files.items():
        tech_sections.append(f"--- {filename} ---\n{content}")
    tech_text = "\n\n".join(tech_sections) if tech_sections else "No config files found."

    user_prompt = (
        f"Repository: {repo_name}\n"
        f"Description: {description or 'No description provided.'}\n\n"
        f"## File Structure\n```\n{tree_text}\n```\n\n"
        f"## Key Configuration Files (actual contents)\n\n{tech_text}\n\n"
        "Using the above real source context, write the README.md now."
    )

    kwargs: dict = {
        "model": settings.LLM_MODEL,
        "api_key": settings.LITELLM_API_KEY,
        "messages": [
            {"role": "system", "content": DEEP_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    if settings.LITELLM_API_BASE:
        kwargs["api_base"] = settings.LITELLM_API_BASE

    response = await acompletion(**kwargs)
    return response.choices[0].message.content
