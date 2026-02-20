"""Repository pattern for data access."""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from terminal_todos.db.models import Email, Event, Note, Todo


class TodoRepository:
    """Repository for Todo operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        content: str,
        note_id: Optional[int] = None,
        priority: int = 0,
        due_date: Optional[datetime] = None
    ) -> Todo:
        """Create a new todo."""
        todo = Todo(content=content, note_id=note_id, priority=priority, due_date=due_date)
        self.session.add(todo)
        self.session.commit()
        self.session.refresh(todo)
        return todo

    def get(self, todo_id: int) -> Optional[Todo]:
        """Get a todo by ID."""
        return self.session.query(Todo).filter(Todo.id == todo_id).first()

    def list_active(self, limit: int = 100) -> List[Todo]:
        """List active (not completed) todos."""
        return (
            self.session.query(Todo)
            .filter(Todo.completed == False)
            .order_by(Todo.priority.desc(), Todo.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_completed(self, limit: int = 100) -> List[Todo]:
        """List completed todos."""
        return (
            self.session.query(Todo)
            .filter(Todo.completed == True)
            .order_by(Todo.completed_at.desc())
            .limit(limit)
            .all()
        )

    def list_completed_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 100) -> List[Todo]:
        """List todos completed within a date range."""
        return (
            self.session.query(Todo)
            .filter(
                Todo.completed == True,
                Todo.completed_at.isnot(None),
                Todo.completed_at >= start_date,
                Todo.completed_at < end_date
            )
            .order_by(Todo.completed_at.desc())
            .limit(limit)
            .all()
        )

    def list_all(self, limit: int = 100) -> List[Todo]:
        """List all todos."""
        return (
            self.session.query(Todo)
            .order_by(Todo.completed.asc(), Todo.priority.desc(), Todo.created_at.desc())
            .limit(limit)
            .all()
        )

    def complete(self, todo_id: int) -> Optional[Todo]:
        """Mark a todo as completed and remove from focus."""
        todo = self.get(todo_id)
        if todo:
            todo.completed = True
            todo.completed_at = datetime.utcnow()
            todo.focus_order = None  # Auto-remove from focus
            self.session.commit()
            self.session.refresh(todo)
        return todo

    def uncomplete(self, todo_id: int) -> Optional[Todo]:
        """Mark a todo as not completed (does not restore focus)."""
        todo = self.get(todo_id)
        if todo:
            todo.completed = False
            todo.completed_at = None
            # Note: focus_order stays None, user must re-add to focus
            self.session.commit()
            self.session.refresh(todo)
        return todo

    def delete(self, todo_id: int) -> bool:
        """Delete a todo."""
        todo = self.get(todo_id)
        if todo:
            self.session.delete(todo)
            self.session.commit()
            return True
        return False

    def get_by_content(self, content: str) -> Optional[Todo]:
        """Get a todo by exact content match."""
        return self.session.query(Todo).filter(Todo.content == content).first()

    def search_by_content(self, query: str, limit: int = 10) -> List[Todo]:
        """Search todos by content (simple LIKE query)."""
        return (
            self.session.query(Todo)
            .filter(Todo.content.ilike(f"%{query}%"))
            .limit(limit)
            .all()
        )

    def list_due_today(self) -> List[Todo]:
        """List todos due today."""
        from datetime import date
        today = date.today()
        return (
            self.session.query(Todo)
            .filter(
                Todo.completed == False,
                Todo.due_date.isnot(None),
                Todo.due_date >= datetime(today.year, today.month, today.day),
                Todo.due_date < datetime(today.year, today.month, today.day + 1)
            )
            .order_by(Todo.priority.desc(), Todo.due_date.asc())
            .all()
        )

    def list_due_this_week(self) -> List[Todo]:
        """List todos due this week."""
        from datetime import date, timedelta
        today = date.today()
        week_end = today + timedelta(days=7)
        return (
            self.session.query(Todo)
            .filter(
                Todo.completed == False,
                Todo.due_date.isnot(None),
                Todo.due_date >= datetime(today.year, today.month, today.day),
                Todo.due_date < datetime(week_end.year, week_end.month, week_end.day)
            )
            .order_by(Todo.priority.desc(), Todo.due_date.asc())
            .all()
        )

    def list_overdue(self) -> List[Todo]:
        """List overdue todos."""
        from datetime import date
        today = date.today()
        return (
            self.session.query(Todo)
            .filter(
                Todo.completed == False,
                Todo.due_date.isnot(None),
                Todo.due_date < datetime(today.year, today.month, today.day)
            )
            .order_by(Todo.priority.desc(), Todo.due_date.asc())
            .all()
        )

    def list_no_due_date(self) -> List[Todo]:
        """List todos with no due date."""
        return (
            self.session.query(Todo)
            .filter(Todo.completed == False, Todo.due_date.is_(None))
            .order_by(Todo.priority.desc(), Todo.created_at.desc())
            .all()
        )

    def update_due_date(self, todo_id: int, due_date: Optional[datetime]) -> Optional[Todo]:
        """Update the due date of a todo."""
        todo = self.get(todo_id)
        if todo:
            todo.due_date = due_date
            self.session.commit()
            self.session.refresh(todo)
        return todo

    def list_by_date_range(self, start_date: datetime, end_date: datetime, include_completed: bool = False) -> List[Todo]:
        """List todos within a date range."""
        query = self.session.query(Todo).filter(
            Todo.due_date.isnot(None),
            Todo.due_date >= start_date,
            Todo.due_date < end_date
        )

        if not include_completed:
            query = query.filter(Todo.completed == False)

        return query.order_by(Todo.priority.desc(), Todo.due_date.asc()).all()

    def list_focused(self) -> List[Todo]:
        """List todos in the focus list, ordered by focus_order."""
        return (
            self.session.query(Todo)
            .filter(Todo.completed == False, Todo.focus_order.isnot(None))
            .order_by(Todo.focus_order.asc())
            .all()
        )

    def add_to_focus(self, todo_id: int) -> Optional[Todo]:
        """Add a todo to the focus list with next available order."""
        todo = self.get(todo_id)
        if not todo:
            return None

        # Get max focus_order
        max_order = self.session.query(func.max(Todo.focus_order)).scalar() or 0

        todo.focus_order = max_order + 1
        self.session.commit()
        self.session.refresh(todo)
        return todo

    def remove_from_focus(self, todo_id: int) -> Optional[Todo]:
        """Remove a todo from the focus list."""
        todo = self.get(todo_id)
        if todo:
            todo.focus_order = None
            self.session.commit()
            self.session.refresh(todo)
        return todo

    def get_focus_count(self) -> int:
        """Get count of todos currently in focus list."""
        return (
            self.session.query(Todo)
            .filter(Todo.completed == False, Todo.focus_order.isnot(None))
            .count()
        )

    def clear_focus(self) -> int:
        """Remove all todos from focus list. Returns count cleared."""
        count = (
            self.session.query(Todo)
            .filter(Todo.focus_order.isnot(None))
            .update({Todo.focus_order: None})
        )
        self.session.commit()
        return count


class NoteRepository:
    """Repository for Note operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self, content: str, title: Optional[str] = None, note_type: str = "general"
    ) -> Note:
        """Create a new note."""
        note = Note(content=content, title=title, note_type=note_type)
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def get(self, note_id: int) -> Optional[Note]:
        """Get a note by ID."""
        return self.session.query(Note).filter(Note.id == note_id).first()

    def list_all(self, limit: int = 100) -> List[Note]:
        """List all notes."""
        return (
            self.session.query(Note)
            .order_by(Note.created_at.desc())
            .limit(limit)
            .all()
        )

    def delete(self, note_id: int) -> bool:
        """Delete a note."""
        note = self.get(note_id)
        if note:
            self.session.delete(note)
            self.session.commit()
            return True
        return False

    def search_by_content(self, query: str, limit: int = 10) -> List[Note]:
        """Search notes by content (simple LIKE query)."""
        return (
            self.session.query(Note)
            .filter(Note.content.ilike(f"%{query}%") | Note.title.ilike(f"%{query}%"))
            .limit(limit)
            .all()
        )

    def list_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 100) -> List[Note]:
        """List notes created within a date range."""
        return (
            self.session.query(Note)
            .filter(
                Note.created_at >= start_date,
                Note.created_at < end_date
            )
            .order_by(Note.created_at.desc())
            .limit(limit)
            .all()
        )


class EmailRepository:
    """Repository for Email operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        subject: str,
        body: str,
        recipient: Optional[str] = None,
        context_note_ids: Optional[List[int]] = None,
        template_type: Optional[str] = None,
    ) -> Email:
        """Create a new email draft."""
        email = Email(
            subject=subject,
            body=body,
            recipient=recipient,
            context_note_ids=json.dumps(context_note_ids) if context_note_ids else None,
            template_type=template_type,
        )
        self.session.add(email)
        self.session.commit()
        self.session.refresh(email)
        return email

    def get(self, email_id: int) -> Optional[Email]:
        """Get email by ID."""
        return self.session.query(Email).filter_by(id=email_id).first()

    def list_recent(self, limit: int = 10) -> List[Email]:
        """List recent emails."""
        return (
            self.session.query(Email)
            .order_by(Email.created_at.desc())
            .limit(limit)
            .all()
        )

    def delete(self, email_id: int) -> bool:
        """Delete an email."""
        email = self.get(email_id)
        if email:
            self.session.delete(email)
            self.session.commit()
            return True
        return False


class EventRepository:
    """Repository for Event logging."""

    def __init__(self, session: Session):
        self.session = session

    def log_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: int,
        details: Optional[dict] = None,
    ) -> Event:
        """Log an event."""
        event = Event(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details) if details else None,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def get_recent(self, limit: int = 50) -> List[Event]:
        """Get recent events."""
        return (
            self.session.query(Event)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_entity(
        self, entity_type: str, entity_id: int, limit: int = 50
    ) -> List[Event]:
        """Get events for a specific entity."""
        return (
            self.session.query(Event)
            .filter(Event.entity_type == entity_type, Event.entity_id == entity_id)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )
