"""Pydantic schemas for AI extraction."""

from typing import List

from pydantic import BaseModel, Field


class ExtractedTodo(BaseModel):
    """A single extracted todo item."""

    content: str = Field(description="The todo item text/task description")
    priority: int = Field(
        default=0,
        description="Priority level: 0=normal, 1=high, 2=urgent",
        ge=0,
        le=2,
    )


class NoteExtraction(BaseModel):
    """Result of extracting todos from a note."""

    title: str = Field(description="Extracted title or summary of the note")
    todos: List[ExtractedTodo] = Field(
        default_factory=list,
        description="List of todo items extracted from the note",
    )
    note_type: str = Field(
        default="general",
        description="Type of note: meeting, general, brainstorm, etc.",
    )

    def has_todos(self) -> bool:
        """Check if any todos were extracted."""
        return len(self.todos) > 0

    def get_todo_count(self) -> int:
        """Get the number of extracted todos."""
        return len(self.todos)

    def get_high_priority_todos(self) -> List[ExtractedTodo]:
        """Get todos with high or urgent priority."""
        return [todo for todo in self.todos if todo.priority >= 1]
