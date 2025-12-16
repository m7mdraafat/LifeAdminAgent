"""Sidebar component for the web UI."""

import streamlit as st
from datetime import date


def render_sidebar():
    """Render the sidebar with summaries and quick actions."""
    with st.sidebar:
        # App branding
        st.markdown("## :material/task_alt: Life Admin")
        st.caption("Your personal life organizer")
        
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
            
            st.metric("Active", len(active_events))
            
            if active_events:
                st.markdown("---")
                for event in active_events[:3]:
                    completed = sum(1 for item in event.checklist_items if item.is_completed)
                    total = len(event.checklist_items)
                    progress = completed / total if total > 0 else 0
                    
                    days_left = (event.target_date - date.today()).days
                    st.caption(f"**{event.title[:25]}**")
                    st.progress(progress, text=f"{completed}/{total} tasks · {days_left} days left")
        
        st.divider()
        
        # Footer actions
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent.reset_conversation()
            st.rerun()
        
        st.caption(f"Today: {date.today().strftime('%B %d, %Y')}")
