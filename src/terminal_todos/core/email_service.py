"""Email service for managing email drafts."""

from typing import List, Optional

from terminal_todos.db.connection import get_session
from terminal_todos.db.models import Email
from terminal_todos.db.repositories import EmailRepository


class EmailService:
    """High-level service for email operations."""

    def __init__(self, session=None):
        self.session = session or get_session()
        self.email_repo = EmailRepository(self.session)

    def create_email(
        self,
        subject: str,
        body: str,
        recipient: Optional[str] = None,
        context_note_ids: Optional[List[int]] = None,
        template_type: Optional[str] = None,
    ) -> Email:
        """Create a new email draft."""
        return self.email_repo.create(
            subject=subject,
            body=body,
            recipient=recipient,
            context_note_ids=context_note_ids,
            template_type=template_type,
        )

    def get_email(self, email_id: int) -> Optional[Email]:
        """Get email by ID."""
        return self.email_repo.get(email_id)

    def list_recent_emails(self, limit: int = 10) -> List[Email]:
        """List recent emails."""
        return self.email_repo.list_recent(limit)

    def delete_email(self, email_id: int) -> bool:
        """Delete an email."""
        return self.email_repo.delete(email_id)

    def close(self):
        """Close the database session."""
        if self.session:
            self.session.close()


def get_email_service() -> EmailService:
    """Factory function for EmailService."""
    return EmailService()
