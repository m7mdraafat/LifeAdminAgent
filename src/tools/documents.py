"""
Document tracking tools for the Life Admin Assistant.
These functions are called by the AI agent to manage user documents.
"""

from datetime import date, datetime
from typing import Annotated, Optional, List

from ..database.repository.repository import Repository
from ..database.models.Document import Document

# Create a global repository instance (Singleton pattern).
# (In production, consider dependency injection instead)

_repository: Optional[Repository] = None

def get_repository() -> Repository:
    """Get or create the global repository instance."""
    global _repository
    if _repository is None:
        _repository = Repository()
    return _repository


def set_repository(repo: Repository):
    """Set the global repository instance (for testing or customization)."""
    global _repository
    _repository = repo


# =========================================================
# TOOL FUNCTIONS - These are what the AI can call
# =========================================================

def add_document(
    name: Annotated[str, "Name of the document (e.g., 'Passport', 'Driver's License')"],
    category: Annotated[str, "Category of the document (e.g., 'identification', 'insurance', etc.)"],
    expiry_date: Annotated[str, "Expiry date in YYYY-MM-DD format"],
    family_member: Annotated[Optional[str], "Family member the document belongs to, or 'self'"] = "self",
    notes: Annotated[Optional[str], "Additional notes about the document"] = "",
) -> str:
    """
    Add a new document to track its expiry date.
    The assistant will remind you before the document expires.
    """

    try:
        expiry = date.fromisoformat(expiry_date)

        valid_categories = [
            "identification", "insurance", "warranty", 
            "medical", "financial", "vehicle", "property", "other"
        ]

        if category.lower() not in valid_categories:
            category = "other"
        
        document = Document(
            name=name,
            category=category.lower(),
            expiry_date=expiry,
            family_member=family_member or "self",
            notes=notes or ""
        )

        repo = get_repository()
        saved_doc = repo.save_document(document)

        days_left = document.days_until_expiry()

        # Return confirmation message
        return (
            f"✅ Document saved successfully!\n"
            f"📄 {saved_doc.name} ({saved_doc.category})\n"
            f"📅 Expires: {saved_doc.expiry_date.strftime('%B %d, %Y')}\n"
            f"⏰ {days_left} days remaining\n"
            f"🔔 Reminders set for: 90, 30, and 7 days before expiry"
        )
    
    except ValueError as e:
        return f"❌ Error: Invalid date format. Please use YYYY-MM-DD."
    except Exception as e:
        return f"❌ Error: Could not save document. {str(e)}"
    
def list_documents(
    category: Annotated[Optional[str], "Filter by category (optional)"] = None,
    family_member: Annotated[Optional[str], "Filter by family member (optional)"] = None
) -> str:
    """
    List all tracked documents, optionally filtered by category or family member.
    """
    try:
        repo = get_repository()
        documents = repo.get_documents(category=category)
        
        if not documents:
            return "📭 No documents found. Add some documents to track!"
        
        # Build response
        lines = [f"📄 **Your Documents** ({len(documents)} total)\n"]
        
        for doc in documents:
            status = doc.get_status()
            lines.append(f"• {doc.name} ({doc.category}) - {status}")
            if doc.notes:
                lines.append(f"  📝 {doc.notes}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Error retrieving documents: {str(e)}"


def get_expiring_documents(
    days_ahead: Annotated[int, "Number of days to look ahead (default: 30)"] = 30
) -> str:
    """
    Get documents expiring within the specified number of days.
    Useful for checking what needs attention soon.
    """
    try:
        repo = get_repository()
        documents = repo.get_expiring_documents(days_ahead=days_ahead)
        
        if not documents:
            return f"✅ No documents expiring in the next {days_ahead} days. You're all set!"
        
        # Group by urgency
        expired = []
        urgent = []      # <= 7 days
        warning = []     # <= 30 days
        upcoming = []    # > 30 days
        
        for doc in documents:
            days = doc.days_until_expiry()
            if days < 0:
                expired.append((doc, days))
            elif days <= 7:
                urgent.append((doc, days))
            elif days <= 30:
                warning.append((doc, days))
            else:
                upcoming.append((doc, days))
        
        lines = [f"📋 **Documents Expiring Soon** (next {days_ahead} days)\n"]
        
        if expired:
            lines.append("⚠️ **EXPIRED:**")
            for doc, days in expired:
                lines.append(f"  🔴 {doc.name} - expired {abs(days)} days ago!")
            lines.append("")
        
        if urgent:
            lines.append("🚨 **URGENT (≤7 days):**")
            for doc, days in urgent:
                lines.append(f"  🔴 {doc.name} - {days} days left")
            lines.append("")
        
        if warning:
            lines.append("⚠️ **WARNING (≤30 days):**")
            for doc, days in warning:
                lines.append(f"  🟠 {doc.name} - {days} days left")
            lines.append("")
        
        if upcoming:
            lines.append("📅 **UPCOMING:**")
            for doc, days in upcoming:
                lines.append(f"  🟡 {doc.name} - {days} days left")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Error checking expiring documents: {str(e)}"


def delete_document(
    document_name: Annotated[str, "Name of the document to delete"]
) -> str:
    """
    Delete a document from tracking.
    """
    try:
        repo = get_repository()
        documents = repo.get_documents()
        
        # Find document by name (case-insensitive)
        matching = [d for d in documents if d.name.lower() == document_name.lower()]
        
        if not matching:
            return f"❌ Document '{document_name}' not found. Use 'list documents' to see all tracked documents."
        
        doc = matching[0]
        repo.delete_document(doc.id)
        
        return f"✅ Deleted '{doc.name}' from tracking."
        
    except Exception as e:
        return f"❌ Error deleting document: {str(e)}"


# ========================================================
# EXPORT: Lost of tools the agent can use
# ========================================================

DOCUMENT_TOOLS = [
    add_document,
    list_documents,
    get_expiring_documents,
    delete_document,
]