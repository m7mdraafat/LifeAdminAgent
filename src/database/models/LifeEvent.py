from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List
import uuid

@dataclass
class ChecklistItem:
    """A single task in a life event checklist."""
    id: str
    title: str
    description: str = ""
    is_completed: bool = False
    category: str = ""
    order: int = 0
    completed_at: Optional[datetime] = None

    def mark_completed(self):
        """Mark the checklist item as completed."""
        self.is_completed = True
        self.completed_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert ChecklistItem instance to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "is_completed": self.is_completed,
            "category": self.category,
            "order": self.order,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
@dataclass
class LifeEvent:
    """Major life event with checklist tracking."""

    event_type: str
    title: str
    target_date: date
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    checklist_items: List[ChecklistItem] = field(default_factory=list)
    status: str = "planning"
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    VALID_EVENT_TYPES = [
        "moving", "new_job", "buying_car", "buying_home",
        "getting_married", "having_baby", "travel", "other"
    ]

    def get_progress(self) -> tuple[int, int]:
        """Return (completed, totoal) counts."""
        total = len(self.checklist_items)
        completed = sum(1 for item in self.checklist_items if item.is_completed)
        return completed, total
    
    def get_progress_percentage(self) -> float:
        """Return completion percentage."""
        completed, total = self.get_progress()
        return (completed / total * 100) if total > 0 else 0.0
    
    def add_checklist_item(self, item: ChecklistItem):
        """Add a checklist item to the life event."""
        item = ChecklistItem(
            id=str(uuid.uuid4()),
            title=item.title,
            description=item.description,
            order=len(self.checklist_items)
        )

        self.checklist_items.append(item)
        return item
    
    def mark_item_completed(self, item_id: str) -> bool:
        """Mark a checklist item as completed by ID."""
        for item in self.checklist_items:
            if item.id == item_id:
                item.mark_completed()
                return True
        return False
