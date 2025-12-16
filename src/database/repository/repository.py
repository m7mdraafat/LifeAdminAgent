import sqlite3
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager

from ..models.Document import Document
from ..models.LifeEvent import LifeEvent, ChecklistItem
from ..models.Subscription import Subscription

class Repository:
    """Database operations for Life Admin Assistant."""

    def __init__(self, db_path: str = "data/life_admin.db", user_id: str = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.user_id = user_id  # Current user's ID for data isolation
        self._init_database()
    
    def set_user(self, user_id: str):
        """Set the current user for data filtering."""
        self.user_id = user_id

    @contextmanager
    def _get_connection(self):
        """Context manager for safe database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row # Access columns by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        
    def _init_database(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Documents table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                family_member TEXT,
                name TEXT,
                category TEXT,
                expiry_date TEXT,
                reminder_days TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
                )
            """)
            
            # Migration: Add user_id column if it doesn't exist
            self._migrate_add_user_id_column(cursor, "documents")

            # Life events table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS life_events (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                event_type TEXT,
                title TEXT,
                target_date TEXT,
                checklist_items TEXT,
                status TEXT DEFAULT 'planning',
                notes TEXT,
                created_at TEXT
                )
            """)
            
            # Migration: Add user_id column if it doesn't exist
            self._migrate_add_user_id_column(cursor, "life_events")

            # Subscriptions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                service_name TEXT NOT NULL,
                cost REAL NOT NULL,
                renewal_date TEXT NOT NULL,
                billing_cycle TEXT DEFAULT 'monthly',
                category TEXT DEFAULT 'other',
                is_free_trial INTEGER DEFAULT 0,
                trial_end_date TEXT,
                is_active INTEGER DEFAULT 1,
                notes TEXT,
                created_at TEXT
                )
            """)
            
            # Migration: Add user_id column if it doesn't exist
            self._migrate_add_user_id_column(cursor, "subscriptions")
    
    def _migrate_add_user_id_column(self, cursor, table_name: str):
        """Add user_id column to existing tables if missing."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        if "user_id" not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN user_id TEXT")


    # DOCUMENT OPERATIONS

    def save_document(self, document: Document) -> Document:
        """Save or update a document."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO documents
            (id, user_id, name, category, expiry_date, reminder_days, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document.id,
                self.user_id,
                document.name,
                document.category,
                document.expiry_date.isoformat(),
                json.dumps(document.reminder_days),
                document.notes,
                document.created_at.isoformat(),
                datetime.now().isoformat()
            ))
        return document
    
    def get_documents(self, category: Optional[str] = None) -> List[Document]:
        """Get all documents for current user, optionally filtered by category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "SELECT * FROM documents WHERE user_id = ? AND category = ? ORDER BY expiry_date ASC",
                    (self.user_id, category)
                )
            else:
                cursor.execute(
                    "SELECT * FROM documents WHERE user_id = ? ORDER BY expiry_date ASC",
                    (self.user_id,)
                )
            return [self._row_to_document(row) for row in cursor.fetchall()]
        

    def get_expiring_documents(self, days_ahead: int = 30) -> List[Document]:
        """Get documents expiring within N days for current user."""
        end_date = date.today() + timedelta(days=days_ahead)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM documents
            WHERE user_id = ? AND DATE(expiry_date) <= DATE(?)
            ORDER BY expiry_date ASC
            """, (self.user_id, end_date.isoformat()))
            return [self._row_to_document(row) for row in cursor.fetchall()]
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID (only if owned by current user)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (document_id, self.user_id))
            return cursor.rowcount > 0
    
    def _row_to_document(self, row) -> Document:
        """Convert a database row to a Document object."""
        return Document(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            expiry_date=date.fromisoformat(row["expiry_date"]),
            family_member=row["family_member"] if "family_member" in row.keys() else "self",
            reminder_days=json.loads(row["reminder_days"]) if row["reminder_days"] else [90, 30, 7],
            notes=row["notes"] if row["notes"] else "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
        )
    # SUBSCRIPTION OPERATIONS

    def save_subscription(self, subscription: Subscription) -> Subscription:
        """Save or update a subscription."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO subscriptions
            (id, user_id, service_name, cost, renewal_date, billing_cycle, category,
             is_free_trial, trial_end_date, is_active, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subscription.id,
                self.user_id,
                subscription.service_name,
                subscription.cost,
                subscription.renewal_date.isoformat(),
                subscription.billing_cycle,
                subscription.category,
                int(subscription.is_free_trial),
                subscription.trial_end_date.isoformat() if subscription.trial_end_date else None,
                int(subscription.is_active),
                subscription.notes,
                subscription.created_at.isoformat()
            ))
        return subscription

    def get_subscriptions(self, active_only: bool = False) -> List[Subscription]:
        """Get all subscriptions for current user, optionally filtering only active ones."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute(
                    "SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1 ORDER BY renewal_date ASC",
                    (self.user_id,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY renewal_date ASC",
                    (self.user_id,)
                )
            return [self._row_to_subscription(row) for row in cursor.fetchall()]
    
    def get_free_trials(self) -> List[Subscription]:
        """Get all active free trials for current user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM subscriptions 
                WHERE user_id = ? AND is_free_trial = 1 AND is_active = 1
                ORDER BY trial_end_date ASC
            """, (self.user_id,))
            return [self._row_to_subscription(row) for row in cursor.fetchall()]

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription by ID (only if owned by current user)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscriptions WHERE id = ? AND user_id = ?", (subscription_id, self.user_id))
            return cursor.rowcount > 0
        
    def get_spending_summary(self) -> dict:
        """Calculate monthly/yearly spending on active subscriptions."""
        subscriptions = self.get_subscriptions(active_only=True)
        monthly_total = sum(
            sub.get_monthly_cost()
            for sub in subscriptions
            if not sub.is_free_trial
        )

        return {
            "monthly_total": round(monthly_total, 2),
            "yearly_total": round(monthly_total * 12, 2),
            "subscription_count": len(subscriptions)
        }
    
    def _row_to_subscription(self, row) -> Subscription:
        """Convert a database row to a Subscription object."""
        return Subscription(
            id=row["id"],
            service_name=row["service_name"],
            cost=row["cost"],
            renewal_date=date.fromisoformat(row["renewal_date"]),
            billing_cycle=row["billing_cycle"] if row["billing_cycle"] else "monthly",
            category=row["category"] if row["category"] else "other",
            is_free_trial=bool(row["is_free_trial"]),
            trial_end_date=date.fromisoformat(row["trial_end_date"]) if row["trial_end_date"] else None,
            is_active=bool(row["is_active"]),
            notes=row["notes"] if row["notes"] else "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
        )
    # LIFE EVENT OPERATIONS

    def save_life_event(self, event: LifeEvent) -> LifeEvent:
        """Save or update a life event."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO life_events
                (id, user_id, event_type, title, target_date, checklist_items, status, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    self.user_id,
                    event.event_type,
                    event.title,
                    event.target_date.isoformat(),
                    json.dumps([{
                        "id": item.id,
                        "title": item.title,
                        "description": item.description,
                        "is_completed": item.is_completed,
                        "category": item.category,
                        "order": item.order,
                        "completed_at": item.completed_at.isoformat() if item.completed_at else None
                    } for item in event.checklist_items]),
                    event.status,
                    event.notes,
                    event.created_at.isoformat(),
                ),
            )
        return event
    
    def update_checklist_item(self, event_id: str, item_id: str, completed: bool) -> bool:
        """Update a specific checklist item within a life event."""
        event = self.get_life_event(event_id)
        if not event:
            return False
        
        if completed:
            event.mark_item_completed(item_id)
        else:
            # mark incomplete logic
            pass

        self.save_life_event(event)
        return True
    
    def get_life_events(self, status: Optional[str] = None) -> List[LifeEvent]:
        """Get all life events for current user, optionally filtered by status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM life_events WHERE user_id = ? AND status = ? ORDER BY target_date ASC",
                    (self.user_id, status)
                )
            else:
                cursor.execute(
                    "SELECT * FROM life_events WHERE user_id = ? ORDER BY target_date ASC",
                    (self.user_id,)
                )
            return [self._row_to_life_event(row) for row in cursor.fetchall()]

    def get_life_event(self, event_id: str) -> Optional[LifeEvent]:
        """Get a single life event by ID (only if owned by current user)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM life_events WHERE id = ? AND user_id = ?", (event_id, self.user_id))
            row = cursor.fetchone()
            if row:
                return self._row_to_life_event(row)
            return None

    def _row_to_life_event(self, row) -> LifeEvent:
        """Convert a database row to a LifeEvent object."""
        import json
        
        # Parse checklist items from JSON
        checklist_data = json.loads(row["checklist_items"]) if row["checklist_items"] else []
        checklist_items = []
        
        for i, item in enumerate(checklist_data):
            checklist_items.append(ChecklistItem(
                id=item.get("id", f"item_{i}"),
                title=item["title"],
                description=item.get("description", ""),
                is_completed=item.get("is_completed", False),
                category=item.get("category", ""),
                order=item.get("order", i),
                completed_at=datetime.fromisoformat(item["completed_at"]) if item.get("completed_at") else None
            ))
        
        return LifeEvent(
            id=row["id"],
            event_type=row["event_type"],
            title=row["title"],
            target_date=date.fromisoformat(row["target_date"]),
            checklist_items=checklist_items,
            status=row["status"] if row["status"] else "planning",
            notes=row["notes"] if row["notes"] else "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
        )
        
    def delete_life_event(self, event_id: str) -> bool:
        """Delete a life event by ID (only if owned by current user)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM life_events WHERE id = ? AND user_id = ?", (event_id, self.user_id))
            return cursor.rowcount > 0