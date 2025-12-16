"""
Launch script for Streamlit Web UI.
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Get path to webapp.py
    webapp_path = Path(__file__).parent / "src" / "webapp.py"

    # Run streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(webapp_path),
        "--server.port", "8501",
        "--browser.gatherUsageStats", "false"
    ])

if __name__ == "__main__":
    main()

