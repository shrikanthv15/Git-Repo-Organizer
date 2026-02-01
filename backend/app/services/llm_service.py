from litellm import acompletion

from app.core.config import settings

SYSTEM_PROMPT = (
    "You are a technical documentarian. "
    "Write a professional, concise README.md in Markdown format. "
    "Include sections for: project title, description, installation, "
    "usage, and contributing. Only output the Markdown content, nothing else."
)


async def generate_readme(
    repo_name: str,
    file_structure: list[str],
    description: str | None,
) -> str:
    """Generate a README.md using LiteLLM."""
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
