"""
Agent configuration for Life Admin Assistant.
Sets up the ChatAgent with GitHub Models and tools.
"""

import asyncio
import logging
from datetime import date
from pathlib import Path
from typing import Optional
from functools import wraps

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from agent_framework.observability import setup_observability
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError

from .tools import ALL_TOOLS, set_document_repository, set_subscription_repository, set_checklist_repository, set_notification_repository
from .config import Config
from .database.repository.repository import Repository

# Configure logging
logger = logging.getLogger(__name__)


def setup_tracing(enable: bool = True, otlp_endpoint: str = "http://localhost:4317"):
    """
    Set up OpenTelemetry tracing for the agent.
    
    Args:
        enable: Whether to enable tracing (default: True)
        otlp_endpoint: OTLP collector endpoint (default: AI Toolkit gRPC endpoint)
    
    To view traces:
    1. Open VS Code Command Palette (Ctrl+Shift+P)
    2. Run "AI Toolkit: Open Trace Viewer"
    """
    if not enable:
        return
    
    try:
        setup_observability(
            otlp_endpoint=otlp_endpoint,
            enable_sensitive_data=True  # Capture prompts and completions for debugging
        )
        logger.info(f"Tracing enabled. Sending traces to {otlp_endpoint}")
    except Exception as e:
        logger.warning(f"Failed to set up tracing: {e}. Continuing without tracing.")


def retry_async(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for async functions to retry on transient errors.
    Uses exponential backoff between retries.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except RateLimitError as e:
                    last_exception = e
                    logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
                except APIConnectionError as e:
                    last_exception = e
                    logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}). Retrying in {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
                except APIError as e:
                    # Don't retry on client errors (4xx except 429)
                    if e.status_code and 400 <= e.status_code < 500 and e.status_code != 429:
                        raise
                    last_exception = e
                    logger.warning(f"API error (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            # All retries exhausted
            logger.error(f"All {max_retries} retries exhausted for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator

class LifeAdminAgent:
    """
    The Life Admin Assistant agent.
    Wraps a ChatAgent with our configuration and tools.
    """

    _tracing_initialized = False  # Class-level flag to avoid duplicate setup

    def __init__(self):
        """Initialize the agent with configuration."""
        Config.validate()

        # Set up tracing (only once per application)
        if not LifeAdminAgent._tracing_initialized and Config.TRACING_ENABLED:
            setup_tracing(enable=True, otlp_endpoint=Config.OTLP_ENDPOINT)
            LifeAdminAgent._tracing_initialized = True

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
        set_notification_repository(self.repository)

        return ALL_TOOLS
    
    @retry_async(max_retries=3, delay=1.0, backoff=2.0)
    async def chat(self, user_message: str) -> str:
        """
        Send a message and get a response.
        Uses streaming internally but returns complete response.
        Includes automatic retry on transient errors.
        """
        try:
            response_text = ""

            async for chunk in self.agent.run_stream(user_message, thread=self.thread):
                if chunk.text:
                    response_text += chunk.text
            
            return response_text
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise
    
    async def chat_stream(self, user_message: str):
        """
        Send a message and stream the response.
        Yields chunks of text as they arrive.
        Includes error handling for streaming.
        """
        try:
            async for chunk in self.agent.run_stream(user_message, thread=self.thread):
                if chunk.text:
                    yield chunk.text
        except RateLimitError:
            yield "\n\n⚠️ Rate limit reached. Please wait a moment and try again."
        except APIConnectionError:
            yield "\n\n⚠️ Connection error. Please check your internet connection."
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"\n\n⚠️ An error occurred: {str(e)}"
    
    def reset_conversation(self):
        """Reset the conversation thread."""
        self.thread = self.agent.get_new_thread()
    

async def create_agent() -> LifeAdminAgent:
    """Factory function to create a configured agent."""
    return LifeAdminAgent()

