"""
Subscription tracking tools for the Life Admin Assistant.
Track recurring payments, free trials, and calculate spending.
"""

from datetime import date, datetime
from typing import Annotated, Optional

from ..database.repository.repository import Repository
from ..database.models.Subsciption import Subscription


# Shared repository instance
_repository: Optional[Repository] = None


def get_repository() -> Repository:
    """Get or create the repository instance."""
    global _repository
    if _repository is None:
        _repository = Repository()
    return _repository


def set_repository(repo: Repository):
    """Set the repository instance."""
    global _repository
    _repository = repo


# ============================================================
# TOOL FUNCTIONS
# ============================================================

def add_subscription(
    service_name: Annotated[str, "Name of the service (e.g., 'Netflix', 'Spotify', 'Gym')"],
    cost: Annotated[float, "Cost per billing cycle (e.g., 15.99)"],
    renewal_date: Annotated[str, "Next billing/renewal date in YYYY-MM-DD format"],
    billing_cycle: Annotated[str, "Billing frequency: 'monthly', 'yearly', or 'weekly'"] = "monthly",
    category: Annotated[str, "Category: 'streaming', 'software', 'fitness', 'gaming', 'news', 'storage', 'education', or 'other'"] = "other",
    is_free_trial: Annotated[bool, "Whether this is a free trial"] = False,
    trial_end_date: Annotated[Optional[str], "When the free trial ends (YYYY-MM-DD), if applicable"] = None,
    notes: Annotated[str, "Any additional notes"] = ""
) -> str:
    """
    Add a new subscription to track recurring payments.
    Helps monitor spending and avoid surprise charges.
    """
    try:
        renewal = date.fromisoformat(renewal_date)
        trial_end = date.fromisoformat(trial_end_date) if trial_end_date else None
        
        # Validate billing cycle
        valid_cycles = ["weekly", "monthly", "yearly"]
        if billing_cycle.lower() not in valid_cycles:
            billing_cycle = "monthly"
        
        # Validate category
        valid_categories = [
            "streaming", "software", "fitness", "gaming", 
            "news", "storage", "education", "utilities", "other"
        ]
        if category.lower() not in valid_categories:
            category = "other"
        
        subscription = Subscription(
            service_name=service_name,
            cost=cost,
            renewal_date=renewal,
            billing_cycle=billing_cycle.lower(),
            category=category.lower(),
            is_free_trial=is_free_trial,
            trial_end_date=trial_end,
            notes=notes
        )
        
        repo = get_repository()
        saved = repo.save_subscription(subscription)
        
        # Calculate monthly cost for display
        monthly = saved.get_monthly_cost()
        yearly = monthly * 12
        
        if is_free_trial and trial_end:
            days_left = (trial_end - date.today()).days
            return (
                f"✅ Free trial tracked!\n"
                f"💳 {saved.service_name} ({saved.category})\n"
                f"🆓 Trial ends: {trial_end.strftime('%B %d, %Y')} ({days_left} days left)\n"
                f"💰 After trial: ${cost:.2f}/{billing_cycle}\n"
                f"🔔 I'll remind you before the trial ends!"
            )
        else:
            return (
                f"✅ Subscription saved!\n"
                f"💳 {saved.service_name} ({saved.category})\n"
                f"💰 ${cost:.2f}/{billing_cycle} (${monthly:.2f}/month, ${yearly:.2f}/year)\n"
                f"📅 Next billing: {renewal.strftime('%B %d, %Y')}"
            )
            
    except ValueError as e:
        return f"❌ Error: Invalid date format. Please use YYYY-MM-DD."
    except Exception as e:
        return f"❌ Error saving subscription: {str(e)}"


def list_subscriptions(
    category: Annotated[Optional[str], "Filter by category (optional)"] = None,
    include_inactive: Annotated[bool, "Include cancelled/inactive subscriptions"] = False
) -> str:
    """
    List all tracked subscriptions with their costs and status.
    """
    try:
        repo = get_repository()
        subscriptions = repo.get_subscriptions(active_only=not include_inactive)
        
        if not subscriptions:
            return "📭 No subscriptions found. Add some to start tracking your spending!"
        
        lines = [f"💳 **Your Subscriptions** ({len(subscriptions)} total)\n"]
        
        total_monthly = 0
        trials = []
        
        for sub in subscriptions:
            if sub.is_free_trial:
                trials.append(sub)
                lines.append(f"• 🆓 {sub.service_name} - FREE TRIAL")
                if sub.trial_end_date:
                    days = (sub.trial_end_date - date.today()).days
                    lines.append(f"     Trial ends in {days} days (${sub.cost}/{sub.billing_cycle} after)")
            else:
                monthly = sub.get_monthly_cost()
                total_monthly += monthly
                lines.append(f"• {sub.service_name} ({sub.category}) - ${sub.cost}/{sub.billing_cycle}")
        
        lines.append(f"\n💰 **Total: ${total_monthly:.2f}/month** (${total_monthly * 12:.2f}/year)")
        
        if trials:
            lines.append(f"⚠️ {len(trials)} free trial(s) to watch!")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Error retrieving subscriptions: {str(e)}"


def get_spending_summary() -> str:
    """
    Get a detailed breakdown of subscription spending by category.
    Shows monthly and yearly totals.
    """
    try:
        repo = get_repository()
        summary = repo.get_spending_summary()
        
        if summary["subscription_count"] == 0:
            return "📭 No active subscriptions to summarize. Add some to track your spending!"
        
        lines = [
            "📊 **Subscription Spending Summary**\n",
            f"💰 **Monthly Total: ${summary['monthly_total']:.2f}**",
            f"📅 **Yearly Total: ${summary['yearly_total']:.2f}**",
            f"📋 Active subscriptions: {summary['subscription_count']}",
        ]
        
        if summary.get("free_trial_count", 0) > 0:
            lines.append(f"🆓 Free trials: {summary['free_trial_count']}")
        
        if summary.get("by_category"):
            lines.append("\n📂 **By Category:**")
            # Sort by cost descending
            sorted_cats = sorted(
                summary["by_category"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            for cat, amount in sorted_cats:
                pct = (amount / summary['monthly_total'] * 100) if summary['monthly_total'] > 0 else 0
                lines.append(f"  • {cat.title()}: ${amount:.2f}/month ({pct:.0f}%)")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Error calculating spending: {str(e)}"


def get_trial_alerts(
    days_ahead: Annotated[int, "Days to look ahead for ending trials"] = 7
) -> str:
    """
    Get alerts for free trials ending soon.
    Helps avoid unexpected charges.
    """
    try:
        repo = get_repository()
        trials = repo.get_free_trials()
        
        if not trials:
            return "✅ No active free trials to monitor."
        
        ending_soon = []
        active = []
        
        for trial in trials:
            if trial.trial_end_date:
                days = (trial.trial_end_date - date.today()).days
                if days <= days_ahead:
                    ending_soon.append((trial, days))
                else:
                    active.append((trial, days))
        
        lines = [f"🆓 **Free Trial Status**\n"]
        
        if ending_soon:
            lines.append("🚨 **ENDING SOON:**")
            for trial, days in sorted(ending_soon, key=lambda x: x[1]):
                if days < 0:
                    lines.append(f"  ⚠️ {trial.service_name} - ENDED {abs(days)} days ago!")
                elif days == 0:
                    lines.append(f"  🔴 {trial.service_name} - ENDS TODAY! (${trial.cost}/{trial.billing_cycle})")
                else:
                    lines.append(f"  🟠 {trial.service_name} - {days} days left (${trial.cost}/{trial.billing_cycle} after)")
            lines.append("")
        
        if active:
            lines.append("✅ **Active Trials:**")
            for trial, days in active:
                lines.append(f"  🟢 {trial.service_name} - {days} days remaining")
        
        if not ending_soon and not active:
            return "✅ No free trials currently active."
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Error checking trials: {str(e)}"


def delete_subscription(
    service_name: Annotated[str, "Name of the subscription to delete"]
) -> str:
    """
    Delete a subscription from tracking (e.g., after cancelling).
    """
    try:
        repo = get_repository()
        subscriptions = repo.get_subscriptions(active_only=False)
        
        # Find by name (case-insensitive)
        matching = [s for s in subscriptions if s.service_name.lower() == service_name.lower()]
        
        if not matching:
            return f"❌ Subscription '{service_name}' not found."
        
        sub = matching[0]
        repo.delete_subscription(sub.id)
        
        return f"✅ Removed '{sub.service_name}' from tracking."
        
    except Exception as e:
        return f"❌ Error deleting subscription: {str(e)}"


# ============================================================
# EXPORT
# ============================================================

SUBSCRIPTION_TOOLS = [
    add_subscription,
    list_subscriptions,
    get_spending_summary,
    get_trial_alerts,
    delete_subscription
]