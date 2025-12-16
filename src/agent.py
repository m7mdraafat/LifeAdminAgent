"""
Agent configuration for Life Admin Assistant.
Sets up the ChatAgent with GitHub Models and tools.
"""

import asyncio
from datetime import date
from pathlib import Path
from typing import Optional

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI

from .tools import ALL_TOOLS, set_document_repository, set_subscription_repository, set_checklist_repository
from .config import Config
from .database.repository.repository import Repository

class LifeAdminAgent:
    """
    The Life Admin Assistant agent.
    Wraps a ChatAgent with our configuration and tools.
    """

    def __init__(self):
        """Initialize the agent with configuration."""
        Config.validate()

        # Initialize database
        self.repository = Repository(db_path=Config.DATABASE_PATH)

        # Load system prompt
        self.system_prompt = self._load_system_prompt()

        # Create OpenAI client pointing to GitHub Models endpoint
        self.openai_client = AsyncOpenAI(
            base_url=Config.MODEL_ENDPOINT,
            api_key=Config.GITHUB_TOKEN
        )

        # Create chat client
        self.chat_client = OpenAIChatClient(
            async_client=self.openai_client,
            model_id=Config.MODEL_NAME
        )

        # Create the agent with tools
        self.agent = ChatAgent(
            chat_client=self.chat_client,
            name=Config.AGENT_NAME,
            instructions=self.system_prompt,
            tools=self._get_tools(),
        )

        # Thread for conversation history
        self.thread = self.agent.get_new_thread()


    def _load_system_prompt(self) -> str:
        """Load and format the system prompt."""
        prompt_path = Path(__file__).parent / "prompts" / "system_prompt.txt"
        if prompt_path.exists():
            prompt = prompt_path.read_text(encoding="utf-8")
        else:
            # Fallback prompt if file doesn't exist
            prompt = (
                "You are the Life Admin Assistant, helping users manage their important life documents "
                "and events. Provide clear, concise, and helpful responses."
            )
        
        # Replace placeholders if any
        prompt = prompt.replace("{current_date}", date.today().isoformat())

        return prompt

    def _get_tools(self) -> list:
        """
        Define the tools (functions) the agent can call.
        These connect the AI to your database operations or external APIs.
        """

        # Share the repository with tools
        set_document_repository(self.repository)
        set_subscription_repository(self.repository)
        set_checklist_repository(self.repository)

        return ALL_TOOLS
    
    async def chat(self, user_message: str) -> str:
        """
        Send a message and get a response.
        Uses streaming internally but returns complete response.
        """

        response_text = ""

        async for chunk in self.agent.run_stream(user_message, thread=self.thread):
            if chunk.text:
                response_text += chunk.text
        
        return response_text
    
    async def chat_stream(self, user_message: str):
        """
        Send a message and stream the response.
        Yields chunks of text as they arrive.
        """
        async for chunk in self.agent.run_stream(user_message, thread=self.thread):
            if chunk.text:
                yield chunk.text
    
    def reset_conversation(self):
        """Reset the conversation thread."""
        self.thread = self.agent.get_new_thread()
    

async def create_agent() -> LifeAdminAgent:
    """Factory function to create a configured agent."""
    return LifeAdminAgent()

