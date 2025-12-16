from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import uuid

@dataclass
class Subscription:
    """Track subscriptions like Netflix, Gym, Spotify, etc."""

    # Required fields
    service_name: str
    cost: float
    renewal_date: date

    # Optional/default fields
    billing_cycle: str = "monthly"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default"
    category: str = "other"
    is_free_trial: bool = False
    trial_end_date: Optional[date] = None
    is_active: bool = True
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def get_monthly_cost(self) -> float:
        """Normalize cost to monthly for comparison."""
        if self.billing_cycle == "yearly":
            return self.cost / 12
        elif self.billing_cycle == "weekly":
            return self.cost * 4.33  
        else:
            return self.cost
        
    def get_yearly_cost(self) -> float:
        """Calculate total yearly cost."""
        return self.get_monthly_cost() * 12
    
    def days_until_trial_ends(self) -> Optional[int]:
        """For free trials, how many days left?"""
        if not self.is_free_trial or not self.trial_end_date:
            return None
        return (self.trial_end_date - date.today()).days
    
    def get_status(self) -> str:
        """Human-readable status of the subscription."""
        if self.is_free_trial and self.trial_end_date:
            days = self.days_until_trial_ends()
            if days < 2:
                return f"🔴 TRIAL ENDING SOON: {days} days left"
            return f"🟢 TRIAL ACTIVE: {days} days left"
        return f"🟢 ACTIVE - ${self.cost}/{self.billing_cycle}"
        