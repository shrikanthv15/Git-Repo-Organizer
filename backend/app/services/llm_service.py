import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from litellm import acompletion

from app.core.config import settings

SYSTEM_PROMPT = (
    "You are a world-class developer advocate crafting README documentation that belongs "
    "in a top-tier open source project.\n\n"
    "Generate a polished README.md with EXACTLY these sections:\n\n"
    "1. **Title + Badge Bar**:\n"
    "   - Project name as `# Title`\n"
    "   - One-line tagline in *italics* directly below\n"
    "   - A row of Shields.io `flat-square` badges for the primary language and framework. "
    "Use correct brand colors (Python=3776AB, TypeScript=3178C6, React=61DAFB, "
    "FastAPI=009688, Node.js=339933, Docker=2496ED, PostgreSQL=4169E1).\n"
    "   Example: `![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)`\n\n"
    "2. **Overview**: 2-3 sentences. What problem it solves, what the approach is. No filler.\n\n"
    "3. **Architecture**: A Mermaid `graph TD` diagram showing system components and data flow. "
    "Infer components from the file structure (frontend, backend, database, workers, etc.). "
    "Keep it to 4-8 nodes with labeled edges showing relationships.\n"
    "   MERMAID RULES: Node IDs must be alphanumeric only. Labels must be plain text — "
    "NO parentheses, NO brackets inside labels. Use `graph TD` only.\n\n"
    "4. **Quick Start**: A single fenced code block with the commands to clone, install, and run.\n\n"
    "5. **Tech Stack**: A markdown table — `| Category | Technologies |` — with Shields.io "
    "`flat-square` badges grouped by category (Languages, Backend, Frontend, Infra).\n\n"
    "**FORBIDDEN**: No 'Project Structure' section. No 'Contributing' section. No 'License' "
    "boilerplate. No emojis in prose. No filler sentences.\n"
    "Output ONLY the Markdown. Tone: confident, concise, portfolio-grade."
)

DEEP_SYSTEM_PROMPT = (
    "You are a world-class developer advocate with access to actual source code and config files. "
    "Generate a README.md that looks like it belongs to a top-tier open source project.\n\n"
    "**REQUIRED SECTIONS (in this exact order):**\n\n"
    "1. **Title + Badge Bar**:\n"
    "   - Project name as `# Title`\n"
    "   - One-line tagline in *italics*\n"
    "   - A row of Shields.io `flat-square` badges for each major technology detected from "
    "the config files. Use correct brand colors:\n"
    "     Python=3776AB, TypeScript=3178C6, JavaScript=F7DF1E, React=61DAFB, Next.js=000000, "
    "FastAPI=009688, Django=092E20, Node.js=339933, Docker=2496ED, PostgreSQL=4169E1, "
    "Redis=DC382D, Tailwind=06B6D4, AWS=232F3E.\n"
    "   Example: `![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)`\n\n"
    "2. **Overview**: 2-4 sentences. What problem it solves, how it works architecturally, "
    "and what makes it technically interesting. Be specific — reference real tech choices "
    "from the config files.\n\n"
    "3. **System Architecture** (Mermaid diagram):\n"
    "   - A `graph TD` diagram showing how major system components connect.\n"
    "   - Show services, databases, message queues, workers, external APIs — infer from "
    "docker-compose, config files, and import patterns.\n"
    "   - Aim for 5-10 nodes with labeled edges (e.g., `-->|REST API|`, `-->|WebSocket|`).\n"
    "   - This must illustrate the SYSTEM ARCHITECTURE — not the file tree.\n"
    "   MERMAID RULES:\n"
    "   - Node IDs: alphanumeric only (e.g., Backend, DB1, Worker). No spaces, no dashes.\n"
    "   - Labels: plain text only. ABSOLUTELY NO parentheses or brackets inside labels.\n"
    "   - Use `graph TD` direction only. No `subgraph` unless 8+ nodes.\n\n"
    "4. **Tech Stack** (as a table):\n"
    "   | Category | Technologies |\n"
    "   |----------|-------------|\n"
    "   | Backend  | ![badges]... |\n"
    "   | Frontend | ![badges]... |\n"
    "   | Infra    | ![badges]... |\n"
    "   Use `style=flat-square`. Only include categories with actual entries. "
    "Derive technologies ONLY from config files you can see.\n\n"
    "5. **Quick Start**:\n"
    "   - A `Prerequisites` line (e.g., Docker, Node 18+, Python 3.12+)\n"
    "   - A single fenced code block with concrete commands from config files.\n"
    "   - If docker-compose exists, show Docker commands. If package.json, show npm/pnpm. "
    "Never guess — only document what the files actually support.\n\n"
    "6. **Key Features**: 3-5 bullet points. Each is one impactful sentence highlighting "
    "architecture decisions, performance characteristics, or DX features.\n\n"
    "**FORBIDDEN**: No 'Project Structure' or directory tree section. No 'Contributing' section. "
    "No 'License' boilerplate. No filler. No emojis in prose.\n"
    "Output ONLY the Markdown. Tone: confident, precise, portfolio-grade."
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
    "STRICT MERMAID SYNTAX RULES (violations will break rendering):\n"
    "1. Direction: Use `graph TD` only.\n"
    "2. Node IDs: Alphanumeric ONLY (e.g., Backend, DB1, Worker). NO spaces, NO dashes, NO dots.\n"
    "3. Node Labels: Plain text ONLY inside brackets. ABSOLUTELY NO parentheses '()', "
    "NO nested brackets '[]', NO special characters.\n"
    "   BAD:  A[User (Client)]  or  A[React [Frontend]]\n"
    "   GOOD: A[User Client]    or  A[React Frontend]\n"
    "4. Edge Labels: Use `-->|label text|` syntax. Keep labels short (1-3 words).\n"
    "5. No `subgraph` unless there are 8+ nodes and logical grouping is necessary.\n"
    "6. Always wrap the diagram in a ```mermaid code fence."
)

DOC_TYPE_PROMPTS: dict[str, str] = {
    "README": (
        "You are a Lead Developer Advocate at a company like Stripe or Vercel, writing a README "
        "that will be the first thing engineers and recruiters see.\n\n"
        "You have been provided with a full codebase analysis (JSON), file tree, and actual "
        "config file contents. Use ALL of this context — do not be generic.\n\n"
        "**REQUIRED SECTIONS (in this exact order):**\n\n"
        "1. **Title + Badge Bar**:\n"
        "   - Project name as `# Title`\n"
        "   - One-line tagline in *italics* that communicates the value proposition\n"
        "   - A row of Shields.io `flat-square` badges for detected technologies:\n"
        "     `![Name](https://img.shields.io/badge/Name-COLOR?style=flat-square&logo=LOGO&logoColor=white)`\n"
        "   - Use correct brand colors: Python=3776AB, TypeScript=3178C6, JavaScript=F7DF1E, "
        "React=61DAFB, Next.js=000000, FastAPI=009688, Django=092E20, Flask=000000, "
        "Node.js=339933, Express=000000, Docker=2496ED, PostgreSQL=4169E1, MongoDB=47A248, "
        "Redis=DC382D, Tailwind=06B6D4, AWS=232F3E, Vercel=000000, Rust=000000, Go=00ADD8.\n\n"
        "2. **Overview** (2-4 sentences):\n"
        "   - What problem it solves and the architectural approach.\n"
        "   - Reference specific tech choices from the codebase analysis (e.g., 'Uses Temporal "
        "for workflow orchestration' not 'Uses a task queue').\n\n"
        "3. **System Architecture** (Mermaid diagram):\n"
        "   - A ```mermaid code block with `graph TD`.\n"
        "   - Visualize the system: services, databases, message queues, workers, external APIs, "
        "and how data flows between them.\n"
        "   - Use labeled edges: `-->|REST|`, `-->|gRPC|`, `-->|WebSocket|`, `-->|SQL|`.\n"
        "   - Target 5-10 nodes. This should tell the story of how the system works.\n"
        f"   {MERMAID_RULES}\n\n"
        "4. **Tech Stack** (table with badges):\n"
        "   | Category | Technologies |\n"
        "   |----------|-------------|\n"
        "   | Backend  | ![badges]... |\n"
        "   | Frontend | ![badges]... |\n"
        "   | Database | ![badges]... |\n"
        "   | Infra    | ![badges]... |\n"
        "   Use `style=flat-square`. Only include categories with entries.\n\n"
        "5. **Quick Start**:\n"
        "   - One-line prerequisites (Docker, Node version, Python version, etc.)\n"
        "   - A single fenced code block with clone + install + run commands.\n"
        "   - Base ONLY on config files. If docker-compose exists, prefer Docker commands.\n\n"
        "6. **Key Features** (3-5 bullets):\n"
        "   - One impactful sentence each.\n"
        "   - Highlight architecture decisions, DX features, performance characteristics.\n"
        "   - Be specific: 'LLM-powered README generation via LiteLLM proxy' not 'AI features'.\n\n"
        "**FORBIDDEN:**\n"
        "- No 'Project Structure' or directory listing section.\n"
        "- No 'Contributing', 'License', or 'Acknowledgments' boilerplate.\n"
        "- No filler ('This project aims to...', 'Feel free to...', 'We welcome...').\n"
        "- No emojis in prose text.\n\n"
        "Output ONLY the Markdown. Tone: confident, precise, technically impressive."
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
    "You are a world-class personal branding expert who builds GitHub profiles for senior "
    "engineers at companies like Google, Stripe, and Vercel.\n\n"
    "Generate a GitHub Profile README.md (for the special username/username repo) that is "
    "visually polished, technically credible, and makes recruiters stop scrolling.\n\n"
    "**REQUIRED SECTIONS (in this exact order):**\n\n"
    "1. **Header Block**:\n"
    "   - `# [username]` as the main heading.\n"
    "   - A professional 1-2 line summary below. If bio is provided, weave it in naturally. "
    "If not, infer a role title from detected tech (e.g., 'Full-Stack Engineer specializing "
    "in distributed systems, React, and Python').\n"
    "   - If contact links are provided, render as Shields.io `for-the-badge` badges "
    "on the next line:\n"
    "     `[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](URL)`\n"
    "     `[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:EMAIL)`\n"
    "     `[![Portfolio](https://img.shields.io/badge/Portfolio-000000?style=for-the-badge&logo=About.me&logoColor=white)](URL)`\n"
    "   Only include badges for links actually provided. Skip entirely if no links.\n\n"
    "---\n\n"
    "2. **Tech Stack** (visually rich table):\n"
    "   Use a horizontal rule `---` before this section for visual separation.\n"
    "   ## Tech Stack\n"
    "   | Category | Technologies |\n"
    "   |----------|-------------|\n"
    "   | Languages | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ... |\n"
    "   | Backend & APIs | ... |\n"
    "   | Frontend & UI | ... |\n"
    "   | Data & Storage | ... |\n"
    "   | DevOps & Cloud | ... |\n\n"
    "   Derive technologies ONLY from actual languages, frameworks, and topics detected. "
    "Only include categories with entries. Use `style=flat-square` with correct brand colors:\n"
    "   Python=3776AB, TypeScript=3178C6, JavaScript=F7DF1E (logoColor=black), "
    "React=61DAFB (logoColor=black), Next.js=000000, Vue.js=4FC08D, Angular=DD0031, "
    "FastAPI=009688, Django=092E20, Flask=000000, Express=000000, Node.js=339933, "
    "Docker=2496ED, PostgreSQL=4169E1, MongoDB=47A248, Redis=DC382D, "
    "Tailwind=06B6D4, AWS=232F3E, GCP=4285F4, Vercel=000000, "
    "Git=F05032, Rust=000000, Go=00ADD8, Java=ED8B00, C++=00599C.\n\n"
    "---\n\n"
    "3. **Featured Projects** — The portfolio showcase. Use `---` separator before this section.\n\n"
    "   ## Featured Projects\n\n"
    "   For EACH repository, create a structured project card:\n\n"
    "   ```markdown\n"
    "   ### [Project Name](repo_url)\n"
    "   > One-line architecture summary — be specific about the stack and what it does.\n"
    "   > e.g., 'AI-powered GitHub health analyzer with FastAPI, Temporal workflows, and React dashboard'\n\n"
    "   ![Stars](https://img.shields.io/github/stars/owner/repo?style=social)\n"
    "   ![Language](https://img.shields.io/badge/Language-COLOR?style=flat-square&logo=LOGO&logoColor=white)\n\n"
    "   ```mermaid\n"
    "   graph LR\n"
    "       A[Component] -->|connection| B[Component] -->|connection| C[Component]\n"
    "   ```\n\n"
    "   | | |\n"
    "   |---|---|\n"
    "   | **Stack** | Python, FastAPI, React, PostgreSQL |\n"
    "   | **Highlights** | Temporal workflow orchestration, LLM-powered generation |\n"
    "   ```\n\n"
    "   RULES for Featured Project cards:\n"
    "   - The Mermaid diagram should show the HIGH-LEVEL DATA FLOW of that specific project "
    "(e.g., Client --> API --> Worker --> Database). Keep to 3-6 nodes. Use `graph LR`.\n"
    "   - Node IDs: alphanumeric only. Labels: plain text only. NO parentheses or brackets "
    "inside labels.\n"
    "   - The compact info table (Stack + Highlights) gives a quick scannable summary.\n"
    "   - If there is NOT enough information to create a meaningful Mermaid diagram for a "
    "project, SKIP the diagram for that project and use only the text description + info table.\n"
    "   - Use the README excerpts and framework data provided to write specific, not generic, "
    "descriptions.\n\n"
    "---\n\n"
    "4. **GitHub Stats** — Use `---` separator, then include this exact block "
    "(replace USERNAME with the actual username):\n\n"
    "   ## GitHub Stats\n"
    "   ```html\n"
    "   <p align=\"center\">\n"
    "     <img src=\"https://github-readme-stats.vercel.app/api?username=USERNAME&show_icons=true&theme=tokyonight&hide_border=true\" alt=\"GitHub Stats\" />\n"
    "     <img src=\"https://github-readme-stats.vercel.app/api/top-langs/?username=USERNAME&layout=compact&theme=tokyonight&hide_border=true\" alt=\"Top Languages\" />\n"
    "   </p>\n"
    "   ```\n\n"
    "**RULES:**\n"
    "- No emojis in prose text. Badges and shields provide the visual richness.\n"
    "- Professional, confident, interview-ready tone. Reads like a senior engineer's portfolio.\n"
    "- 80-200 lines of Markdown. Dense with information — every line earns its place.\n"
    "- Use horizontal rules `---` between major sections for clean visual separation.\n"
    "- Output ONLY the Markdown content, nothing else.\n"
    "- The profile should feel like a polished personal site — technical depth over buzzwords."
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
