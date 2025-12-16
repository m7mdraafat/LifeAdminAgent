"""Sidebar component for the web UI."""

import streamlit as st
from datetime import date
from .auth import get_current_user, logout


def render_sidebar():
    """Render the sidebar with summaries and quick actions."""
    with st.sidebar:
        # App branding
        st.markdown("## :material/task_alt: Life Admin")
        
        # User info
        user = get_current_user()
        if user:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"👤 {user['display_name']}")
            with col2:
                if st.button("↪️", help="Logout", key="logout_btn"):
                    logout()
                    st.rerun()
        
        st.divider()

        # Quick Actions
        st.markdown("**:material/bolt: Quick Actions**")
        
        if st.button(":material/description: Add Document", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "I want to add a new document"})
            st.rerun()
        
        if st.button(":material/credit_card: Add Subscription", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "I want to add a new subscription"})
            st.rerun()
        
        if st.button(":material/event: Start Life Event", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "What life events can you help me with?"})
            st.rerun()
        
        st.divider()
        
        # Dashboard
        st.markdown("**:material/dashboard: Dashboard**")
        
        # Document Summary
        with st.expander(":material/description: Documents", expanded=True):
            docs = st.session_state.repo.get_documents()
            expiring = st.session_state.repo.get_expiring_documents(days_ahead=30)
            
            col1, col2 = st.columns(2)
            col1.metric("Total", len(docs))
            col2.metric("Expiring", len(expiring))
            
            if expiring:
                st.markdown("---")
                for doc in expiring[:3]:
                    days = doc.days_until_expiry()
                    if days < 0:
                        st.caption(f"⚠️ **{doc.name}** — Expired")
                    elif days <= 7:
                        st.caption(f"⚠️ **{doc.name}** — {days} days left")
                    else:
                        st.caption(f"• {doc.name} — {days} days left")

        # Subscription Summary
        with st.expander(":material/credit_card: Subscriptions", expanded=True):
            subs = st.session_state.repo.get_subscriptions()
            summary = st.session_state.repo.get_spending_summary()
            
            col1, col2 = st.columns(2)
            col1.metric("Monthly", f"${summary['monthly_total']:.0f}")
            col2.metric("Yearly", f"${summary['yearly_total']:.0f}")
            
            # Trials ending soon
            trials = [s for s in subs if s.is_free_trial]
            ending_trials = [s for s in trials if s.trial_end_date and (s.trial_end_date - date.today()).days <= 7]
            
            if ending_trials:
                st.markdown("---")
                st.caption("**Trials ending soon:**")
                for trial in ending_trials[:2]:
                    days = (trial.trial_end_date - date.today()).days
                    st.caption(f"⚠️ {trial.service_name} — {days} days left")

        # Life Events Summary  
        with st.expander(":material/event: Life Events", expanded=True):
            events = st.session_state.repo.get_life_events()
            active_events = [e for e in events if e.status != "completed"]
            total_tasks = sum(len(e.checklist_items) for e in active_events)
            completed_tasks = sum(sum(1 for i in e.checklist_items if i.is_completed) for e in active_events)
            
            col1, col2 = st.columns(2)
            col1.metric("Active", len(active_events))
            col2.metric("Tasks", f"{completed_tasks}/{total_tasks}")
            
            st.caption("👉 See **Overview tab** for checklists")
        
        st.divider()
        
        # Footer actions
        if st.button(":material/refresh: Clear conversation", use_container_width=True):
            st.session_state.messages = []
            if hasattr(st.session_state, 'agent'):
                st.session_state.agent.reset_conversation()
            st.rerun()
        
        st.caption(f"Today: {date.today().strftime('%B %d, %Y')}")
