"""Note service with database and vector store operations."""

from typing import Any, Dict, List, Optional

from terminal_todos.db.connection import get_session
from terminal_todos.db.models import Note
from terminal_todos.db.repositories import EventRepository, NoteRepository
from terminal_todos.core.sync_service import SyncService
from terminal_todos.vector.search import SemanticSearch


class NoteService:
    """High-level service for note operations."""

    def __init__(self):
        self.session = get_session()
        self.note_repo = NoteRepository(self.session)
        self.event_repo = EventRepository(self.session)
        self.sync_service = SyncService()
        self.search = SemanticSearch(self.sync_service.vector_store)

    def create_note(
        self, content: str, title: Optional[str] = None, note_type: str = "general"
    ) -> Note:
        """Create a new note and sync to vector store."""
        # Create in database
        note = self.note_repo.create(content=content, title=title, note_type=note_type)

        # Sync to vector store
        self.sync_service.sync_note(note.id)

        # Log event
        self.event_repo.log_event(
            event_type="note_created",
            entity_type="note",
            entity_id=note.id,
            details={"title": title, "note_type": note_type},
        )

        return note

    def get_note(self, note_id: int) -> Optional[Note]:
        """Get a note by ID."""
        return self.note_repo.get(note_id)

    def list_all(self, limit: int = 100) -> List[Note]:
        """List all notes."""
        return self.note_repo.list_all(limit=limit)

    def delete_note(self, note_id: int) -> bool:
        """Delete a note and remove from vector store."""
        # Log before deleting
        note = self.note_repo.get(note_id)
        if not note:
            return False

        title = note.title

        # Delete from database
        deleted = self.note_repo.delete(note_id)

        if deleted:
            # Remove from vector store
            self.sync_service.remove_note(note_id)

            # Log event
            self.event_repo.log_event(
                event_type="note_deleted",
                entity_type="note",
                entity_id=note_id,
                details={"title": title},
            )

        return deleted

    def search_notes(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Search notes semantically.

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of search results with relevance scores
        """
        return self.search.search_notes(query, k=k)

    def find_notes_by_partial_content(self, query: str, limit: int = 10) -> List[Note]:
        """Find notes by partial content match (simple LIKE query)."""
        return self.note_repo.search_by_content(query, limit=limit)

    def get_note_count(self) -> int:
        """Get total count of notes."""
        return len(self.list_all(limit=10000))

    def list_by_date_range(self, start_date, end_date, limit: int = 100):
        """List notes created within a date range."""
        return self.note_repo.list_by_date_range(start_date, end_date, limit=limit)

    def create_note_with_metadata(
        self,
        content: str,
        title: Optional[str] = None,
        note_type: str = "general",
        category: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Note:
        """Create a note with rich metadata and sync to vector store."""
        from terminal_todos.utils.logger import log_debug, log_error

        try:
            log_debug("Creating note with metadata", {
                "title": title,
                "note_type": note_type,
                "category": category,
                "has_keywords": bool(keywords),
                "has_topics": bool(topics),
                "has_tags": bool(tags)
            })

            # Create in database
            note = self.note_repo.create(content=content, title=title, note_type=note_type)
            log_debug(f"Note created in database with ID: {note.id}")

            # Set metadata fields
            if category:
                note.category = category
            if keywords:
                note.set_keywords(keywords)
            if topics:
                note.set_topics(topics)
            if summary:
                note.summary = summary
            if tags:
                note.set_tags(tags)

            log_debug("Committing metadata to database")
            self.session.commit()
            self.session.refresh(note)

            # Sync to vector store with full metadata
            log_debug(f"Syncing note {note.id} to vector store")
            self._sync_note_with_metadata(note)
            log_debug(f"Note {note.id} synced successfully")

        except Exception as e:
            log_error(e, f"Failed to create note with metadata (title: {title})", show_traceback=True)
            raise

        # Log event with metadata
        self.event_repo.log_event(
            event_type="note_created",
            entity_type="note",
            entity_id=note.id,
            details={
                "title": title,
                "note_type": note_type,
                "category": category,
                "keywords": keywords,
                "topics": topics,
                "tags": tags,
            },
        )

        return note

    def _sync_note_with_metadata(self, note: Note) -> None:
        """Sync note to vector store with full metadata."""
        from terminal_todos.utils.logger import log_debug, log_error

        try:
            log_debug(f"Syncing note {note.id} to vector store", {
                "title": note.title,
                "category": note.category,
                "keywords_count": len(note.get_keywords()),
                "topics_count": len(note.get_topics()),
                "tags_count": len(note.get_tags())
            })

            self.sync_service.vector_store.upsert_note(
                note_id=note.id,
                content=note.content,
                title=note.title,
                created_at=note.created_at.isoformat(),
                note_type=note.note_type,
                category=note.category,
                keywords=note.get_keywords(),
                topics=note.get_topics(),
                summary=note.summary,
                updated_at=note.updated_at.isoformat(),
                tags=note.get_tags(),
            )

            log_debug(f"Note {note.id} vector store sync complete")

        except Exception as e:
            log_error(e, f"Failed to sync note {note.id} to vector store", show_traceback=True)
            raise

    def create_notes_bulk(
        self,
        notes: List[Dict[str, Any]],
    ) -> List[Note]:
        """
        Create multiple notes in bulk.

        Args:
            notes: List of dicts with keys: content, title, category, keywords, topics, summary, tags

        Returns:
            List of created Note objects
        """
        from terminal_todos.utils.logger import log_debug, log_error, log_info

        log_info(f"Starting bulk note creation for {len(notes)} notes")
        created_notes = []

        for i, note_data in enumerate(notes, 1):
            try:
                log_debug(f"Creating note {i}/{len(notes)}", {
                    "title": note_data.get("title"),
                    "category": note_data.get("category")
                })

                note = self.create_note_with_metadata(
                    content=note_data["content"],
                    title=note_data.get("title"),
                    note_type="imported",  # Mark as imported
                    category=note_data.get("category"),
                    keywords=note_data.get("keywords"),
                    topics=note_data.get("topics"),
                    summary=note_data.get("summary"),
                    tags=note_data.get("tags"),
                )
                created_notes.append(note)
                log_debug(f"Note {i}/{len(notes)} created successfully (ID: {note.id})")

            except Exception as e:
                log_error(e, f"Failed to create note {i}/{len(notes)}", show_traceback=True)
                raise

        log_info(f"Bulk creation complete: {len(created_notes)} notes created")
        return created_notes

    def close(self):
        """Close connections."""
        self.sync_service.close()
        if self.session:
            self.session.close()
