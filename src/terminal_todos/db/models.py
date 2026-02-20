"""SQLAlchemy ORM models for Terminal Todos."""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Todo(Base):
    """Todo item model."""

    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=True)
    priority = Column(Integer, default=0)
    focus_order = Column(Integer, nullable=True, default=None)

    # Relationships
    note = relationship("Note", back_populates="todos")

    def __repr__(self) -> str:
        status = "✓" if self.completed else "○"
        return f"<Todo {self.id}: {status} {self.content[:50]}>"


class Note(Base):
    """Note model for storing meeting notes and general notes."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    note_type = Column(String, default="general")

    # Metadata fields for knowledge management
    keywords = Column(Text, nullable=True)  # JSON array of strings
    topics = Column(Text, nullable=True)    # JSON array of strings
    summary = Column(Text, nullable=True)   # AI-generated summary
    category = Column(String, nullable=True)  # Primary category
    tags = Column(Text, nullable=True)  # JSON array of strings (accounts, clients, projects)

    # Relationships
    todos = relationship("Todo", back_populates="note")

    def __repr__(self) -> str:
        return f"<Note {self.id}: {self.title or 'Untitled'}>"

    def get_keywords(self) -> List[str]:
        """Parse keywords from JSON string."""
        if self.keywords:
            try:
                return json.loads(self.keywords)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def set_keywords(self, keywords: List[str]) -> None:
        """Store keywords as JSON string."""
        if keywords:
            self.keywords = json.dumps(keywords)
        else:
            self.keywords = None

    def get_topics(self) -> List[str]:
        """Parse topics from JSON string."""
        if self.topics:
            try:
                return json.loads(self.topics)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def set_topics(self, topics: List[str]) -> None:
        """Store topics as JSON string."""
        if topics:
            self.topics = json.dumps(topics)
        else:
            self.topics = None

    def get_tags(self) -> List[str]:
        """Parse tags from JSON string."""
        if self.tags:
            try:
                return json.loads(self.tags)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def set_tags(self, tags: List[str]) -> None:
        """Store tags as JSON string."""
        if tags:
            self.tags = json.dumps(tags)
        else:
            self.tags = None


class Email(Base):
    """Email draft model."""

    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    recipient = Column(String, nullable=True)
    context_note_ids = Column(String, nullable=True)  # JSON array of note IDs
    template_type = Column(String, nullable=True)  # "follow_up", "enablement", "custom"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Email {self.id}: {self.subject[:50]}>"

    def get_context_note_ids(self) -> List[int]:
        """Parse context_note_ids JSON string."""
        if not self.context_note_ids:
            return []
        try:
            return json.loads(self.context_note_ids)
        except json.JSONDecodeError:
            return []


class Event(Base):
    """Event log for auditing actions."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    details = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Event {self.id}: {self.event_type} on {self.entity_type} {self.entity_id}>"


class Metadata(Base):
    """Metadata for schema versioning and app state."""

    __tablename__ = "metadata"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<Metadata {self.key}: {self.value}>"
