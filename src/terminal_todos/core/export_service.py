"""Export service for creating portable backups of all application data."""

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from terminal_todos.config import get_settings
from terminal_todos.db.connection import get_session
from terminal_todos.db.models import Email, Event, Metadata, Note, Todo
from terminal_todos.db.repositories import (
    EmailRepository,
    EventRepository,
    NoteRepository,
    TodoRepository,
)


class ExportService:
    """Service for exporting all application data to portable format."""

    def __init__(self):
        """Initialize export service with database session and repositories."""
        self.session = get_session()
        self.todo_repo = TodoRepository(self.session)
        self.note_repo = NoteRepository(self.session)
        self.email_repo = EmailRepository(self.session)
        self.event_repo = EventRepository(self.session)
        self.settings = get_settings()

    def export_to_zip(self, output_path: Optional[str] = None) -> Dict:
        """
        Export all data to ZIP file containing JSON + SQLite backup.

        Args:
            output_path: Path to output ZIP file. If None, generates default name.

        Returns:
            Dictionary with export statistics and output path.
        """
        # Generate default filename if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"terminal-todos-export-{timestamp}.zip"

        # Create temporary directory for staging
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Export JSON data
            json_data = self._export_data_to_json()
            json_path = temp_path / "data_export.json"
            with open(json_path, "w") as f:
                json.dump(json_data, f, indent=2)

            # Copy SQLite database
            db_path = Path(self.settings.db_path)
            if db_path.exists():
                shutil.copy(db_path, temp_path / "todos.db")

            # Create human-readable manifest
            manifest_path = temp_path / "export_manifest.txt"
            self._create_manifest(manifest_path, json_data["export_metadata"])

            # Create ZIP file
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(json_path, "data_export.json")
                if (temp_path / "todos.db").exists():
                    zipf.write(temp_path / "todos.db", "todos.db")
                zipf.write(manifest_path, "export_manifest.txt")

        return {
            "output_path": output_path,
            "counts": json_data["export_metadata"]["counts"],
        }

    def _export_data_to_json(self) -> Dict:
        """Export all data to JSON-serializable format."""
        # Get schema version from metadata table
        schema_version = self._get_schema_version()

        # Export all entities
        todos = self._export_todos_to_json()
        notes = self._export_notes_to_json()
        emails = self._export_emails_to_json()
        events = self._export_events_to_json()

        # Create export metadata
        export_metadata = {
            "version": "1.0",
            "schema_version": schema_version,
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "source_app": "terminal-todos",
            "counts": {
                "todos": len(todos),
                "notes": len(notes),
                "emails": len(emails),
                "events": len(events),
            },
        }

        return {
            "export_metadata": export_metadata,
            "todos": todos,
            "notes": notes,
            "emails": emails,
            "events": events,
        }

    def _export_todos_to_json(self) -> List[Dict]:
        """Export all todos to JSON format."""
        todos = self.todo_repo.list_all(limit=100000)
        return [
            {
                "id": todo.id,
                "content": todo.content,
                "completed": todo.completed,
                "created_at": todo.created_at.isoformat() if todo.created_at else None,
                "completed_at": todo.completed_at.isoformat()
                if todo.completed_at
                else None,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "note_id": todo.note_id,
                "priority": todo.priority,
                "focus_order": todo.focus_order,
            }
            for todo in todos
        ]

    def _export_notes_to_json(self) -> List[Dict]:
        """Export all notes with metadata to JSON format."""
        notes = self.note_repo.list_all(limit=100000)
        return [
            {
                "id": note.id,
                "content": note.content,
                "title": note.title,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                "note_type": note.note_type,
                "keywords": note.get_keywords(),  # Parsed from JSON string
                "topics": note.get_topics(),  # Parsed from JSON string
                "summary": note.summary,
                "category": note.category,
                "tags": note.get_tags(),  # Parsed from JSON string
            }
            for note in notes
        ]

    def _export_emails_to_json(self) -> List[Dict]:
        """Export all emails to JSON format."""
        # Get all emails (EmailRepository doesn't have list_all, so query directly)
        emails = self.session.query(Email).all()
        return [
            {
                "id": email.id,
                "subject": email.subject,
                "body": email.body,
                "recipient": email.recipient,
                "context_note_ids": email.get_context_note_ids(),  # Parsed from JSON
                "template_type": email.template_type,
                "created_at": email.created_at.isoformat()
                if email.created_at
                else None,
            }
            for email in emails
        ]

    def _export_events_to_json(self) -> List[Dict]:
        """Export complete audit log to JSON format."""
        # Get all events (query directly for complete history)
        events = self.session.query(Event).order_by(Event.created_at.asc()).all()
        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "details": event.details,  # Already a JSON string
                "created_at": event.created_at.isoformat()
                if event.created_at
                else None,
            }
            for event in events
        ]

    def _get_schema_version(self) -> int:
        """Get current schema version from metadata table."""
        try:
            metadata = (
                self.session.query(Metadata)
                .filter(Metadata.key == "schema_version")
                .first()
            )
            if metadata:
                return int(metadata.value)
            return 0
        except Exception:
            return 0

    def _create_manifest(self, manifest_path: Path, metadata: Dict) -> None:
        """Create human-readable manifest file."""
        with open(manifest_path, "w") as f:
            f.write("=" * 60 + "\n")
            f.write("TERMINAL TODOS EXPORT MANIFEST\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Export Version: {metadata['version']}\n")
            f.write(f"Schema Version: {metadata['schema_version']}\n")
            f.write(f"Export Time: {metadata['export_timestamp']}\n")
            f.write(f"Source App: {metadata['source_app']}\n\n")
            f.write("Data Counts:\n")
            f.write(f"  Todos:  {metadata['counts']['todos']}\n")
            f.write(f"  Notes:  {metadata['counts']['notes']}\n")
            f.write(f"  Emails: {metadata['counts']['emails']}\n")
            f.write(f"  Events: {metadata['counts']['events']}\n\n")
            f.write("Files Included:\n")
            f.write("  - data_export.json (JSON export with all data)\n")
            f.write("  - todos.db (SQLite database backup)\n")
            f.write("  - export_manifest.txt (this file)\n\n")
            f.write("=" * 60 + "\n")

    def close(self):
        """Close database session."""
        if self.session:
            self.session.close()
