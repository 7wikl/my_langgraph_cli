"""Application settings - loads configuration from .env via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file's directory (project root), not CWD
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    # LLM settings
    LLM_MODEL_NAME: str = "gpt-3.5-turbo"
    OPENAI_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"

    # LangFuse observability
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "http://localhost:3000"

    # LangGraph persistence
    POSTGRES_DATABASE_URI: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # Vector database & embedding
    QDRANT_URL: str = ""
    COLLECTION: str = ""
    TEI_URL: str = ""

    # External APIs
    AI_SQL_URL: str = ""
    EXECUTE_SQL_URL: str = ""
    ASSET_CONTROL_KEY: str = "dev-secret-key-change-in-production"
    STOCKSELECT_API_URL: str = ""
    TUSHARE_TOKEN: str = ""

    # FastAPI server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_KEY: str = ""

    # LangChain tracing
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = ""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
