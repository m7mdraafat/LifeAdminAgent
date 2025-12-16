"""
Document data model for tracking important documents and their expiry dates.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List
import uuid

@dataclass
class Document:
    """
    Represents an important document that needs expiry tracking.
    Examples: Passport, Driver's License, Insurance Policy, etc.
    """

    # Required fields
    name: str
    category: str
    expiry_date: date

    ## auto-generated fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default"
    family_member: str = "self"
    reminder_days: List[int] = field(default_factory=lambda: [90, 30, 7])
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Valid categories
    VALID_CATEGORIES = [
        "identification", "insurance", "warranty",
        "medical", "financial", "vehicle", "property", "other"
    ]

    def days_until_expiry(self) -> int:
        """Calculate days remaining until the document expires."""
        delta = self.expiry_date - date.today()
        return delta.days
    
    def is_expired(self) -> bool:
        """Check if the document has already expired."""
        return self.days_until_expiry() < 0
    
    def get_status(self) -> str:
        """Get human-readable status with emoji."""
        days = self.days_until_expiry()
        if days < 0:
            return f"⚠️ EXPIRED ({abs(days)} days ago)"
        elif days <= 7:
            return f"🔴 URGENT: {days} days left"
        elif days <= 30:
            return f"🟠 WARNING: {days} days left"
        elif days <= 90:
            return f"🟡 UPCOMING: {days} days left"
        else:
            return f"🟢 OK: {days} days left"
        
    def to_dict(self) -> dict:
        """Convert Document instance to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "family_member": self.family_member,
            "name": self.name,
            "category": self.category,
            "expiry_date": self.expiry_date.isoformat(),
            "reminder_days": self.reminder_days,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        """Create Document from dictionary (when loading from DB)."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", "default"),
            family_member=data.get("family_member", "self"),
            name=data["name"],
            category=data["category"],
            expiry_date=date.fromisoformat(data["expiry_date"]),
            reminder_days=data.get("reminder_days", [90, 30, 7]),
            notes=data.get("notes", ""),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
        )
