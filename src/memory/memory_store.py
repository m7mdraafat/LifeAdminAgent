"""
Persistent memory store for Life Admin Assistant.
Enables long-term memory across conversation sessions.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    user_id: str
    memory_type: str  # "fact", "preference", "context", "summary"
    content: str
    metadata: Dict[str, Any]
    importance: float  # 0.0 to 1.0
    created_at: str
    last_accessed: str
    access_count: int = 0


class MemoryStore:
    """
    Persistent memory store for maintaining context across sessions.
    
    Memory Types:
    - fact: User facts (e.g., "User has 2 children")
    - preference: User preferences (e.g., "User prefers email reminders")
    - context: Important conversation context
    - summary: Session summaries
    """
    
    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for safe database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """Create memory tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Long-term memory table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                importance REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER DEFAULT 0
            )
            """)
            
            # Session summaries table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_topics TEXT,
                actions_taken TEXT,
                created_at TEXT NOT NULL
            )
            """)
            
            # Create indexes
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_user_type 
            ON memories(user_id, memory_type)
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_importance 
            ON memories(user_id, importance DESC)
            """)
    
    def add_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = "fact",
        metadata: Optional[Dict] = None,
        importance: float = 0.5
    ) -> MemoryEntry:
        """Add a new memory entry."""
        import uuid
        
        now = datetime.now().isoformat()
        memory = MemoryEntry(
            id=str(uuid.uuid4()),
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
            importance=min(max(importance, 0.0), 1.0),
            created_at=now,
            last_accessed=now,
            access_count=0
        )
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO memories 
            (id, user_id, memory_type, content, metadata, importance, created_at, last_accessed, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.user_id,
                memory.memory_type,
                memory.content,
                json.dumps(memory.metadata),
                memory.importance,
                memory.created_at,
                memory.last_accessed,
                memory.access_count
            ))
        
        return memory
    
    def get_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 20,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """Retrieve memories for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if memory_type:
                cursor.execute("""
                SELECT * FROM memories 
                WHERE user_id = ? AND memory_type = ? AND importance >= ?
                ORDER BY importance DESC, last_accessed DESC
                LIMIT ?
                """, (user_id, memory_type, min_importance, limit))
            else:
                cursor.execute("""
                SELECT * FROM memories 
                WHERE user_id = ? AND importance >= ?
                ORDER BY importance DESC, last_accessed DESC
                LIMIT ?
                """, (user_id, min_importance, limit))
            
            memories = []
            for row in cursor.fetchall():
                memories.append(MemoryEntry(
                    id=row["id"],
                    user_id=row["user_id"],
                    memory_type=row["memory_type"],
                    content=row["content"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    importance=row["importance"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                    access_count=row["access_count"]
                ))
            
            # Update access timestamps
            if memories:
                memory_ids = [m.id for m in memories]
                placeholders = ",".join(["?" for _ in memory_ids])
                cursor.execute(f"""
                UPDATE memories 
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id IN ({placeholders})
                """, [datetime.now().isoformat()] + memory_ids)
            
            return memories
    
    def get_relevant_context(self, user_id: str, query: str, limit: int = 5) -> str:
        """Get relevant memories formatted as context for the agent."""
        # Get high-importance facts and preferences
        facts = self.get_memories(user_id, "fact", limit=limit, min_importance=0.3)
        prefs = self.get_memories(user_id, "preference", limit=3, min_importance=0.5)
        
        # Get most recent session summary
        summaries = self._get_recent_summaries(user_id, limit=1)
        
        context_parts = []
        
        if facts:
            context_parts.append("**Known facts about user:**")
            for f in facts:
                context_parts.append(f"- {f.content}")
        
        if prefs:
            context_parts.append("\n**User preferences:**")
            for p in prefs:
                context_parts.append(f"- {p.content}")
        
        if summaries:
            context_parts.append(f"\n**Last session summary:** {summaries[0]['summary']}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def save_session_summary(
        self,
        user_id: str,
        summary: str,
        key_topics: List[str],
        actions_taken: List[str]
    ) -> None:
        """Save a session summary for long-term context."""
        import uuid
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO session_summaries 
            (id, user_id, summary, key_topics, actions_taken, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                user_id,
                summary,
                json.dumps(key_topics),
                json.dumps(actions_taken),
                datetime.now().isoformat()
            ))
    
    def _get_recent_summaries(self, user_id: str, limit: int = 3) -> List[Dict]:
        """Get recent session summaries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM session_summaries 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """, (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_importance(self, memory_id: str, importance: float) -> bool:
        """Update the importance of a memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE memories SET importance = ? WHERE id = ?
            """, (min(max(importance, 0.0), 1.0), memory_id))
            return cursor.rowcount > 0
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0
    
    def cleanup_old_memories(self, user_id: str, days_old: int = 90, keep_important: bool = True):
        """Remove old, low-importance memories."""
        from datetime import timedelta
        
        cutoff = (datetime.now() - timedelta(days=days_old)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if keep_important:
                cursor.execute("""
                DELETE FROM memories 
                WHERE user_id = ? AND last_accessed < ? AND importance < 0.7
                """, (user_id, cutoff))
            else:
                cursor.execute("""
                DELETE FROM memories 
                WHERE user_id = ? AND last_accessed < ?
                """, (user_id, cutoff))
            
            return cursor.rowcount
