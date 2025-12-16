"""
Agent configuration for Life Admin Assistant.
Sets up the ChatAgent with GitHub Models and tools.
"""

import asyncio
import logging
from datetime import date
from pathlib import Path
from typing import Optional, List, Dict
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
    
    # Token management settings (for 8000 token limit)
    # Be VERY aggressive to avoid 413 errors
    MAX_CONVERSATION_TOKENS = 2000  # Very conservative
    TOKENS_PER_CHAR = 0.5  # Conservative estimate
    MAX_MESSAGES_BEFORE_SUMMARY = 4  # Summarize very frequently
    MAX_MESSAGE_LENGTH = 1000  # Truncate long messages in history
    SYSTEM_PROMPT_TOKENS = 600  # Condensed system prompt estimate

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
        
        # Track conversation for token management
        self.conversation_history: List[Dict[str, str]] = []
        self.conversation_summary: Optional[str] = None


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
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (rough approximation)."""
        return int(len(text) * self.TOKENS_PER_CHAR)
    
    def _get_conversation_tokens(self) -> int:
        """Estimate total tokens in conversation history."""
        total = 0
        if self.conversation_summary:
            total += self._estimate_tokens(self.conversation_summary)
        for msg in self.conversation_history:
            total += self._estimate_tokens(msg.get("content", ""))
        return total
    
    def _truncate_message(self, content: str) -> str:
        """Truncate a message to stay within limits."""
        if len(content) > self.MAX_MESSAGE_LENGTH:
            return content[:self.MAX_MESSAGE_LENGTH] + "... [truncated]"
        return content
    
    async def _summarize_conversation(self) -> str:
        """Create a summary of the conversation history."""
        if not self.conversation_history:
            return ""
        
        # Build context for summarization
        history_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content'][:500]}"  # Truncate long messages
            for msg in self.conversation_history[-10:]  # Last 10 messages
        ])
        
        summary_prompt = (
            "Summarize this conversation briefly, focusing on:\n"
            "1. User's main goals/requests\n"
            "2. Key actions taken (documents, subscriptions, events created)\n"
            "3. Important context for continuing the conversation\n\n"
            f"Conversation:\n{history_text}\n\n"
            "Summary (2-3 sentences):"
        )
        
        try:
            # Use the model to create a summary
            response = await self.openai_client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=200,
                temperature=0.3
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"Failed to summarize conversation: {e}")
            # Fallback: just keep key points
            return f"Previous context: User has been managing their life admin tasks."
    
    async def _manage_conversation_length(self, force_summarize: bool = False):
        """Manage conversation history to stay within token limits."""
        current_tokens = self._get_conversation_tokens()
        
        # Check if we need to summarize
        should_summarize = (
            force_summarize or
            current_tokens > self.MAX_CONVERSATION_TOKENS or 
            len(self.conversation_history) > self.MAX_MESSAGES_BEFORE_SUMMARY
        )
        
        if should_summarize and len(self.conversation_history) > 1:
            logger.info(f"Conversation tokens ({current_tokens}) - Summarizing...")
            
            # Create summary of older messages
            try:
                new_summary = await self._summarize_conversation()
            except Exception as e:
                logger.warning(f"Summarization failed: {e}")
                new_summary = "User working on life admin tasks."
            
            # Keep only the most recent summary (limit size)
            self.conversation_summary = new_summary[:300] if new_summary else None
            
            # Keep only the last message for continuity
            if force_summarize:
                self.conversation_history = []  # Complete reset if forced
            else:
                self.conversation_history = self.conversation_history[-1:] if self.conversation_history else []
            
            # Reset thread with fresh context
            self.thread = self.agent.get_new_thread()
            
            logger.info(f"Conversation summarized. New token estimate: {self._get_conversation_tokens()}")
    
    async def chat(self, user_message: str) -> str:
        """
        Send a message and get a response.
        Uses streaming internally but returns complete response.
        Manages conversation length to avoid token limits.
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Manage conversation length before sending
                await self._manage_conversation_length()
                
                # Only add user message on first attempt
                if attempt == 0:
                    self.conversation_history.append({
                        "role": "user",
                        "content": self._truncate_message(user_message)
                    })
                
                response_text = ""

                async for chunk in self.agent.run_stream(user_message, thread=self.thread):
                    if chunk.text:
                        response_text += chunk.text
                
                # Track assistant response (truncated for history)
                self.conversation_history.append({
                    "role": "assistant",
                    "content": self._truncate_message(response_text)
                })
                
                return response_text
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check for token limit error (can be wrapped in various ways)
                if "413" in error_str or "tokens_limit" in error_str or "too large" in error_str:
                    logger.warning(f"Token limit hit (attempt {attempt + 1}) - forcing summarization")
                    
                    if attempt < max_retries - 1:
                        # Force aggressive summarization and reset
                        await self._manage_conversation_length(force_summarize=True)
                        # Clear and start fresh thread
                        self.thread = self.agent.get_new_thread()
                        continue
                    else:
                        # Last resort: clear everything but preserve user's last request
                        logger.error("Token limit persists - resetting conversation")
                        last_request = user_message[:200]  # Keep context of what they wanted
                        self.reset_conversation()
                        return (
                            f"⚠️ Memory limit reached. I've cleared the history but remember you wanted: **{last_request}**\n\n"
                            "Please say 'continue' or rephrase your request. "
                            "Tip: Ask for a summary version first, then expand sections."
                        )
                else:
                    logger.error(f"Chat error: {e}")
                    raise
        
        return "⚠️ An error occurred. Please try again."
    
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
        """Reset the conversation thread and history."""
        self.thread = self.agent.get_new_thread()
        self.conversation_history = []
        self.conversation_summary = None
    
    def get_conversation_stats(self) -> Dict:
        """Get statistics about the current conversation."""
        return {
            "message_count": len(self.conversation_history),
            "estimated_tokens": self._get_conversation_tokens(),
            "max_tokens": self.MAX_CONVERSATION_TOKENS,
            "has_summary": self.conversation_summary is not None,
            "token_usage_percent": int(
                (self._get_conversation_tokens() / self.MAX_CONVERSATION_TOKENS) * 100
            )
        }
    

async def create_agent() -> LifeAdminAgent:
    """Factory function to create a configured agent."""
    return LifeAdminAgent()

