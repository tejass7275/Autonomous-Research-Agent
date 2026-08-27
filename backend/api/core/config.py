"""
config.py
Central application configuration, loaded from environment variables.
Import `settings` anywhere config values are needed instead of reading
os.environ directly, so there's a single source of truth.
"""

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # App
    APP_NAME: str = "Autonomous Research Agent API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/research_agent",
    )

    # Auth / security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # CORS
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

    # RAG engine (shared with Member 1's module)
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "data/faiss_index")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 50


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — avoids re-reading env vars on every import."""
    return Settings()


settings = get_settings()

