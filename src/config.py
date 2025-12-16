"""
Configuration management for Life Admin Assistant.
Loads environment variables and provides app-wide settings.
Supports both local .env files and Streamlit Cloud secrets.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root (for local development)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_secret(key: str, default: str = "") -> str:
    """
    Get a secret value, checking Streamlit secrets first, then environment variables.
    This allows the app to work both locally (with .env) and on Streamlit Cloud.
    """
    # Try Streamlit secrets first (for cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except (ImportError, Exception):
        pass  # Not running in Streamlit context
    
    # Fall back to environment variables (for local development)
    return os.getenv(key, default)


class Config:
    """Application configuration loaded from environment variables or Streamlit secrets."""

    # GitHub Models API
    GITHUB_TOKEN: str = get_secret("GITHUB_TOKEN", "")
    MODEL_ENDPOINT: str = "https://models.github.ai/inference"
    MODEL_NAME: str = get_secret("MODEL_NAME", "openai/gpt-4.1-mini")

    # Database
    DATABASE_PATH: str = get_secret("DATABASE_PATH", "data/life_admin.db")

    # Agent settings
    AGENT_NAME: str = "Life Admin Assistant"
    MAX_HISTORY_MESSAGES: int = 20 # Keep last N messages in context

    # Tracing/Observability settings
    TRACING_ENABLED: bool = get_secret("TRACING_ENABLED", "true").lower() == "true"
    OTLP_ENDPOINT: str = get_secret("OTLP_ENDPOINT", "http://localhost:4317")

    @classmethod
    def validate(cls) -> bool:
        """Check if required config is present."""
        if not cls.GITHUB_TOKEN:
            raise ValueError(
                "GITHUB_TOKEN not found!\n"
                "Please create a .env file with your GitHub token."
                "GITHUB_TOKEN=your_token_here\n\n",
                "Get a token from: https://github.com/settings/tokens"
            )
        return True
    
    @classmethod
    def get_model_display_name(cls) -> str:
        """Get friendly model name for UI."""
        return cls.MODEL_NAME.split("/")[-1]
    
    
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(e)

