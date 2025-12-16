"""
Configuration management for Life Admin Assistant.
Loads environment variables and provides app-wide settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    """Application configuration loaded from environment variables."""

    # GitHub Models API
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    MODEL_ENDPOINT: str = "https://models.github.ai/inference"
    MODEL_NAME: str = os.getenv("MODEL_NAME", "openai/gpt-4.1-mini")

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/life_admin.db")

    # Agent settings
    AGENT_NAME: str = "Life Admin Assistant"
    MAX_HISTORY_MESSAGES: int = 20 # Keep last N messages in context

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

