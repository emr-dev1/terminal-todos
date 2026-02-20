"""Import service for restoring data from export archives."""

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from terminal_todos.config import get_settings
from terminal_todos.core.sync_service import SyncService
from terminal_todos.db.connection import get_session
from terminal_todos.db.models import Email, Event, Note, Todo
from terminal_todos.db.repositories import (
    EmailRepository,
    EventRepository,
    NoteRepository,
    TodoRepository,
)

# Current schema version (should match migrations.py)
CURRENT_SCHEMA_VERSION = 6


class ImportService:
    """Service for importing data from export ZIP files."""

    def __init__(self):
        """Initialize import service with database session and repositories."""
        self.session = get_session()
        self.todo_repo = TodoRepository(self.session)
        self.note_repo = NoteRepository(self.session)
        self.email_repo = EmailRepository(self.session)
        self.event_repo = EventRepository(self.session)
        self.sync_service = SyncService()
        self.settings = get_settings()

    def import_from_zip(
        self,
        zip_path: str,
        confirm_overwrite: bool = False,
        method: str = "json",
    ) -> Dict:
        """
        Import data from export ZIP file with validation.

        Args:
            zip_path: Path to export ZIP file
            confirm_overwrite: If True, allows overwriting existing data
            method: Import method - "json" (default) or "sqlite"

        Returns:
            Dictionary with import statistics

        Raises:
            ValueError: If validation fails or overwrite not confirmed
            zipfile.BadZipFile: If ZIP file is invalid
        """
        # Validate ZIP file
        issues = self._validate_export_file(zip_path)
        if issues:
            raise ValueError(f"Invalid export file: {'; '.join(issues)}")

        # Extract and validate export data
        with zipfile.ZipFile(zip_path, "r") as zf:
            json_data = json.loads(zf.read("data_export.json"))

        # Validate export metadata and schema compatibility
        issues = self._validate_export_metadata(json_data["export_metadata"])
        if issues:
            raise ValueError(f"Export validation failed: {'; '.join(issues)}")

        # Validate relationships
        issues = self._validate_relationships(json_data)
        if issues:
            raise ValueError(f"Data relationship errors: {'; '.join(issues)}")

        # Check for existing data
        existing = self._check_existing_data()
        if existing["has_data"] and not confirm_overwrite:
            raise ValueError(
                f"Database contains existing data (todos: {existing['todos']}, "
                f"notes: {existing['notes']}). Use --confirm-overwrite to proceed."
            )

        # Create backup before overwrite
        if existing["has_data"]:
            self._create_backup()

        # Import based on method
        if method == "sqlite":
            result = self._import_from_sqlite(zip_path)
        else:
            result = self._import_from_json(json_data)

        # Rebuild vector store embeddings
        print("Rebuilding vector store embeddings...")
        sync_stats = self.sync_service.full_sync()
        result["embeddings"] = (
            sync_stats["total_success"] if sync_stats else 0
        )

        return result

    def _validate_export_file(self, zip_path: str) -> List[str]:
        """Validate ZIP file structure."""
        issues = []

        if not os.path.exists(zip_path):
            issues.append(f"File not found: {zip_path}")
            return issues

        if not zipfile.is_zipfile(zip_path):
            issues.append("Not a valid ZIP file")
            return issues

        # Check for required files
        with zipfile.ZipFile(zip_path, "r") as zf:
            filenames = zf.namelist()
            if "data_export.json" not in filenames:
                issues.append("Missing data_export.json")
            if "todos.db" not in filenames:
                issues.append("Missing todos.db backup")

        return issues

    def _validate_export_metadata(self, metadata: Dict) -> List[str]:
        """Validate export metadata and schema compatibility."""
        issues = []

        export_version = metadata.get("schema_version")
        if export_version is None:
            issues.append("Missing schema_version in export metadata")
        elif export_version > CURRENT_SCHEMA_VERSION:
            issues.append(
                f"Export schema v{export_version} is newer than app v{CURRENT_SCHEMA_VERSION}. "
                "Update terminal-todos before importing."
            )

        if not metadata.get("export_timestamp"):
            issues.append("Missing export_timestamp")

        if not metadata.get("counts"):
            issues.append("Missing data counts")

        return issues

    def _validate_relationships(self, export_data: Dict) -> List[str]:
        """Validate foreign key relationships in export data."""
        issues = []

        # Build index of all note IDs
        note_ids = {note["id"] for note in export_data.get("notes", [])}

        # Validate Todo.note_id → Notes.id
        for todo in export_data.get("todos", []):
            if todo.get("note_id") is not None and todo["note_id"] not in note_ids:
                issues.append(
                    f"Todo #{todo['id']} references non-existent note #{todo['note_id']}"
                )

        # Validate Email.context_note_ids → Notes.id
        for email in export_data.get("emails", []):
            context_ids = email.get("context_note_ids", [])
            if context_ids:
                for note_id in context_ids:
                    if note_id not in note_ids:
                        issues.append(
                            f"Email #{email['id']} references non-existent note #{note_id}"
                        )

        return issues

    def _check_existing_data(self) -> Dict:
        """Check if database has existing data."""
        todo_count = self.session.query(Todo).count()
        note_count = self.session.query(Note).count()

        return {
            "has_data": todo_count > 0 or note_count > 0,
            "todos": todo_count,
            "notes": note_count,
        }

    def _create_backup(self) -> str:
        """Create automatic backup before import."""
        db_path = Path(self.settings.db_path)
        if not db_path.exists():
            return ""

        # Create backup directory
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"pre-import-{timestamp}.db"
        shutil.copy(db_path, backup_path)

        print(f"Backup created: {backup_path}")
        return str(backup_path)

    def _import_from_json(self, json_data: Dict) -> Dict:
        """Import data from JSON export."""
        try:
            # Begin transaction
            self.session.begin_nested()

            # Clear existing data
            self._clear_database()

            # Import in order: notes → todos → emails → events
            notes_count = self._import_notes(json_data.get("notes", []))
            todos_count = self._import_todos(json_data.get("todos", []))
            emails_count = self._import_emails(json_data.get("emails", []))
            events_count = self._import_events(json_data.get("events", []))

            # Commit transaction
            self.session.commit()

            return {
                "todos": todos_count,
                "notes": notes_count,
                "emails": emails_count,
                "events": events_count,
            }

        except Exception as e:
            # Rollback on any error
            self.session.rollback()
            raise ImportError(f"Import failed, rolled back: {e}")

    def _import_from_sqlite(self, zip_path: str) -> Dict:
        """Import by replacing SQLite database file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract SQLite backup
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extract("todos.db", temp_dir)

            # Close current session
            self.session.close()

            # Replace database file
            db_path = Path(self.settings.db_path)
            shutil.copy(Path(temp_dir) / "todos.db", db_path)

            # Reconnect to new database
            self.session = get_session()
            self.todo_repo = TodoRepository(self.session)
            self.note_repo = NoteRepository(self.session)

            # Count imported data
            todos_count = self.session.query(Todo).count()
            notes_count = self.session.query(Note).count()
            emails_count = self.session.query(Email).count()
            events_count = self.session.query(Event).count()

            return {
                "todos": todos_count,
                "notes": notes_count,
                "emails": emails_count,
                "events": events_count,
            }

    def _clear_database(self) -> None:
        """Clear all data from database tables."""
        # Delete in reverse order of dependencies
        self.session.query(Event).delete()
        self.session.query(Email).delete()
        self.session.query(Todo).delete()
        self.session.query(Note).delete()
        self.session.flush()

    def _import_notes(self, notes_data: List[Dict]) -> int:
        """Import notes from JSON data."""
        for note_data in notes_data:
            note = Note(
                id=note_data["id"],
                content=note_data["content"],
                title=note_data.get("title"),
                created_at=datetime.fromisoformat(note_data["created_at"])
                if note_data.get("created_at")
                else datetime.utcnow(),
                updated_at=datetime.fromisoformat(note_data["updated_at"])
                if note_data.get("updated_at")
                else datetime.utcnow(),
                note_type=note_data.get("note_type", "general"),
                summary=note_data.get("summary"),
                category=note_data.get("category"),
            )

            # Serialize JSON fields
            if note_data.get("keywords"):
                note.set_keywords(note_data["keywords"])
            if note_data.get("topics"):
                note.set_topics(note_data["topics"])
            if note_data.get("tags"):
                note.set_tags(note_data["tags"])

            self.session.add(note)

        self.session.flush()
        return len(notes_data)

    def _import_todos(self, todos_data: List[Dict]) -> int:
        """Import todos from JSON data."""
        for todo_data in todos_data:
            todo = Todo(
                id=todo_data["id"],
                content=todo_data["content"],
                completed=todo_data.get("completed", False),
                created_at=datetime.fromisoformat(todo_data["created_at"])
                if todo_data.get("created_at")
                else datetime.utcnow(),
                completed_at=datetime.fromisoformat(todo_data["completed_at"])
                if todo_data.get("completed_at")
                else None,
                due_date=datetime.fromisoformat(todo_data["due_date"])
                if todo_data.get("due_date")
                else None,
                note_id=todo_data.get("note_id"),
                priority=todo_data.get("priority", 0),
                focus_order=todo_data.get("focus_order"),
            )
            self.session.add(todo)

        self.session.flush()
        return len(todos_data)

    def _import_emails(self, emails_data: List[Dict]) -> int:
        """Import emails from JSON data."""
        for email_data in emails_data:
            email = Email(
                id=email_data["id"],
                subject=email_data["subject"],
                body=email_data["body"],
                recipient=email_data.get("recipient"),
                context_note_ids=json.dumps(email_data.get("context_note_ids", []))
                if email_data.get("context_note_ids")
                else None,
                template_type=email_data.get("template_type"),
                created_at=datetime.fromisoformat(email_data["created_at"])
                if email_data.get("created_at")
                else datetime.utcnow(),
            )
            self.session.add(email)

        self.session.flush()
        return len(emails_data)

    def _import_events(self, events_data: List[Dict]) -> int:
        """Import events from JSON data."""
        for event_data in events_data:
            event = Event(
                id=event_data["id"],
                event_type=event_data["event_type"],
                entity_type=event_data["entity_type"],
                entity_id=event_data["entity_id"],
                details=event_data.get("details"),
                created_at=datetime.fromisoformat(event_data["created_at"])
                if event_data.get("created_at")
                else datetime.utcnow(),
            )
            self.session.add(event)

        self.session.flush()
        return len(events_data)

    def close(self):
        """Close database session."""
        if self.session:
            self.session.close()
        if self.sync_service:
            self.sync_service.close()
