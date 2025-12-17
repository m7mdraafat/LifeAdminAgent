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
from src.web.auth import render_auth_page, get_current_user, logout, init_sessions_table


# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Life Admin Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
apply_custom_styles()

# Initialize base repository for auth (no user filter)
# Also reinitialize if repo is outdated (missing set_user method from older cached session)
if "repo" not in st.session_state or not hasattr(st.session_state.repo, "set_user"):
    st.session_state.repo = Repository()
    init_sessions_table(st.session_state.repo)  # Ensure sessions table exists

# Initialize session state for persistence across reruns
if "messages" not in st.session_state:
    st.session_state.messages = []


def init_user_session(user: dict):
    """Initialize session for authenticated user."""
    # Set user on repository for data isolation
    st.session_state.repo.set_user(user["id"])
    
    # Create agent if not exists or user changed
    if "agent" not in st.session_state or st.session_state.get("current_user_id") != user["id"]:
        st.session_state.agent = LifeAdminAgent()
        st.session_state.agent.set_user(user["id"])
        st.session_state.current_user_id = user["id"]
        st.session_state.messages = []
    else:
        # Ensure user is set even on page refresh
        st.session_state.agent.set_user(user["id"])


def main():
    """Main entry point for the Streamlit app."""
    user = get_current_user()
    
    if not user:
        # Show login/signup page
        render_auth_page()
    else:
        # Initialize user session
        init_user_session(user)
        
        # Render main app
        render_sidebar()
        render_chat()


if __name__ == "__main__":
    main()