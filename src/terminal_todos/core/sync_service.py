"""Synchronization service between database and vector store."""

from typing import List

from terminal_todos.db.connection import get_session
from terminal_todos.db.models import Note, Todo
from terminal_todos.db.repositories import EventRepository, NoteRepository, TodoRepository
from terminal_todos.vector.store import VectorStore


class SyncService:
    """Service for synchronizing database and vector store."""

    def __init__(self, vector_store: VectorStore = None):
        self.vector_store = vector_store or VectorStore()
        self.session = get_session()
        self.todo_repo = TodoRepository(self.session)
        self.note_repo = NoteRepository(self.session)
        self.event_repo = EventRepository(self.session)

    def sync_todo(self, todo_id: int) -> bool:
        """Sync a single todo to the vector store."""
        try:
            todo = self.todo_repo.get(todo_id)
            if todo:
                self.vector_store.upsert_todo(
                    todo_id=todo.id,
                    content=todo.content,
                    completed=todo.completed,
                    created_at=todo.created_at.isoformat(),
                )
                return True
            return False
        except Exception as e:
            print(f"Error syncing todo {todo_id}: {e}")
            return False

    def remove_todo(self, todo_id: int) -> bool:
        """Remove a todo from the vector store."""
        try:
            self.vector_store.delete_todo(todo_id)
            return True
        except Exception as e:
            print(f"Error removing todo {todo_id} from vector store: {e}")
            return False

    def sync_note(self, note_id: int) -> bool:
        """Sync a single note to the vector store with full metadata."""
        try:
            note = self.note_repo.get(note_id)
            if note:
                # Sync with all available metadata
                self.vector_store.upsert_note(
                    note_id=note.id,
                    content=note.content,
                    title=note.title,
                    created_at=note.created_at.isoformat(),
                    note_type=note.note_type,
                    category=note.category if hasattr(note, 'category') else None,
                    keywords=note.get_keywords() if hasattr(note, 'get_keywords') else None,
                    topics=note.get_topics() if hasattr(note, 'get_topics') else None,
                    summary=note.summary if hasattr(note, 'summary') else None,
                    updated_at=note.updated_at.isoformat() if note.updated_at else None,
                    tags=note.get_tags() if hasattr(note, 'get_tags') else None,
                )
                return True
            return False
        except Exception as e:
            print(f"Error syncing note {note_id}: {e}")
            return False

    def remove_note(self, note_id: int) -> bool:
        """Remove a note from the vector store."""
        try:
            self.vector_store.delete_note(note_id)
            return True
        except Exception as e:
            print(f"Error removing note {note_id} from vector store: {e}")
            return False

    def full_sync_todos(self) -> tuple[int, int]:
        """
        Sync all todos from database to vector store.

        Returns:
            Tuple of (success_count, error_count)
        """
        todos = self.todo_repo.list_all(limit=10000)
        success_count = 0
        error_count = 0

        for todo in todos:
            if self.sync_todo(todo.id):
                success_count += 1
            else:
                error_count += 1

        return success_count, error_count

    def full_sync_notes(self) -> tuple[int, int]:
        """
        Sync all notes from database to vector store.

        Returns:
            Tuple of (success_count, error_count)
        """
        notes = self.note_repo.list_all(limit=10000)
        success_count = 0
        error_count = 0

        for note in notes:
            if self.sync_note(note.id):
                success_count += 1
            else:
                error_count += 1

        return success_count, error_count

    def full_sync(self) -> dict:
        """
        Full synchronization of all data.

        Returns:
            Dictionary with sync statistics
        """
        print("Starting full synchronization...")

        todo_success, todo_errors = self.full_sync_todos()
        note_success, note_errors = self.full_sync_notes()

        stats = {
            "todos": {"success": todo_success, "errors": todo_errors},
            "notes": {"success": note_success, "errors": note_errors},
            "total_success": todo_success + note_success,
            "total_errors": todo_errors + note_errors,
        }

        print(f"Sync complete: {stats['total_success']} items synced, {stats['total_errors']} errors")

        # Log the sync event
        self.event_repo.log_event(
            event_type="full_sync",
            entity_type="system",
            entity_id=0,
            details=stats,
        )

        return stats

    def verify_consistency(self) -> dict:
        """
        Verify consistency between database and vector store.

        Returns:
            Dictionary with consistency check results
        """
        # Get all todos from DB
        todos = self.todo_repo.list_all(limit=10000)
        notes = self.note_repo.list_all(limit=10000)

        # Check if they exist in vector store
        missing_todos = []
        missing_notes = []

        for todo in todos:
            # Simple check: search for exact content
            results = self.vector_store.search_todos(todo.content, k=1)
            if not results or results[0]["todo_id"] != todo.id:
                missing_todos.append(todo.id)

        for note in notes:
            results = self.vector_store.search_notes(note.content[:100], k=1)
            if not results or results[0]["note_id"] != note.id:
                missing_notes.append(note.id)

        return {
            "total_todos": len(todos),
            "total_notes": len(notes),
            "missing_todos": missing_todos,
            "missing_notes": missing_notes,
            "consistent": len(missing_todos) == 0 and len(missing_notes) == 0,
        }

    def close(self):
        """Close the database session."""
        if self.session:
            self.session.close()
