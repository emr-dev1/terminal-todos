"""Todo service with database and vector store operations."""

from typing import Any, Dict, List, Optional

from terminal_todos.db.connection import get_session
from terminal_todos.db.models import Todo
from terminal_todos.db.repositories import EventRepository, TodoRepository
from terminal_todos.core.sync_service import SyncService
from terminal_todos.vector.search import SemanticSearch


class TodoService:
    """High-level service for todo operations."""

    def __init__(self):
        self.session = get_session()
        self.todo_repo = TodoRepository(self.session)
        self.event_repo = EventRepository(self.session)
        self.sync_service = SyncService()
        self.search = SemanticSearch(self.sync_service.vector_store)

    def create_todo(
        self,
        content: str,
        note_id: Optional[int] = None,
        priority: int = 0,
        due_date: Optional[Any] = None
    ) -> Todo:
        """Create a new todo and sync to vector store."""
        from datetime import datetime

        # Convert due_date if it's a string
        if isinstance(due_date, str):
            try:
                due_date = datetime.fromisoformat(due_date)
            except:
                due_date = None

        # Create in database
        todo = self.todo_repo.create(content=content, note_id=note_id, priority=priority, due_date=due_date)

        # Sync to vector store
        self.sync_service.sync_todo(todo.id)

        # Log event
        self.event_repo.log_event(
            event_type="todo_created",
            entity_type="todo",
            entity_id=todo.id,
            details={"content": content, "note_id": note_id},
        )

        return todo

    def get_todo(self, todo_id: int) -> Optional[Todo]:
        """Get a todo by ID."""
        return self.todo_repo.get(todo_id)

    def list_active(self, limit: int = 100) -> List[Todo]:
        """List active todos."""
        return self.todo_repo.list_active(limit=limit)

    def list_completed(self, limit: int = 100) -> List[Todo]:
        """List completed todos."""
        return self.todo_repo.list_completed(limit=limit)

    def list_completed_by_date_range(self, start_date, end_date, limit: int = 100) -> List[Todo]:
        """List todos completed within a date range."""
        return self.todo_repo.list_completed_by_date_range(start_date, end_date, limit=limit)

    def list_all(self, limit: int = 100) -> List[Todo]:
        """List all todos."""
        return self.todo_repo.list_all(limit=limit)

    def complete_todo(self, todo_id: int) -> Optional[Todo]:
        """Mark a todo as completed and sync."""
        todo = self.todo_repo.complete(todo_id)

        if todo:
            # Sync to vector store (updates metadata)
            self.sync_service.sync_todo(todo.id)

            # Log event
            self.event_repo.log_event(
                event_type="todo_completed",
                entity_type="todo",
                entity_id=todo.id,
            )

        return todo

    def uncomplete_todo(self, todo_id: int) -> Optional[Todo]:
        """Mark a todo as not completed and sync."""
        todo = self.todo_repo.uncomplete(todo_id)

        if todo:
            # Sync to vector store
            self.sync_service.sync_todo(todo.id)

            # Log event
            self.event_repo.log_event(
                event_type="todo_uncompleted",
                entity_type="todo",
                entity_id=todo.id,
            )

        return todo

    def delete_todo(self, todo_id: int) -> bool:
        """Delete a todo and remove from vector store."""
        # Log before deleting
        todo = self.todo_repo.get(todo_id)
        if not todo:
            return False

        content = todo.content

        # Delete from database
        deleted = self.todo_repo.delete(todo_id)

        if deleted:
            # Remove from vector store
            self.sync_service.remove_todo(todo_id)

            # Log event
            self.event_repo.log_event(
                event_type="todo_deleted",
                entity_type="todo",
                entity_id=todo_id,
                details={"content": content},
            )

        return deleted

    def search_todos(
        self,
        query: str,
        k: int = 10,
        completed: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search todos semantically.

        Args:
            query: Search query
            k: Number of results
            completed: Filter by completion status

        Returns:
            List of search results with relevance scores
        """
        return self.search.search_todos(query, k=k, completed=completed)

    def find_todo_by_content(self, content: str) -> Optional[Todo]:
        """Find a todo by exact content match."""
        return self.todo_repo.get_by_content(content)

    def find_todos_by_partial_content(self, query: str, limit: int = 10) -> List[Todo]:
        """Find todos by partial content match (simple LIKE query)."""
        return self.todo_repo.search_by_content(query, limit=limit)

    def get_todo_count(self) -> Dict[str, int]:
        """Get count of todos by status."""
        active = len(self.list_active(limit=10000))
        completed = len(self.list_completed(limit=10000))
        return {
            "active": active,
            "completed": completed,
            "total": active + completed,
        }

    def list_due_today(self) -> List[Todo]:
        """List todos due today."""
        return self.todo_repo.list_due_today()

    def list_due_this_week(self) -> List[Todo]:
        """List todos due this week."""
        return self.todo_repo.list_due_this_week()

    def list_overdue(self) -> List[Todo]:
        """List overdue todos."""
        return self.todo_repo.list_overdue()

    def list_no_due_date(self) -> List[Todo]:
        """List todos with no due date."""
        return self.todo_repo.list_no_due_date()

    def update_due_date(self, todo_id: int, due_date: Optional[Any]) -> Optional[Todo]:
        """Update the due date of a todo."""
        from datetime import datetime

        # Convert due_date if it's a string
        if isinstance(due_date, str):
            try:
                due_date = datetime.fromisoformat(due_date)
            except:
                due_date = None

        todo = self.todo_repo.update_due_date(todo_id, due_date)

        if todo:
            # Sync to vector store
            self.sync_service.sync_todo(todo.id)

            # Log event
            self.event_repo.log_event(
                event_type="todo_due_date_updated",
                entity_type="todo",
                entity_id=todo.id,
                details={"due_date": due_date.isoformat() if due_date else None},
            )

        return todo

    def list_by_date_range(self, start_date: Any, end_date: Any, include_completed: bool = False) -> List[Todo]:
        """List todos within a date range."""
        from datetime import datetime

        # Convert dates if they're strings
        if isinstance(start_date, str):
            try:
                start_date = datetime.fromisoformat(start_date)
            except:
                return []

        if isinstance(end_date, str):
            try:
                end_date = datetime.fromisoformat(end_date)
            except:
                return []

        return self.todo_repo.list_by_date_range(start_date, end_date, include_completed)

    def list_focused(self) -> List[Todo]:
        """List todos in the focus list."""
        return self.todo_repo.list_focused()

    def add_to_focus(self, todo_id: int) -> Optional[Todo]:
        """Add a todo to the focus list."""
        todo = self.todo_repo.add_to_focus(todo_id)

        if todo:
            # Sync to vector store (metadata updated)
            self.sync_service.sync_todo(todo.id)

            # Log event
            self.event_repo.log_event(
                event_type="todo_focused",
                entity_type="todo",
                entity_id=todo.id,
            )

        return todo

    def remove_from_focus(self, todo_id: int) -> Optional[Todo]:
        """Remove a todo from the focus list."""
        todo = self.todo_repo.remove_from_focus(todo_id)

        if todo:
            # Sync to vector store
            self.sync_service.sync_todo(todo.id)

            # Log event
            self.event_repo.log_event(
                event_type="todo_unfocused",
                entity_type="todo",
                entity_id=todo.id,
            )

        return todo

    def get_focus_count(self) -> int:
        """Get count of focused todos."""
        return self.todo_repo.get_focus_count()

    def clear_focus(self) -> int:
        """Clear all focused todos."""
        count = self.todo_repo.clear_focus()

        # Log event
        self.event_repo.log_event(
            event_type="focus_cleared",
            entity_type="todo",
            entity_id=0,
            details={"count": count},
        )

        return count

    def get_completion_stats(self, days: int = 5) -> Dict[str, Any]:
        """
        Get completion statistics for the past X days.

        Args:
            days: Number of days to look back (default 5)

        Returns:
            Dictionary with daily stats, totals, and trends
        """
        from datetime import datetime, timedelta, date
        from collections import defaultdict

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)  # -1 to include today
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Query all todos completed in this range
        completed_todos = (
            self.session.query(Todo)
            .filter(
                Todo.completed == True,
                Todo.completed_at >= start_date,
                Todo.completed_at <= end_date
            )
            .all()
        )

        # Query todos created in this range (for completion rate)
        created_todos = (
            self.session.query(Todo)
            .filter(
                Todo.created_at >= start_date,
                Todo.created_at <= end_date
            )
            .all()
        )

        # Group by day
        daily_stats = defaultdict(lambda: {
            'date': None,
            'completed': 0,
            'created': 0,
            'by_priority': {0: 0, 1: 0, 2: 0}
        })

        # Process completed todos
        for todo in completed_todos:
            day = todo.completed_at.date()
            daily_stats[day]['date'] = day
            daily_stats[day]['completed'] += 1
            daily_stats[day]['by_priority'][todo.priority] += 1

        # Process created todos
        for todo in created_todos:
            day = todo.created_at.date()
            if day not in daily_stats:
                daily_stats[day]['date'] = day
            daily_stats[day]['created'] += 1

        # Fill in missing days with zeros
        current_date = start_date.date()
        for i in range(days):
            day = current_date + timedelta(days=i)
            if day not in daily_stats:
                daily_stats[day] = {
                    'date': day,
                    'completed': 0,
                    'created': 0,
                    'by_priority': {0: 0, 1: 0, 2: 0}
                }

        # Sort by date
        sorted_days = sorted(daily_stats.items())
        daily_list = [stats for _, stats in sorted_days]

        # Calculate totals
        total_completed = sum(day['completed'] for day in daily_list)
        total_created = sum(day['created'] for day in daily_list)
        total_by_priority = {
            0: sum(day['by_priority'][0] for day in daily_list),
            1: sum(day['by_priority'][1] for day in daily_list),
            2: sum(day['by_priority'][2] for day in daily_list)
        }

        # Calculate completion rate
        completion_rate = (total_completed / total_created * 100) if total_created > 0 else 0

        # Calculate average per day
        avg_per_day = total_completed / days if days > 0 else 0

        # Get current active and overdue counts for context
        active_count = len(self.list_active(limit=10000))
        overdue_count = len(self.list_overdue())

        return {
            'days': days,
            'start_date': start_date.date(),
            'end_date': end_date.date(),
            'daily_stats': daily_list,
            'totals': {
                'completed': total_completed,
                'created': total_created,
                'by_priority': total_by_priority
            },
            'completion_rate': completion_rate,
            'avg_per_day': avg_per_day,
            'current_active': active_count,
            'current_overdue': overdue_count
        }

    def close(self):
        """Close connections."""
        self.sync_service.close()
        if self.session:
            self.session.close()
