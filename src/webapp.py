"""
Streamlit Web UI for Life Admin Assistant.
A beautiful chat interface with dashboard sidebar.
"""

import streamlit as st
import asyncio
from datetime import datetime, date
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import LifeAdminAgent
from src.database.repository.repository import Repository 


st.set_page_config(
    page_title="Life Admin Assistant",
    page_icon="🤖",
    layout="wide", # Use full screen with
    initial_sidebar_state="expanded"
)

# Initialize session state for persistence across reruns
if "messages" not in st.session_state:
    st.session_state.messages = [] # Chat History

if "agent" not in st.session_state:
    st.session_state.agent = LifeAdminAgent() # AI agent instance

if "repo" not in st.session_state:
    st.session_state.repo = Repository() # Database repository instance


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def render_sidebar():
    """Render the sidebar with summaries"""
    with st.sidebar:
        st.title("📊 Dashboard")

        # Document Summary
        st.subheader("📄 Documents")
        docs = st.session_state.repo.get_documents()
        expiring = st.session_state.repo.get_expiring_documents(days_ahead=30)

        col1, col2 = st.columns(2)
        col1.metric("Total", len(docs))
        col2.metric("Expiring Soon", len(expiring))

        if expiring:
            st.warning(f"⚠️ {len(expiring)} document(s) expiring in 30 days!")
            for doc in expiring[:3]:  # Show first 3
                st.caption(f"• {doc.name}: {doc.days_until_expiry()} days")

        st.divider()

        # Subscription Summary
        st.subheader("💳 Subscriptions")
        subs = st.session_state.repo.get_subscriptions()
        summary = st.session_state.repo.get_spending_summary()

        st.metric("Monthly Spending", f"${summary['monthly_total']:.2f}")
        st.metric("Yearly Projection", f"${summary['yearly_total']:.2f}")

        # Find trials ending soon
        trials = [s for s in subs if s.is_free_trial and s.days_until_trial_ends() <= 7]
        if trials:
            st.error(f"🔔 {len(trials)} trial(s) ending soon!")

        st.divider()

        # Life Events Summary
        st.subheader("🎯 Life Events")
        events = st.session_state.repo.get_life_events()
        active_events = [e for e in events if e.status != "completed"]
        
        st.metric("Active Events", len(active_events))
        
        for event in active_events[:3]:
            completed = sum(1 for item in event.checklist_items if item.is_completed)
            total = len(event.checklist_items)
            progress = completed / total if total > 0 else 0
            
            st.caption(f"**{event.title}**")
            st.progress(progress, text=f"{completed}/{total} tasks")
        
        st.divider()
        
        # Clear conversation button
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent.reset_conversation()
            st.rerun()

def render_chat():
    """Render the main chat interface."""
    st.title("🤖 Life Admin Assistant Chat")
    st.caption("Your personal life management companion")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me about your documents, subscriptions, or life events..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response asynchronously
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Run async chat method
                    response = run_async(st.session_state.agent.chat(prompt))
                    st.markdown(response)

                    # Add assistant response to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
        st.rerun() # Rerun to refresh sidebar stats
    
def main():
    """Main entry point."""
    render_sidebar()
    render_chat()

if __name__ == "__main__":
    main()