from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    anthropic_api_key: str
    github_pat: str = ""
    github_org: str = "oscorpAI"
    database_url: str
    model: str = "claude-sonnet-4-6"
    max_react_iterations: int = 20
    observability_adapter: str = "local"   # "local" | "datadog"
    cicd_adapter: str = "mock"             # "mock" | "real"


settings = Settings()
