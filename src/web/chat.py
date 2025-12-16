"""Chat component for the web UI."""

import streamlit as st
import asyncio

from .overview import render_overview_tab


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If there's already a running loop, create a new one in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(coro)


def render_welcome_message():
    """Show welcome message for new users."""
    return """
**Welcome to Life Admin Assistant!**

I can help you manage:
- **Documents** - Track expiry dates for passports, licenses, etc.
- **Subscriptions** - Monitor spending and free trials
- **Life Events** - Checklists for moving, new job, buying a car, and more

**Try saying:**
- "My passport expires on March 15, 2026"
- "I subscribe to Netflix for $15.99/month"
- "I'm moving next month"
- "What's expiring soon?"

How can I help you today?
    """


def render_chat():
    """Render the main chat interface."""
    
    # Header with tabs
    tab1, tab2 = st.tabs([":material/chat: Chat", ":material/analytics: Overview"])
    
    with tab1:
        # Header - always visible
        st.markdown(
            "<h2 style='text-align: center;'>✓ Life Admin Agent</h2>"
            "<p style='text-align: center; color: gray;'>"
            "Your personal assistant for documents, subscriptions, and life's big moments."
            "</p>",
            unsafe_allow_html=True
        )
        
        has_messages = len(st.session_state.messages) > 0
        
        # Suggestion chips - only show when no messages
        if not has_messages:
            st.markdown("")
            col1, col2, col3, col4 = st.columns(4)
            suggestions = [
                ("What's expiring?", col1),
                ("My subscriptions", col2),
                ("List documents", col3),
                ("Life events", col4)
            ]
            for text, col in suggestions:
                with col:
                    if st.button(text, use_container_width=True, key=f"sug_{text[:8]}"):
                        st.session_state.messages.append({"role": "user", "content": text})
                        st.rerun()
        
        st.markdown("---")
        
        # Display messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # If last message is from user, get agent response
        if has_messages and st.session_state.messages[-1]["role"] == "user":
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        response = run_async(st.session_state.agent.chat(
                            st.session_state.messages[-1]["content"]
                        ))
                    except Exception as e:
                        response = f"Error: {str(e)}"
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })
            st.rerun()
        
        # Chat input - always at bottom
        if prompt := st.chat_input("Ask me about your documents, subscriptions, or life events..."):
            # Add user message to history and trigger rerun to process it
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    with tab2:
        render_overview_tab()
