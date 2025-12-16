"""
Command-line interface for Life Admin Assistant.
Provides an interactive chat experience.
"""

import asyncio
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

from .agent import LifeAdminAgent
from .config import Config


console = Console()


class ChatCLI:
    """Interactive command-line chat interface."""
    
    def __init__(self):
        self.agent: Optional[LifeAdminAgent] = None
        self.running = False
    
    def print_welcome(self):
        """Display welcome message."""
        welcome = """
# 🏠 Life Admin Assistant

Your personal assistant for managing:
- 📄 **Documents** - Track expiry dates (passport, license, etc.)
- 💳 **Subscriptions** - Monitor spending and free trials
- 📋 **Life Events** - Checklists for moving, new job, and more

**Commands:**
- Type `/help` for available commands
- Type `/exit` or `/quit` to exit
- Type `/clear` to clear conversation history
- Type `/status` to see tracked items

Let's get started! How can I help you today?
        """
        console.print(Panel(Markdown(welcome), style="bold cyan"))
    
    def print_help(self):
        """Display help information."""
        help_text = """
## Available Commands

### Special Commands
- `/help` - Show this help message
- `/exit`, `/quit` - Exit the application
- `/clear` - Clear conversation history
- `/status` - Show summary of tracked items

### What You Can Do
- **Track documents**: "My passport expires in March 2026"
- **Manage subscriptions**: "I subscribe to Netflix for $15.99/month"
- **Plan life events**: "I'm moving next month"
- **Get reminders**: "What's expiring soon?"
- **Calculate spending**: "How much am I spending on subscriptions?"

Just talk naturally - I'll understand!
        """
        console.print(Panel(Markdown(help_text), style="cyan"))
    
    async def show_status(self):
        """Display summary of tracked items."""
        console.print("\n[bold cyan]📊 Current Status[/bold cyan]\n")
        
        # Get documents expiring soon
        response = await self.agent.chat("List all my documents and tell me what's expiring soon")
        console.print(Markdown(response))
        
        console.print()
        
        # Get subscription summary
        response = await self.agent.chat("Show my subscription spending summary")
        console.print(Markdown(response))
        
        console.print()
        
        # Get life events
        response = await self.agent.chat("List my life events")
        console.print(Markdown(response))
    
    def handle_command(self, user_input: str) -> bool:
        """
        Handle special commands.
        Returns True if command was handled, False otherwise.
        """
        command = user_input.lower().strip()
        
        if command in ["/exit", "/quit"]:
            console.print("\n[bold yellow]👋 Goodbye! Stay organized![/bold yellow]\n")
            self.running = False
            return True
        
        elif command == "/help":
            self.print_help()
            return True
        
        elif command == "/clear":
            self.agent.reset_conversation()
            console.clear()
            self.print_welcome()
            console.print("[green]✅ Conversation history cleared![/green]\n")
            return True
        
        elif command == "/status":
            asyncio.create_task(self.show_status())
            return True
        
        return False
    
    async def chat_loop(self):
        """Main interactive chat loop."""
        # Initialize agent
        console.print("[yellow]🔧 Initializing Life Admin Assistant...[/yellow]")
        self.agent = LifeAdminAgent()
        model_name = Config.get_model_display_name()
        console.print(f"[green]✅ Connected to {model_name}[/green]\n")
        
        # Show welcome
        self.print_welcome()
        
        self.running = True
        
        while self.running:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    if self.handle_command(user_input):
                        if not self.running:
                            break
                        continue
                
                # Show typing indicator while processing
                console.print("\n[bold green]Assistant[/bold green]: ", end="")
                
                # Stream response
                response_text = ""
                async for chunk in self.agent.chat_stream(user_input):
                    console.print(chunk, end="", style="white")
                    response_text += chunk
                
                console.print()  # New line after response
                
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
                continue
            except Exception as e:
                console.print(f"\n[red]❌ Error: {e}[/red]")
                console.print("[yellow]Type /help for assistance.[/yellow]")
    
    async def run(self):
        """Start the CLI application."""
        try:
            await self.chat_loop()
        except Exception as e:
            console.print(f"\n[red]Fatal error: {e}[/red]")
            raise


async def main():
    """Entry point for CLI application."""
    cli = ChatCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())