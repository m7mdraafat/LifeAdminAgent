"""Overview tab component for the web UI."""

import streamlit as st
from datetime import date


def render_overview_tab():
    """Render the overview/analytics tab."""
    st.markdown("## Your Life Admin Overview")
    
    # Top row - key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    docs = st.session_state.repo.get_documents()
    subs = st.session_state.repo.get_subscriptions()
    events = st.session_state.repo.get_life_events()
    summary = st.session_state.repo.get_spending_summary()
    expiring = st.session_state.repo.get_expiring_documents(days_ahead=30)
    
    with col1:
        st.metric("Documents", len(docs), delta=f"{len(expiring)} expiring" if expiring else None, delta_color="inverse")
    with col2:
        st.metric("Subscriptions", len(subs))
    with col3:
        st.metric("Monthly Spend", f"${summary['monthly_total']:.2f}")
    with col4:
        active_events = [e for e in events if e.status != "completed"]
        st.metric("Active Events", len(active_events))
    
    st.divider()
    
    # Two column layout for details
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Documents section
        st.markdown("### Documents")
        if docs:
            for doc in sorted(docs, key=lambda d: d.expiry_date)[:5]:
                days = doc.days_until_expiry()
                if days < 0:
                    status = ":material/error: EXPIRED"
                elif days <= 7:
                    status = f":material/error: {days}d"
                elif days <= 30:
                    status = f":material/warning: {days}d"
                elif days <= 90:
                    status = f":material/schedule: {days}d"
                else:
                    status = f":material/check_circle: {days}d"
                
                st.markdown(f"**{doc.name}** ({doc.category}) - {status}")
            
            if len(docs) > 5:
                st.caption(f"...and {len(docs) - 5} more documents")
        else:
            st.info("No documents tracked yet. Try: 'My passport expires March 2026'")
        
        st.markdown("### Life Events")
        if events:
            for event in events:
                completed, total = event.get_progress()
                pct = event.get_progress_percentage()
                days_left = (event.target_date - date.today()).days
                
                with st.expander(f"**{event.title}** - {completed}/{total} tasks ({days_left}d left)", expanded=False):
                    st.progress(pct / 100)
                    
                    # Group tasks by category
                    tasks_by_category = {}
                    for item in event.checklist_items:
                        cat = (item.category or "general").replace("_", " ").title()
                        if cat not in tasks_by_category:
                            tasks_by_category[cat] = []
                        tasks_by_category[cat].append(item)
                    
                    for category, items in tasks_by_category.items():
                        st.markdown(f"**{category}**")
                        for item in items:
                            icon = ":material/check_circle:" if item.is_completed else ":material/radio_button_unchecked:"
                            if item.description:
                                st.markdown(f"{icon} **{item.title}**  \n{item.description}")
                            else:
                                st.markdown(f"{icon} **{item.title}**")
        else:
            st.info("No life events. Try: 'I'm moving next month'")
    
    with col_right:
        # Subscriptions section
        st.markdown("### Subscriptions")
        if subs:
            # Group by category
            categories = {}
            for sub in subs:
                cat = sub.category.title()
                if cat not in categories:
                    categories[cat] = {"count": 0, "total": 0}
                categories[cat]["count"] += 1
                categories[cat]["total"] += sub.get_monthly_cost()
            
            for cat, data in sorted(categories.items(), key=lambda x: x[1]["total"], reverse=True):
                st.markdown(f"**{cat}**: {data['count']} sub(s) - ${data['total']:.2f}/mo")
            
            st.divider()
            st.markdown(f"**Total:** ${summary['monthly_total']:.2f}/month")
            st.markdown(f"**Yearly:** ${summary['yearly_total']:.2f}/year")
            
            # Free trials
            trials = [s for s in subs if s.is_free_trial]
            if trials:
                st.markdown("#### Free Trials")
                for trial in trials:
                    if trial.trial_end_date:
                        days = (trial.trial_end_date - date.today()).days
                        if days <= 3:
                            st.error(f"{trial.service_name}: {days}d left!")
                        else:
                            st.warning(f"{trial.service_name}: {days}d left")
        else:
            st.info("No subscriptions tracked. Try: 'I subscribe to Netflix for $15.99/month'")
