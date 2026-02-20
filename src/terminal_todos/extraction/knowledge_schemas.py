"""Pydantic schemas for knowledge extraction."""

from typing import List
from pydantic import BaseModel, Field


class ExtractedNote(BaseModel):
    """A single extracted note with metadata."""

    title: str = Field(
        description="Concise, descriptive title for the note (max 100 chars)"
    )
    summary: str = Field(
        description="2-3 sentence summary of the key points"
    )
    content: str = Field(
        description="Full note content (cleaned of delimiters)"
    )
    category: str = Field(
        description=(
            "Primary category: technical, meeting, documentation, "
            "project, brainstorm, reference, decision, action-items"
        )
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="3-7 important keywords/tags for search (lowercase, no duplicates)",
        max_length=10
    )
    topics: List[str] = Field(
        default_factory=list,
        description="2-5 high-level topics/themes (e.g., 'authentication', 'API design')",
        max_length=7
    )


class BulkNoteExtraction(BaseModel):
    """Result of extracting multiple notes from bulk input."""

    notes: List[ExtractedNote] = Field(
        default_factory=list,
        description="List of extracted notes with metadata"
    )

    def has_notes(self) -> bool:
        """Check if any notes were extracted."""
        return len(self.notes) > 0

    def get_note_count(self) -> int:
        """Get the number of extracted notes."""
        return len(self.notes)

    def get_by_category(self, category: str) -> List[ExtractedNote]:
        """Get notes filtered by category."""
        return [note for note in self.notes if note.category == category]
