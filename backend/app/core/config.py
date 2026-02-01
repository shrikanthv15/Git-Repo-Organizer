from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "GitHub Gardener"
    GITHUB_CLIENT_ID: str = "Ov23li4fEHcW2f7yiRhp"
    GITHUB_CLIENT_SECRET: str = "f72979e998aa61108d92e1d856c1cd3367aa7671"
    LITELLM_API_KEY: str = "sk-l5ZNnzwyHAcQGb8yLSvaxA"
    LLM_MODEL: str = "gpt-5-nano"
    LITELLM_API_BASE: str | None = "https://litellm.confersolutions.ai/v1"


settings = Settings()
