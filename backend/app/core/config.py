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


settings = Settings()
