"""
Notification tools for the Life Admin Assistant.
Send email reminders for expiring documents, ending trials, and upcoming events.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, timedelta
from typing import Annotated, Optional, List

from ..database.repository.repository import Repository
from ..config import get_secret

logger = logging.getLogger(__name__)

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
# EMAIL CONFIGURATION
# ============================================================

def _get_email_config() -> dict:
    """Get email configuration from environment/secrets."""
    return {
        "smtp_server": get_secret("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(get_secret("SMTP_PORT", "587")),
        "sender_email": get_secret("SENDER_EMAIL", ""),
        "sender_password": get_secret("SENDER_PASSWORD", ""),
        "recipient_email": get_secret("NOTIFICATION_EMAIL", ""),
    }


def _send_email(subject: str, body: str, to_email: str = None) -> bool:
    """
    Send an email notification.
    Returns True if successful, False otherwise.
    """
    config = _get_email_config()
    
    if not config["sender_email"] or not config["sender_password"]:
        logger.warning("Email not configured. Set SENDER_EMAIL and SENDER_PASSWORD.")
        return False
    
    recipient = to_email or config["recipient_email"]
    if not recipient:
        logger.warning("No recipient email configured.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = config["sender_email"]
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["sender_email"], config["sender_password"])
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {recipient}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


# ============================================================
# TOOL FUNCTIONS
# ============================================================

def check_notification_status() -> str:
    """
    Check if email notifications are configured and working.
    Use this to verify notification settings.
    """
    config = _get_email_config()
    
    lines = ["📧 **Notification Status**\n"]
    
    if config["sender_email"]:
        lines.append(f"✅ Sender email: {config['sender_email'][:3]}...{config['sender_email'].split('@')[-1]}")
    else:
        lines.append("❌ Sender email: Not configured")
    
    if config["sender_password"]:
        lines.append("✅ Sender password: Configured")
    else:
        lines.append("❌ Sender password: Not configured")
    
    if config["recipient_email"]:
        lines.append(f"✅ Notification recipient: {config['recipient_email'][:3]}...{config['recipient_email'].split('@')[-1]}")
    else:
        lines.append("❌ Notification recipient: Not configured")
    
    lines.append(f"\n📮 SMTP Server: {config['smtp_server']}:{config['smtp_port']}")
    
    if not config["sender_email"] or not config["sender_password"]:
        lines.append("\n💡 **To enable notifications:**")
        lines.append("Add these to your .env file or Streamlit secrets:")
        lines.append("```")
        lines.append("SENDER_EMAIL=your_email@gmail.com")
        lines.append("SENDER_PASSWORD=your_app_password")
        lines.append("NOTIFICATION_EMAIL=recipient@example.com")
        lines.append("```")
    
    return "\n".join(lines)


def send_expiry_reminder(
    days_ahead: Annotated[int, "Days to look ahead for expiring items"] = 30,
    email: Annotated[Optional[str], "Override recipient email address"] = None
) -> str:
    """
    Send an email reminder about documents and trials expiring soon.
    Combines all urgent items into a single notification.
    """
    repo = get_repository()
    
    # Get expiring documents
    expiring_docs = repo.get_expiring_documents(days_ahead=days_ahead)
    
    # Get ending trials
    trials = repo.get_free_trials()
    ending_trials = []
    for trial in trials:
        if trial.trial_end_date:
            days = (trial.trial_end_date - date.today()).days
            if days <= days_ahead:
                ending_trials.append((trial, days))
    
    # Get upcoming life events
    events = repo.get_life_events(status="planning") + repo.get_life_events(status="in_progress")
    upcoming_events = []
    for event in events:
        days = (event.target_date - date.today()).days
        if 0 <= days <= days_ahead:
            upcoming_events.append((event, days))
    
    if not expiring_docs and not ending_trials and not upcoming_events:
        return f"✅ No items requiring attention in the next {days_ahead} days!"
    
    # Build email content
    subject = f"🔔 Life Admin Alert: {len(expiring_docs) + len(ending_trials) + len(upcoming_events)} items need attention"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">🏠 Life Admin Assistant</h2>
        <p>Here's your summary of items needing attention in the next {days_ahead} days:</p>
    """
    
    if expiring_docs:
        body += """
        <h3 style="color: #d63031;">📄 Expiring Documents</h3>
        <ul>
        """
        for doc in expiring_docs:
            days = doc.days_until_expiry()
            urgency = "🔴" if days <= 7 else "🟠" if days <= 30 else "🟡"
            body += f"<li>{urgency} <strong>{doc.name}</strong> - {days} days left</li>"
        body += "</ul>"
    
    if ending_trials:
        body += """
        <h3 style="color: #e17055;">💳 Free Trials Ending</h3>
        <ul>
        """
        for trial, days in ending_trials:
            body += f"<li>🆓 <strong>{trial.service_name}</strong> - {days} days left (${trial.cost}/{trial.billing_cycle} after)</li>"
        body += "</ul>"
    
    if upcoming_events:
        body += """
        <h3 style="color: #0984e3;">🎯 Upcoming Life Events</h3>
        <ul>
        """
        for event, days in upcoming_events:
            completed, total = event.get_progress()
            pct = event.get_progress_percentage()
            body += f"<li>📋 <strong>{event.title}</strong> - {days} days away ({pct:.0f}% complete)</li>"
        body += "</ul>"
    
    body += """
        <hr style="border: 1px solid #ddd;">
        <p style="color: #666; font-size: 12px;">
            Sent by Life Admin Assistant 🤖
        </p>
    </body>
    </html>
    """
    
    # Send email
    if _send_email(subject, body, email):
        return (
            f"✅ **Reminder sent!**\n\n"
            f"📧 Email sent with:\n"
            f"• {len(expiring_docs)} expiring document(s)\n"
            f"• {len(ending_trials)} ending trial(s)\n"
            f"• {len(upcoming_events)} upcoming event(s)"
        )
    else:
        return (
            f"⚠️ **Could not send email notification.**\n\n"
            f"Items found:\n"
            f"• {len(expiring_docs)} expiring document(s)\n"
            f"• {len(ending_trials)} ending trial(s)\n"
            f"• {len(upcoming_events)} upcoming event(s)\n\n"
            f"Please configure email settings. Use 'check notification status' for details."
        )


def send_test_notification(
    email: Annotated[str, "Email address to send test notification to"]
) -> str:
    """
    Send a test notification to verify email configuration is working.
    """
    subject = "🧪 Life Admin Assistant - Test Notification"
    body = """
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #00b894;">✅ Test Successful!</h2>
        <p>Your Life Admin Assistant email notifications are working correctly.</p>
        <p>You'll receive alerts for:</p>
        <ul>
            <li>📄 Expiring documents</li>
            <li>💳 Free trials ending</li>
            <li>🎯 Upcoming life events</li>
        </ul>
        <hr style="border: 1px solid #ddd;">
        <p style="color: #666; font-size: 12px;">
            Sent by Life Admin Assistant 🤖
        </p>
    </body>
    </html>
    """
    
    if _send_email(subject, body, email):
        return f"✅ Test email sent successfully to {email}!"
    else:
        return f"❌ Failed to send test email. Please check your email configuration."


def get_daily_digest() -> str:
    """
    Generate a daily digest of all items needing attention.
    Does not send email - just returns the summary.
    """
    repo = get_repository()
    today = date.today()
    
    lines = [f"📬 **Daily Digest** - {today.strftime('%B %d, %Y')}\n"]
    
    # Urgent items (next 7 days)
    lines.append("### 🚨 Urgent (Next 7 Days)")
    
    urgent_docs = repo.get_expiring_documents(days_ahead=7)
    if urgent_docs:
        for doc in urgent_docs:
            days = doc.days_until_expiry()
            if days < 0:
                lines.append(f"• ⚠️ **{doc.name}** - EXPIRED {abs(days)} days ago!")
            else:
                lines.append(f"• 🔴 **{doc.name}** - {days} days left")
    
    trials = repo.get_free_trials()
    for trial in trials:
        if trial.trial_end_date:
            days = (trial.trial_end_date - today).days
            if days <= 7:
                lines.append(f"• 🆓 **{trial.service_name}** trial ends in {days} days")
    
    if len(lines) == 2:  # Only header, no urgent items
        lines.append("• ✅ No urgent items!")
    
    # Upcoming (8-30 days)
    lines.append("\n### 📅 Coming Up (8-30 Days)")
    
    upcoming_docs = [d for d in repo.get_expiring_documents(days_ahead=30) 
                     if 7 < d.days_until_expiry() <= 30]
    for doc in upcoming_docs:
        lines.append(f"• 🟠 **{doc.name}** - {doc.days_until_expiry()} days")
    
    if not upcoming_docs:
        lines.append("• ✅ Nothing in this period")
    
    # Active life events
    lines.append("\n### 🎯 Active Life Events")
    events = repo.get_life_events(status="planning") + repo.get_life_events(status="in_progress")
    
    if events:
        for event in events[:5]:
            completed, total = event.get_progress()
            pct = event.get_progress_percentage()
            days = (event.target_date - today).days
            lines.append(f"• **{event.title}** - {days} days, {pct:.0f}% complete")
    else:
        lines.append("• No active events")
    
    # Spending summary
    summary = repo.get_spending_summary()
    lines.append(f"\n### 💰 Monthly Spending: ${summary['monthly_total']:.2f}")
    
    return "\n".join(lines)


# ============================================================
# EXPORT
# ============================================================

NOTIFICATION_TOOLS = [
    check_notification_status,
    send_expiry_reminder,
    send_test_notification,
    get_daily_digest,
]
