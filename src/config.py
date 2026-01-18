"""
Configuration module for Sprinklr Historical Data Chatbot.

Loads environment variables and provides configuration settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Sprinklr API Configuration
    SPRINKLR_API_KEY: str = os.getenv("SPRINKLR_API_KEY", "")
    SPRINKLR_API_SECRET: str = os.getenv("SPRINKLR_API_SECRET", "")
    SPRINKLR_ENVIRONMENT: str = os.getenv("SPRINKLR_ENVIRONMENT", "prod2")
    SPRINKLR_ACCESS_TOKEN: str = os.getenv("SPRINKLR_ACCESS_TOKEN", "")
    SPRINKLR_REFRESH_TOKEN: str = os.getenv("SPRINKLR_REFRESH_TOKEN", "")

    # Claude API Configuration
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")  # "anthropic" or "openai"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Application Settings
    USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")

    # Sprinklr API Base URLs by environment (includes env path)
    SPRINKLR_BASE_URLS = {
        "prod2": "https://api2.sprinklr.com/prod2",
        "prod3": "https://api3.sprinklr.com/prod3",
        "prod4": "https://api4.sprinklr.com/prod4",
        "prod5": "https://api5.sprinklr.com/prod5",
    }

    # Rate limiting settings (Sprinklr limits)
    RATE_LIMIT_CALLS_PER_HOUR: int = 1000
    RATE_LIMIT_CALLS_PER_SECOND: int = 10

    # Embedding model for vector search
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # ChromaDB collection name
    COLLECTION_NAME: str = "sprinklr_cases"

    # LLM settings
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    MAX_CONTEXT_CASES: int = 10  # Maximum cases to include in context (legacy)

    # Multi-Agent Settings
    USE_MULTI_AGENT: bool = os.getenv("USE_MULTI_AGENT", "true").lower() == "true"
    MAX_CONTEXT_CASES_BROAD: int = int(os.getenv("MAX_CONTEXT_CASES_BROAD", "50"))
    MAX_CONTEXT_CASES_SPECIFIC: int = int(os.getenv("MAX_CONTEXT_CASES_SPECIFIC", "10"))
    THEME_EXTRACTION_METHOD: str = os.getenv("THEME_EXTRACTION_METHOD", "keyword")  # "keyword" or "llm"

    @classmethod
    def get_sprinklr_base_url(cls) -> str:
        """Get the Sprinklr API base URL for the configured environment."""
        return cls.SPRINKLR_BASE_URLS.get(
            cls.SPRINKLR_ENVIRONMENT,
            cls.SPRINKLR_BASE_URLS["prod2"]
        )

    @classmethod
    def validate_sprinklr_config(cls) -> bool:
        """Check if Sprinklr API credentials are configured."""
        return bool(
            cls.SPRINKLR_API_KEY and
            cls.SPRINKLR_ACCESS_TOKEN
        )

    @classmethod
    def validate_anthropic_config(cls) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(cls.ANTHROPIC_API_KEY)

    @classmethod
    def validate_openai_config(cls) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(cls.OPENAI_API_KEY)

    @classmethod
    def ensure_data_directory(cls) -> Path:
        """Ensure the ChromaDB data directory exists."""
        path = Path(cls.CHROMA_DB_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Create a singleton instance for easy access
config = Config()
