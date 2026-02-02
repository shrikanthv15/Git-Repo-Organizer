import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
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
    "STRICT RULE: Do not use parentheses '()' or brackets '[]' inside Mermaid node labels. "
    "Use simple text only (e.g., A[Frontend Service] instead of A[Frontend (Service)]).\n"
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


# ---------------------------------------------------------------------------
# LangChain-powered multi-doc generation (Phase 12)
# ---------------------------------------------------------------------------

def _get_chat_model() -> ChatOpenAI:
    """Factory that builds a ChatOpenAI pointing at the LiteLLM proxy."""
    kwargs: dict = {
        "model": settings.LLM_MODEL,
        "api_key": settings.LITELLM_API_KEY,
    }
    if settings.LITELLM_API_BASE:
        kwargs["base_url"] = settings.LITELLM_API_BASE
    return ChatOpenAI(**kwargs)


ANALYZE_SYSTEM_PROMPT = (
    "You are a senior software architect. Analyze the repository context provided "
    "and return a JSON object with the following keys:\n"
    "- project_name (string)\n"
    "- description (string — 1-2 sentence summary)\n"
    "- tech_stack (list of strings — languages, frameworks, tools)\n"
    "- key_features (list of strings)\n"
    "- architecture_patterns (list of strings — e.g. microservices, monolith, MVC)\n"
    "- build_system (string — e.g. npm, pip, cargo)\n"
    "- entry_points (list of strings — main files)\n"
    "- has_tests (boolean)\n"
    "- has_ci (boolean)\n"
    "- has_docker (boolean)\n\n"
    "Return ONLY valid JSON, no markdown fences, no extra text."
)


async def analyze_codebase(
    repo_name: str,
    description: str,
    file_tree: list[dict],
    tech_stack_files: dict[str, str],
) -> str:
    """Analyze repository and return a JSON summary string."""
    tree_text = _format_tree_for_prompt(file_tree)

    tech_sections: list[str] = []
    for filename, content in tech_stack_files.items():
        tech_sections.append(f"--- {filename} ---\n{content}")
    tech_text = "\n\n".join(tech_sections) if tech_sections else "No config files found."

    prompt = ChatPromptTemplate.from_messages([
        ("system", ANALYZE_SYSTEM_PROMPT),
        ("human",
         "Repository: {repo_name}\n"
         "Description: {description}\n\n"
         "## File Structure\n```\n{tree_text}\n```\n\n"
         "## Key Configuration Files\n\n{tech_text}"),
    ])

    chain = prompt | _get_chat_model()
    response = await chain.ainvoke({
        "repo_name": repo_name,
        "description": description or "No description provided.",
        "tree_text": tree_text,
        "tech_text": tech_text,
    })
    return response.content


# MERMAID_RULES are injected into every prompt to prevent syntax errors
MERMAID_RULES = (
    "STRICT MERMAID SYNTAX RULES:\n"
    "1. Use `graph TD` direction.\n"
    "2. Node IDs must be Alphanumeric ONLY (e.g., A1, UserService, DB). NO spaces, NO dashes.\n"
    "3. Node Labels must be simple text. ABSOLUTELY NO parentheses '()' or brackets '[]'.\n"
    "   - BAD: A[User (Client)]\n"
    "   - GOOD: A[User Client]\n"
    "4. Do NOT use `subgraph` unless strictly necessary. Keep diagrams simple."
)

DOC_TYPE_PROMPTS: dict[str, str] = {
    "README": (
        "You are a Lead Developer Advocate at a top-tier tech company (e.g., Stripe, Vercel).\n"
        "Write a high-impact, professional README.md for this repository.\n\n"
        "**Structure:**\n"
        "1. **Header**: Project Title + One-line high-value description.\n"
        "2. **Quick Start**: A single code block to install and run the project. "
        "Use the detected `package.json` or `requirements.txt` scripts.\n"
        "3. **Architecture**: A Mermaid diagram visualizing the *System Components* "
        "(not file imports).\n"
        f"{MERMAID_RULES}\n"
        "4. **Tech Stack**: A clean list of languages/frameworks detected.\n"
        "5. **Key Features**: 3 bullet points highlighting what makes this project special.\n\n"
        "**Tone**: concise, professional, interview-ready. No fluff."
    ),
}

DOC_TYPE_FILENAMES: dict[str, str] = {
    "README": "README.md",
}


async def generate_doc(
    summary_json: str,
    doc_type: str,
    repo_name: str,
    file_tree: list[dict],
    tech_stack_files: dict[str, str],
) -> str:
    """Generate a single documentation file using LangChain."""
    tree_text = _format_tree_for_prompt(file_tree)

    tech_sections: list[str] = []
    for filename, content in tech_stack_files.items():
        tech_sections.append(f"--- {filename} ---\n{content}")
    tech_text = "\n\n".join(tech_sections) if tech_sections else "No config files found."

    system_prompt = DOC_TYPE_PROMPTS[doc_type]

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human",
         "Repository: {repo_name}\n\n"
         "## Codebase Analysis\n{summary_json}\n\n"
         "## File Structure\n```\n{tree_text}\n```\n\n"
         "## Key Configuration Files\n\n{tech_text}\n\n"
         "Generate the {doc_type} document now."),
    ])

    chain = prompt | _get_chat_model()
    response = await chain.ainvoke({
        "repo_name": repo_name,
        "summary_json": summary_json,
        "tree_text": tree_text,
        "tech_text": tech_text,
        "doc_type": doc_type,
    })
    return response.content


# ---------------------------------------------------------------------------
# Phase 14: Portfolio Profile README Generation
# ---------------------------------------------------------------------------

PROFILE_SYSTEM_PROMPT = (
    "You are a Career Coach and Developer Branding Expert.\n"
    "Write a README.md for a GitHub Profile (the special username/username repository).\n\n"
    f"{MERMAID_RULES}\n\n"
    "**Required Sections:**\n"
    "1. **Intro**: A greeting line: 'Hi, I'm [username]. I build [summary of work] "
    "with [top technologies].' Keep it one short paragraph.\n"
    "2. **Tech Stack**: Generate a Mermaid Pie Chart showing language distribution.\n"
    "   Use ```mermaid pie title My Tech Stack``` syntax.\n"
    "   Each slice label must be a simple string with NO special characters.\n"
    "3. **Featured Work**: A Markdown table with the top projects.\n"
    "   Columns: Project | Stack | Description.\n"
    "   Link each project name to its GitHub URL.\n\n"
    "**Tone**: Professional, confident, interview-ready. No fluff, no emojis in prose.\n"
    "Only output the Markdown content, nothing else."
)


async def generate_profile_readme(
    top_repos: list[dict],
    username: str,
) -> str:
    """Generate a GitHub Profile README using LangChain."""
    # Build aggregated language stats
    lang_counts: dict[str, int] = {}
    for repo in top_repos:
        lang = repo.get("language") or "Other"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    lang_summary = ", ".join(
        f"{lang}: {count} project{'s' if count > 1 else ''}"
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])
    )

    repos_context = json.dumps(top_repos, indent=2, default=str)

    prompt = ChatPromptTemplate.from_messages([
        ("system", PROFILE_SYSTEM_PROMPT),
        ("human",
         "GitHub Username: {username}\n\n"
         "## Aggregated Language Stats\n{lang_summary}\n\n"
         "## Top Repositories (JSON)\n```json\n{repos_context}\n```\n\n"
         "Generate the profile README now."),
    ])

    chain = prompt | _get_chat_model()
    response = await chain.ainvoke({
        "username": username,
        "lang_summary": lang_summary,
        "repos_context": repos_context,
    })
    return response.content
