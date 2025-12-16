"""
Streamlit Web UI for Life Admin Assistant.
A beautiful chat interface with dashboard sidebar.

This is the main entry point for the web app. Components are
organized in the src/web/ package for better maintainability.
"""

import streamlit as st
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import LifeAdminAgent
from src.database.repository.repository import Repository

# Import UI components
from src.web.styles import apply_custom_styles
from src.web.sidebar import render_sidebar
from src.web.chat import render_chat


# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Life Admin Assistant",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
apply_custom_styles()

# Initialize session state for persistence across reruns
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = LifeAdminAgent()

if "repo" not in st.session_state:
    st.session_state.repo = Repository()

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Chat"


def main():
    """Main entry point for the Streamlit app."""
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()