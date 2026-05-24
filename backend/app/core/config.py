from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "GitHub Gardener"
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    LITELLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LITELLM_API_BASE: str | None = None
    DATABASE_URL: str = "postgresql://gardener:gardener_secret@localhost:5432/gardener"
    TEMPORAL_ADDRESS: str = "localhost:7233"
    FRONTEND_URL: str = ""

    # E5 guardrails — LLM cost cap
    # Reject a request when (prompt_tokens * input_price + max_output_tokens *
    # output_price) > this. Default $0.50 is comfortable headroom for normal
    # gpt-4o-mini calls (~$0.001-0.01 typical) and trips when something
    # accidentally feeds the LLM a massive prompt.
    LLM_MAX_COST_PER_REQUEST_USD: float = 0.50
    # Passed to LiteLLM as max_tokens (caps OUTPUT) AND used as the
    # pre-flight INPUT-prompt size check: a prompt larger than this would
    # leave no room for output under most context windows.
    LLM_MAX_TOKENS_PER_REQUEST: int = 4000


settings = Settings()
