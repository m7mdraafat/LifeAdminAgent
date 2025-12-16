"""
Life Admin Assistant - Main entry point
Run this to start the interactive chat interface.
"""

import asyncio
from src.cli import main

if __name__ == "__main__":
    asyncio.run(main())