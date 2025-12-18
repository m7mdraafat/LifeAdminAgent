"""
Memory-related tools for the Life Admin Assistant.
Allows the agent to remember and recall user information.
"""

from typing import Annotated, Optional, List

from ..memory import MemoryStore

# Shared memory store instance
_memory_store: Optional[MemoryStore] = None
_current_user_id: Optional[str] = None


def set_memory_context(memory_store: MemoryStore, user_id: str):
    """Set the memory store and user context."""
    global _memory_store, _current_user_id
    _memory_store = memory_store
    _current_user_id = user_id


def get_memory_store() -> Optional[MemoryStore]:
    """Get the current memory store."""
    return _memory_store


# ============================================================
# MEMORY TOOLS - Agent can call these to manage user memories
# ============================================================

def remember_user_fact(
    fact: Annotated[str, "A fact about the user to remember (e.g., 'User has 2 children', 'User's passport is from Germany')"],
    importance: Annotated[float, "How important is this fact (0.0 to 1.0). Higher = more likely to be recalled"] = 0.5
) -> str:
    """
    Store an important fact about the user for future reference.
    Use this when the user shares personal information that might be useful later.
    
    Examples:
    - User mentions they have family members
    - User shares preferences for reminders
    - User mentions their location or timezone
    """
    if not _memory_store or not _current_user_id:
        return "ℹ️ Memory is not enabled for this session."
    
    try:
        memory = _memory_store.add_memory(
            user_id=_current_user_id,
            content=fact,
            memory_type="fact",
            importance=importance
        )
        return f"✅ I'll remember that: {fact}"
    except Exception as e:
        return f"❌ Couldn't save that to memory: {str(e)}"


def remember_user_preference(
    preference: Annotated[str, "A preference to remember (e.g., 'User prefers email reminders', 'User likes brief responses')"],
    importance: Annotated[float, "Importance level (0.0 to 1.0)"] = 0.7
) -> str:
    """
    Store a user preference for personalization.
    Use this when the user expresses how they like things done.
    """
    if not _memory_store or not _current_user_id:
        return "ℹ️ Memory is not enabled for this session."
    
    try:
        memory = _memory_store.add_memory(
            user_id=_current_user_id,
            content=preference,
            memory_type="preference",
            importance=importance
        )
        return f"✅ I've noted your preference: {preference}"
    except Exception as e:
        return f"❌ Couldn't save preference: {str(e)}"


def recall_user_context(
    topic: Annotated[Optional[str], "Optional topic to filter memories by"] = None
) -> str:
    """
    Recall what you know about the user.
    Use this to check what facts and preferences have been stored.
    """
    if not _memory_store or not _current_user_id:
        return "ℹ️ Memory is not enabled for this session."
    
    try:
        facts = _memory_store.get_memories(_current_user_id, "fact", limit=10)
        prefs = _memory_store.get_memories(_current_user_id, "preference", limit=5)
        
        lines = ["📝 **What I remember about you:**\n"]
        
        if facts:
            lines.append("**Facts:**")
            for f in facts:
                lines.append(f"• {f.content}")
        else:
            lines.append("No facts stored yet.")
        
        if prefs:
            lines.append("\n**Preferences:**")
            for p in prefs:
                lines.append(f"• {p.content}")
        else:
            lines.append("\nNo preferences stored yet.")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error recalling memories: {str(e)}"


def forget_memory(
    memory_content: Annotated[str, "The content or partial content of the memory to forget"]
) -> str:
    """
    Remove a specific memory if the user requests it.
    Use this when the user wants you to forget something.
    """
    if not _memory_store or not _current_user_id:
        return "ℹ️ Memory is not enabled for this session."
    
    try:
        # Find matching memories
        all_memories = _memory_store.get_memories(_current_user_id, limit=50)
        matching = [m for m in all_memories if memory_content.lower() in m.content.lower()]
        
        if not matching:
            return f"❌ No memory found matching '{memory_content}'"
        
        deleted_count = 0
        for memory in matching:
            if _memory_store.delete_memory(memory.id):
                deleted_count += 1
        
        return f"✅ Removed {deleted_count} memory/memories related to '{memory_content}'"
    except Exception as e:
        return f"❌ Error removing memory: {str(e)}"


# ============================================================
# EXPORT
# ============================================================

MEMORY_TOOLS = [
    remember_user_fact,
    remember_user_preference,
    recall_user_context,
    forget_memory
]
