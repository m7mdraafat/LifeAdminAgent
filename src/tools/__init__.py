"""Tools module - Functions the AI agent can call."""

from .documents import (
    DOCUMENT_TOOLS,
    add_document,
    list_documents,
    get_expiring_documents,
    delete_document,
    set_repository as set_document_repository
)

from .subscriptions import (
    SUBSCRIPTION_TOOLS,
    add_subscription,
    list_subscriptions,
    get_spending_summary,
    get_trial_alerts,
    delete_subscription,
    set_repository as set_subscription_repository
)

from .checklists import (
    CHECKLIST_TOOLS,
    get_available_events,
    start_life_event,
    get_checklist,
    mark_task_complete,
    list_life_events,
    delete_life_event,
    set_repository as set_checklist_repository
)

# Combined tools list
ALL_TOOLS = DOCUMENT_TOOLS + SUBSCRIPTION_TOOLS + CHECKLIST_TOOLS

__all__ = [
    "DOCUMENT_TOOLS",
    "SUBSCRIPTION_TOOLS", 
    "CHECKLIST_TOOLS",
    "ALL_TOOLS",
    "set_document_repository",
    "set_subscription_repository",
    "set_checklist_repository"
]