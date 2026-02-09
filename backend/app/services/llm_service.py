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

GOLDEN_PROFILE_SYSTEM_PROMPT = (
    "You are a Senior Developer Branding Expert at a top-tier tech career firm.\n"
    "Write a GitHub Profile README.md (the special username/username repository).\n\n"
    "**Structure (80-150 lines of Markdown):**\n\n"
    "1. **Header**: A clean `# Hi, I'm [username]` heading followed by a one-sentence "
    "professional summary. If bio text is provided, incorporate it naturally.\n\n"
    "2. **Contact Badges** (ONLY if links are provided): Render Shields.io badges for "
    "LinkedIn, Email, and Website using this exact syntax:\n"
    "   `[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](URL)`\n"
    "   `[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:EMAIL)`\n"
    "   `[![Website](https://img.shields.io/badge/Website-000000?style=for-the-badge&logo=About.me&logoColor=white)](URL)`\n"
    "   Only include badges for links that are actually provided. Skip this section entirely if no links given.\n\n"
    "3. **Tech Stack Table**: A categorized table with Shields.io badges:\n"
    "   | Category | Technologies |\n"
    "   |----------|-------------|\n"
    "   | Languages | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ... |\n"
    "   | Backend | ... |\n"
    "   | Frontend | ... |\n"
    "   | DevOps & Tools | ... |\n"
    "   Derive the technologies from the actual frameworks, languages, and topics detected in the repos. "
    "Only include categories that have entries. Use `style=flat-square`.\n\n"
    "4. **Featured Projects**: For each project, write an impact-driven description:\n"
    "   ### [Project Name](url)\n"
    "   > One-line architecture summary (e.g., 'Full-stack app with FastAPI + React + Temporal workflows')\n\n"
    "   - Highlight the architecture and tech choices, not just what the app does.\n"
    "   - If README excerpts or framework data is available, use it for specificity.\n"
    "   - Include stars badge: `![Stars](https://img.shields.io/github/stars/owner/repo?style=social)`\n\n"
    "5. **GitHub Stats Widget**: Include this exact block:\n"
    "   ```\n"
    "   ![GitHub Stats](https://github-readme-stats.vercel.app/api?username=USERNAME&show_icons=true&theme=tokyonight&hide_border=true)\n"
    "   ```\n\n"
    "**Rules:**\n"
    "- No emojis in prose text (badges are fine).\n"
    "- Professional, confident, interview-ready tone.\n"
    "- Only output the Markdown content, nothing else.\n"
    "- Do NOT use Mermaid diagrams in profile READMEs."
)


async def generate_profile_readme(
    top_repos: list[dict],
    username: str,
    bio: str = "",
    links: dict | None = None,
) -> str:
    """Generate a GitHub Profile README using LangChain with rich context."""
    # Build aggregated language stats
    lang_counts: dict[str, int] = {}
    all_frameworks: set[str] = set()
    all_topics: set[str] = set()

    for repo in top_repos:
        lang = repo.get("language") or "Other"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        all_frameworks.update(repo.get("frameworks", []))
        all_topics.update(repo.get("topics", []))

    lang_summary = ", ".join(
        f"{lang}: {count} project{'s' if count > 1 else ''}"
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])
    )

    frameworks_summary = ", ".join(sorted(all_frameworks)) if all_frameworks else "None detected"
    topics_summary = ", ".join(sorted(all_topics)) if all_topics else "None"

    # Build per-repo context with README excerpts
    repo_sections: list[str] = []
    for repo in top_repos:
        section = (
            f"### {repo.get('full_name', repo.get('name', 'unknown'))}\n"
            f"- URL: {repo.get('html_url', '')}\n"
            f"- Language: {repo.get('language', 'N/A')}\n"
            f"- Stars: {repo.get('stargazers_count', 0)}\n"
            f"- Forks: {repo.get('forks_count', 0)}\n"
            f"- Description: {repo.get('description', 'No description')}\n"
            f"- Frameworks: {', '.join(repo.get('frameworks', [])) or 'N/A'}\n"
            f"- Topics: {', '.join(repo.get('topics', [])) or 'N/A'}\n"
        )
        readme_excerpt = repo.get("readme_content", "")
        if readme_excerpt:
            section += f"- README excerpt:\n{readme_excerpt[:1500]}\n"
        repo_sections.append(section)

    repos_context = "\n".join(repo_sections)

    # Build links context
    links_context = ""
    if links:
        link_parts = []
        if links.get("linkedin"):
            link_parts.append(f"LinkedIn: {links['linkedin']}")
        if links.get("email"):
            link_parts.append(f"Email: {links['email']}")
        if links.get("website"):
            link_parts.append(f"Website: {links['website']}")
        links_context = "\n".join(link_parts) if link_parts else "No links provided."
    else:
        links_context = "No links provided."

    bio_context = bio if bio else "No bio provided."

    prompt = ChatPromptTemplate.from_messages([
        ("system", GOLDEN_PROFILE_SYSTEM_PROMPT),
        ("human",
         "GitHub Username: {username}\n\n"
         "## Bio\n{bio_context}\n\n"
         "## Contact Links\n{links_context}\n\n"
         "## Languages\n{lang_summary}\n\n"
         "## Detected Frameworks\n{frameworks_summary}\n\n"
         "## Topics\n{topics_summary}\n\n"
         "## Featured Repositories\n{repos_context}\n\n"
         "Generate the profile README now."),
    ])

    chain = prompt | _get_chat_model()
    response = await chain.ainvoke({
        "username": username,
        "bio_context": bio_context,
        "links_context": links_context,
        "lang_summary": lang_summary,
        "frameworks_summary": frameworks_summary,
        "topics_summary": topics_summary,
        "repos_context": repos_context,
    })
    return response.content
