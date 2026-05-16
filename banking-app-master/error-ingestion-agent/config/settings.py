"""
Error Ingestion Agent — Configuration
Reads all settings from environment variables (12-factor style).
"""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # MySQL (unified rca_db)
    database_url: str = "mysql+pymysql://root:root@localhost:3306/rca_db"

    # Google Gemini
    gemini_api_key: str = ""

    # Operating mode
    mode: Literal["db", "datadog"] = "db"

    # Log file path (mode=db only)
    log_file_path: str = "/var/log/banking-app/app.log"

    # Service identification
    service_name: str = "banking-app"
    environment: str = "production"

    # Polling / webhook
    poll_interval_seconds: int = 5
    webhook_port: int = 8001

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
