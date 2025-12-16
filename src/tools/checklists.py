"""
Life Event checklist tools for the Life Admin Assistant.
Track major life events with step-by-step checklists.
"""

from datetime import date, datetime
from typing import Annotated, Optional, List
import json
from pathlib import Path

from ..database.repository.repository import Repository
from ..database.models.LifeEvent import LifeEvent, ChecklistItem


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
# CHECKLIST TEMPLATES - Pre-defined checklists for common events
# ============================================================

CHECKLIST_TEMPLATES = {
    "moving": {
        "title": "Moving Checklist",
        "items": [
            {"title": "Give notice to current landlord", "category": "4_weeks_before"},
            {"title": "Research moving companies or rent truck", "category": "4_weeks_before"},
            {"title": "Start packing non-essentials", "category": "4_weeks_before"},
            {"title": "Change address with post office", "category": "2_weeks_before"},
            {"title": "Transfer utilities (electric, gas, internet)", "category": "2_weeks_before"},
            {"title": "Update address with bank and employer", "category": "2_weeks_before"},
            {"title": "Notify insurance companies", "category": "2_weeks_before"},
            {"title": "Pack remaining items", "category": "1_week_before"},
            {"title": "Confirm moving day details", "category": "1_week_before"},
            {"title": "Prepare essentials box (toiletries, snacks, chargers)", "category": "1_week_before"},
            {"title": "Do final walkthrough of old place", "category": "moving_day"},
            {"title": "Take photos before leaving old place", "category": "moving_day"},
            {"title": "Hand over keys", "category": "moving_day"},
            {"title": "Update driver's license address", "category": "after_move"},
            {"title": "Register to vote at new address", "category": "after_move"},
            {"title": "Find new local services (doctor, dentist)", "category": "after_move"},
        ]
    },
    "new_job": {
        "title": "New Job Checklist",
        "items": [
            {"title": "Give notice to current employer", "category": "before_start"},
            {"title": "Gather required documents (ID, SSN, bank info)", "category": "before_start"},
            {"title": "Complete any background check paperwork", "category": "before_start"},
            {"title": "Plan commute and parking", "category": "before_start"},
            {"title": "Prepare professional wardrobe", "category": "before_start"},
            {"title": "Review company handbook and policies", "category": "first_week"},
            {"title": "Complete HR onboarding paperwork", "category": "first_week"},
            {"title": "Set up direct deposit", "category": "first_week"},
            {"title": "Enroll in benefits (health, 401k)", "category": "first_week"},
            {"title": "Meet team members and key contacts", "category": "first_week"},
            {"title": "Set up workstation and tools", "category": "first_week"},
            {"title": "Schedule 1:1 with manager", "category": "first_month"},
            {"title": "Learn team processes and workflows", "category": "first_month"},
            {"title": "Complete required training", "category": "first_month"},
        ]
    },
    "buying_car": {
        "title": "Buying a Car Checklist",
        "items": [
            {"title": "Determine budget", "category": "research"},
            {"title": "Research car models and reviews", "category": "research"},
            {"title": "Check credit score", "category": "research"},
            {"title": "Get pre-approved for auto loan", "category": "financing"},
            {"title": "Compare dealer vs bank financing", "category": "financing"},
            {"title": "Visit dealerships and test drive", "category": "shopping"},
            {"title": "Negotiate price", "category": "shopping"},
            {"title": "Review all paperwork carefully", "category": "purchase"},
            {"title": "Verify VIN and title", "category": "purchase"},
            {"title": "Get car insurance", "category": "purchase"},
            {"title": "Register vehicle and get plates", "category": "after_purchase"},
            {"title": "Schedule first service appointment", "category": "after_purchase"},
        ]
    },
    "buying_home": {
        "title": "Buying a Home Checklist",
        "items": [
            {"title": "Check credit score and improve if needed", "category": "preparation"},
            {"title": "Save for down payment and closing costs", "category": "preparation"},
            {"title": "Get pre-approved for mortgage", "category": "preparation"},
            {"title": "Hire a real estate agent", "category": "preparation"},
            {"title": "Define must-haves and nice-to-haves", "category": "house_hunting"},
            {"title": "Tour homes and attend open houses", "category": "house_hunting"},
            {"title": "Research neighborhoods", "category": "house_hunting"},
            {"title": "Make an offer", "category": "offer"},
            {"title": "Negotiate terms", "category": "offer"},
            {"title": "Get home inspection", "category": "due_diligence"},
            {"title": "Review inspection report", "category": "due_diligence"},
            {"title": "Get home appraisal", "category": "due_diligence"},
            {"title": "Finalize mortgage", "category": "closing"},
            {"title": "Get homeowner's insurance", "category": "closing"},
            {"title": "Do final walkthrough", "category": "closing"},
            {"title": "Sign closing documents", "category": "closing"},
            {"title": "Get keys!", "category": "closing"},
        ]
    },
    "getting_married": {
        "title": "Getting Married Checklist",
        "items": [
            {"title": "Set a budget", "category": "planning"},
            {"title": "Choose a date", "category": "planning"},
            {"title": "Create guest list", "category": "planning"},
            {"title": "Book venue", "category": "booking"},
            {"title": "Hire photographer", "category": "booking"},
            {"title": "Book caterer", "category": "booking"},
            {"title": "Send save-the-dates", "category": "invitations"},
            {"title": "Send invitations", "category": "invitations"},
            {"title": "Get marriage license", "category": "legal"},
            {"title": "Plan honeymoon", "category": "planning"},
            {"title": "Arrange transportation", "category": "logistics"},
            {"title": "Confirm all vendors", "category": "final_week"},
            {"title": "Update name on documents (if changing)", "category": "after_wedding"},
            {"title": "Update beneficiaries", "category": "after_wedding"},
        ]
    },
    "travel": {
        "title": "Travel Planning Checklist",
        "items": [
            {"title": "Set travel budget", "category": "planning"},
            {"title": "Research destination", "category": "planning"},
            {"title": "Check passport expiry (6+ months)", "category": "documents"},
            {"title": "Apply for visa if needed", "category": "documents"},
            {"title": "Book flights", "category": "booking"},
            {"title": "Book accommodation", "category": "booking"},
            {"title": "Get travel insurance", "category": "booking"},
            {"title": "Create itinerary", "category": "planning"},
            {"title": "Notify bank of travel dates", "category": "before_trip"},
            {"title": "Arrange pet/house sitter", "category": "before_trip"},
            {"title": "Pack luggage", "category": "before_trip"},
            {"title": "Check in online", "category": "day_before"},
            {"title": "Confirm reservations", "category": "day_before"},
        ]
    },
    "custom": {
        "title": "Custom Checklist",
        "items": []
    }
}


# ============================================================
# TOOL FUNCTIONS
# ============================================================

def get_available_events() -> str:
    """
    List all supported life event types with descriptions.
    Call this to see what checklists are available.
    """
    lines = ["📋 **Available Life Event Checklists**\n"]
    
    event_descriptions = {
        "moving": "🏠 Moving to a new place",
        "new_job": "💼 Starting a new job",
        "buying_car": "🚗 Purchasing a vehicle",
        "buying_home": "🏡 Buying a house/property",
        "getting_married": "💒 Wedding planning",
        "travel": "✈️ Planning a major trip",
    }
    
    for event_type, description in event_descriptions.items():
        template = CHECKLIST_TEMPLATES.get(event_type, {})
        item_count = len(template.get("items", []))
        lines.append(f"• **{event_type}** - {description} ({item_count} tasks)")
    
    lines.append("\n💡 Say something like: 'I'm moving next month' to start a checklist!")
    
    return "\n".join(lines)


def start_life_event(
    event_type: Annotated[str, "Type of event: 'moving', 'new_job', 'buying_car', 'buying_home', 'getting_married', 'travel'"],
    title: Annotated[str, "Custom title for this event (e.g., 'Moving to NYC')"],
    target_date: Annotated[str, "Target/deadline date in YYYY-MM-DD format"],
    notes: Annotated[str, "Any additional notes"] = "",
    custom_tasks_json: Annotated[str, "JSON array of custom tasks (for 'custom' event type)"] = ""
) -> str:
    """
    Start tracking a new life event with a checklist.
    
    - For standard events (moving, new_job, etc.), uses pre-built templates
    - For 'custom' events, either provide custom_tasks_json or start with empty checklist
    - If the title suggests specialized needs (e.g., "Training for X"), consider using 'custom'
    
    For custom events, you can add tasks later using add_task_to_checklist.
    """
    try:
        target = date.fromisoformat(target_date)
        
        # Validate event type
        event_type_lower = event_type.lower()
        if event_type_lower not in CHECKLIST_TEMPLATES:
            available = ", ".join(CHECKLIST_TEMPLATES.keys())
            return f"❌ Unknown event type '{event_type}'. Available: {available}"
        
        template = CHECKLIST_TEMPLATES[event_type_lower]
        
        # For custom events with provided tasks
        if event_type_lower == "custom" and custom_tasks_json:
            try:
                tasks_data = json.loads(custom_tasks_json)
                checklist_items = [
                    ChecklistItem(
                        id=f"item_{i}",
                        title=task.get("title", "Untitled"),
                        description=task.get("description", ""),
                        category=task.get("category", ""),
                        order=i,
                        is_completed=False
                    )
                    for i, task in enumerate(tasks_data)
                ]
            except json.JSONDecodeError:
                return "❌ Invalid JSON format for custom tasks."
        else:
            # Use template items
            checklist_items = [
                ChecklistItem(
                    id=f"item_{i}",
                    title=item["title"],
                    category=item.get("category", ""),
                    order=i,
                    is_completed=False
                )
                for i, item in enumerate(template["items"])
            ]
        
        # Create the life event
        event = LifeEvent(
            event_type=event_type_lower,
            title=title,
            target_date=target,
            checklist_items=checklist_items,
            status="planning",
            notes=notes
        )
        
        repo = get_repository()
        saved = repo.save_life_event(event)
        
        days_until = (target - date.today()).days
        
        response = (
            f"✅ Life event created!\n\n"
            f"📋 **{saved.title}**\n"
            f"📅 Target: {target.strftime('%B %d, %Y')} ({days_until} days away)\n"
            f"📝 {len(checklist_items)} tasks\n\n"
        )
        
        if event_type_lower == "custom" and not custom_tasks_json:
            response += (
                "This is a custom event with an empty checklist.\n"
                "You can add tasks by saying things like:\n"
                "• 'Add task: Complete module 1'\n"
                "• 'Add these tasks to my checklist: [list of tasks]'"
            )
        else:
            response += f"Say 'show my {event_type} checklist' to see all tasks!"
        
        return response
        
    except ValueError:
        return "❌ Invalid date format. Use YYYY-MM-DD."
    except Exception as e:
        return f"❌ Error creating life event: {str(e)}"

def get_checklist(
    event_type: Annotated[Optional[str], "Filter by event type (optional)"] = None
) -> str:
    """
    Show the checklist for a life event with progress.
    """
    try:
        repo = get_repository()
        events = repo.get_life_events(status="planning") + repo.get_life_events(status="in_progress")
        
        if event_type:
            events = [e for e in events if e.event_type == event_type.lower()]
        
        if not events:
            return "📭 No active life events. Start one by telling me about a major event you're planning!"
        
        lines = []
        
        for event in events:
            completed, total = event.get_progress()
            pct = event.get_progress_percentage()
            days = (event.target_date - date.today()).days
            
            lines.append(f"📋 **{event.title}**")
            lines.append(f"📅 Target: {event.target_date.strftime('%B %d, %Y')} ({days} days)")
            lines.append(f"📊 Progress: {completed}/{total} tasks ({pct:.0f}%)\n")
            
            # Group by category
            categories = {}
            for item in event.checklist_items:
                cat = item.category or "other"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)
            
            for cat, items in categories.items():
                cat_display = cat.replace("_", " ").title()
                lines.append(f"**{cat_display}:**")
                for item in items:
                    status = "✅" if item.is_completed else "⬜"
                    lines.append(f"  {status} {item.title}")
                lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Error retrieving checklist: {str(e)}"


def mark_task_complete(
    task_title: Annotated[str, "Title or partial title of the task to mark complete"],
    event_type: Annotated[Optional[str], "Event type to narrow down search"] = None
) -> str:
    """
    Mark a checklist task as complete.
    """
    try:
        repo = get_repository()
        events = repo.get_life_events(status="planning") + repo.get_life_events(status="in_progress")
        
        if event_type:
            events = [e for e in events if e.event_type == event_type.lower()]
        
        if not events:
            return "❌ No active life events found."
        
        # Search for matching task
        for event in events:
            for item in event.checklist_items:
                if task_title.lower() in item.title.lower():
                    if item.is_completed:
                        return f"ℹ️ '{item.title}' is already completed!"
                    
                    item.is_completed = True
                    item.completed_at = datetime.now()
                    event.status = "in_progress"
                    repo.save_life_event(event)
                    
                    completed, total = event.get_progress()
                    pct = event.get_progress_percentage()
                    
                    response = f"✅ Marked complete: **{item.title}**\n"
                    response += f"📊 Progress: {completed}/{total} ({pct:.0f}%)"
                    
                    if completed == total:
                        event.status = "completed"
                        repo.save_life_event(event)
                        response += "\n\n🎉 **Congratulations! All tasks completed!**"
                    
                    return response
        
        return f"❌ Task '{task_title}' not found. Try 'show checklist' to see all tasks."
        
    except Exception as e:
        return f"❌ Error marking task: {str(e)}"


def list_life_events() -> str:
    """
    List all life events being tracked.
    """
    try:
        repo = get_repository()
        events = repo.get_life_events()
        
        if not events:
            return "📭 No life events being tracked. Tell me about a major event you're planning!"
        
        lines = ["📋 **Your Life Events**\n"]
        
        for event in events:
            completed, total = event.get_progress()
            pct = event.get_progress_percentage()
            days = (event.target_date - date.today()).days
            
            status_emoji = {
                "planning": "📝",
                "in_progress": "🔄",
                "completed": "✅",
                "cancelled": "❌"
            }.get(event.status, "📋")
            
            lines.append(f"{status_emoji} **{event.title}** ({event.event_type})")
            lines.append(f"   📅 {event.target_date.strftime('%b %d, %Y')} ({days} days)")
            lines.append(f"   📊 {completed}/{total} tasks ({pct:.0f}%)\n")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Error listing events: {str(e)}"

def delete_life_event(
    event_type: Annotated[str, "Type of event to delete (e.g., 'moving', 'new_job')"]
) -> str:
    """
    Delete/cancel a life event.
    Removes the event and its checklist from tracking.
    """
    try:
        repo = get_repository()
        events = repo.get_life_events()
        
        # Find matching event
        matching = [e for e in events if e.event_type.lower() == event_type.lower()]
        
        if not matching:
            return f"❌ No '{event_type}' life event found."
        
        # Delete all matching events (in case of duplicates)
        deleted_count = 0
        for event in matching:
            if repo.delete_life_event(event.id):
                deleted_count += 1
        
        if deleted_count > 0:
            return f"✅ Deleted {deleted_count} '{event_type}' event(s)."
        else:
            return f"❌ Failed to delete '{event_type}' event."
        
    except Exception as e:
        return f"❌ Error deleting life event: {str(e)}"

def add_task_to_checklist(
    event_identifier: Annotated[str, "Event type or partial title to identify which event"],
    task_title: Annotated[str, "Title of the task to add"],
    category: Annotated[str, "Category/phase for the task (e.g., 'week_1', 'preparation')"] = "general",
    description: Annotated[str, "Detailed description of the task"] = ""
) -> str:
    """
    Add a new task to an existing life event checklist.
    Useful for customizing checklists or adding missing tasks.
    """
    try:
        repo = get_repository()
        events = repo.get_life_events()
        
        # Find matching event by type or title
        matching = [
            e for e in events 
            if event_identifier.lower() in e.event_type.lower() 
            or event_identifier.lower() in e.title.lower()
        ]
        
        if not matching:
            return f"❌ No event found matching '{event_identifier}'. Use 'list my life events' to see all."
        
        event = matching[0]
        
        # Create new task
        new_task = ChecklistItem(
            id=f"item_{len(event.checklist_items)}",
            title=task_title,
            description=description,
            category=category,
            order=len(event.checklist_items),
            is_completed=False
        )
        
        event.checklist_items.append(new_task)
        repo.save_life_event(event)
        
        return (
            f"✅ Added task to '{event.title}':\n"
            f"• {task_title}\n"
            f"📊 Total tasks: {len(event.checklist_items)}"
        )
        
    except Exception as e:
        return f"❌ Error adding task: {str(e)}"


def remove_task_from_checklist(
    event_identifier: Annotated[str, "Event type or partial title"],
    task_identifier: Annotated[str, "Task title or partial title to remove"]
) -> str:
    """
    Remove a task from a life event checklist.
    Useful for removing incorrect or irrelevant tasks.
    """
    try:
        repo = get_repository()
        events = repo.get_life_events()
        
        # Find event
        matching_events = [
            e for e in events 
            if event_identifier.lower() in e.event_type.lower() 
            or event_identifier.lower() in e.title.lower()
        ]
        
        if not matching_events:
            return f"❌ No event found matching '{event_identifier}'."
        
        event = matching_events[0]
        
        # Find task to remove
        task_to_remove = None
        for task in event.checklist_items:
            if task_identifier.lower() in task.title.lower():
                task_to_remove = task
                break
        
        if not task_to_remove:
            return f"❌ No task found matching '{task_identifier}' in '{event.title}'."
        
        # Remove task
        event.checklist_items.remove(task_to_remove)
        
        # Reorder remaining tasks
        for i, task in enumerate(event.checklist_items):
            task.order = i
        
        repo.save_life_event(event)
        
        return (
            f"✅ Removed task from '{event.title}':\n"
            f"• {task_to_remove.title}\n"
            f"📊 Remaining tasks: {len(event.checklist_items)}"
        )
        
    except Exception as e:
        return f"❌ Error removing task: {str(e)}"


def update_task_in_checklist(
    event_identifier: Annotated[str, "Event type or partial title"],
    task_identifier: Annotated[str, "Current task title or partial title"],
    new_title: Annotated[str, "New title for the task"],
    new_description: Annotated[str, "New description (optional)"] = "",
    new_category: Annotated[str, "New category (optional)"] = ""
) -> str:
    """
    Update/edit a task in a life event checklist.
    Change the title, description, or category of an existing task.
    """
    try:
        repo = get_repository()
        events = repo.get_life_events()
        
        # Find event
        matching_events = [
            e for e in events 
            if event_identifier.lower() in e.event_type.lower() 
            or event_identifier.lower() in e.title.lower()
        ]
        
        if not matching_events:
            return f"❌ No event found matching '{event_identifier}'."
        
        event = matching_events[0]
        
        # Find task to update
        task_to_update = None
        for task in event.checklist_items:
            if task_identifier.lower() in task.title.lower():
                task_to_update = task
                break
        
        if not task_to_update:
            return f"❌ No task found matching '{task_identifier}' in '{event.title}'."
        
        # Update task
        old_title = task_to_update.title
        task_to_update.title = new_title
        if new_description:
            task_to_update.description = new_description
        if new_category:
            task_to_update.category = new_category
        
        repo.save_life_event(event)
        
        return (
            f"✅ Updated task in '{event.title}':\n"
            f"Old: {old_title}\n"
            f"New: {new_title}"
        )
        
    except Exception as e:
        return f"❌ Error updating task: {str(e)}"


def replace_entire_checklist(
    event_identifier: Annotated[str, "Event type or partial title"],
    tasks_json: Annotated[str, "JSON array of tasks with title, category, description fields"]
) -> str:
    """
    Replace the entire checklist for a life event with new tasks.
    Useful when the AI needs to regenerate a completely new checklist.
    
    Example tasks_json format:
    [
        {"title": "Task 1", "category": "week1", "description": "Details"},
        {"title": "Task 2", "category": "week2", "description": "More details"}
    ]
    """
    try:
        import json
        
        repo = get_repository()
        events = repo.get_life_events()
        
        # Find event
        matching_events = [
            e for e in events 
            if event_identifier.lower() in e.event_type.lower() 
            or event_identifier.lower() in e.title.lower()
        ]
        
        if not matching_events:
            return f"❌ No event found matching '{event_identifier}'."
        
        event = matching_events[0]
        
        # Parse new tasks
        try:
            new_tasks_data = json.loads(tasks_json)
        except json.JSONDecodeError:
            return "❌ Invalid JSON format for tasks."
        
        # Create new checklist items
        new_checklist = []
        for i, task_data in enumerate(new_tasks_data):
            new_checklist.append(ChecklistItem(
                id=f"item_{i}",
                title=task_data.get("title", "Untitled task"),
                description=task_data.get("description", ""),
                category=task_data.get("category", "general"),
                order=i,
                is_completed=False
            ))
        
        # Replace checklist
        event.checklist_items = new_checklist
        repo.save_life_event(event)
        
        return (
            f"✅ Replaced checklist for '{event.title}':\n"
            f"📝 New checklist has {len(new_checklist)} tasks\n"
            f"Say 'show my checklist' to see all tasks!"
        )
        
    except Exception as e:
        return f"❌ Error replacing checklist: {str(e)}"

def find_similar_events(query: str) -> list:
    """Find events with similar names using fuzzy matching."""
    from difflib import SequenceMatcher
    
    events = _checklist_repo.get_life_events()
    similar = []
    
    for event in events:
        ratio = SequenceMatcher(None, query.lower(), event.title.lower()).ratio()
        if ratio > 0.5:  # 50% similarity threshold
            similar.append({"event": event, "similarity": ratio})
    
    return sorted(similar, key=lambda x: x["similarity"], reverse=True)


def update_life_event_title(
    event_id: Annotated[str, "The ID of the life event to update"],
    new_title: Annotated[str, "The new title for the life event"]
) -> str:
    """
    Update the title of an existing life event.
    Use this when the user wants to rename a life event or fix a typo.
    """
    repo = get_checklist_repository()
    
    try:
        # Find the event
        events = repo.get_life_events()
        event = None
        for e in events:
            if e.id == event_id:
                event = e
                break
        
        if not event:
            return f"❌ Life event with ID '{event_id}' not found."
        
        old_title = event.title
        event.title = new_title
        repo.save_life_event(event)
        
        return (
            f"✅ Updated life event title:\n"
            f"📝 Old: '{old_title}'\n"
            f"📝 New: '{new_title}'"
        )
        
    except Exception as e:
        return f"❌ Error updating life event: {str(e)}"


# ============================================================
# EXPORT
# ============================================================

CHECKLIST_TOOLS = [
    get_available_events,
    start_life_event,
    get_checklist,
    mark_task_complete,
    list_life_events,
    delete_life_event,
    add_task_to_checklist,
    remove_task_from_checklist,
    update_task_in_checklist,
    replace_entire_checklist,
    find_similar_events,
    update_life_event_title,
]