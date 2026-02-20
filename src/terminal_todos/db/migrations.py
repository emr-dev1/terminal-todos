"""Simple database migration system."""

from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from terminal_todos.db.connection import get_engine, get_session, init_db
from terminal_todos.db.models import Base, Metadata

CURRENT_SCHEMA_VERSION = 6


class Migration:
    """Represents a single database migration."""

    def __init__(
        self,
        version: int,
        description: str,
        up: Callable[[Session], None],
        down: Optional[Callable[[Session], None]] = None,
    ):
        self.version = version
        self.description = description
        self.up = up
        self.down = down

    def __repr__(self) -> str:
        return f"<Migration v{self.version}: {self.description}>"


def migration_v1_initial(session: Session) -> None:
    """Initial schema creation."""
    # Schema is created by init_db()
    pass


def migration_v2_add_due_date(session: Session) -> None:
    """Add due_date column to todos table."""
    from sqlalchemy import text

    try:
        # Check if column exists
        result = session.execute(text("PRAGMA table_info(todos)"))
        columns = [row[1] for row in result]

        if "due_date" not in columns:
            # Add the column
            session.execute(text("ALTER TABLE todos ADD COLUMN due_date DATETIME"))
            session.commit()
            print("  Added due_date column to todos table")
        else:
            print("  due_date column already exists, skipping")
    except Exception as e:
        print(f"  Warning: Could not add due_date column: {e}")
        session.rollback()


def migration_v3_add_note_metadata(session: Session) -> None:
    """Add metadata fields to notes table for knowledge management."""
    from sqlalchemy import text

    try:
        # Check existing columns
        result = session.execute(text("PRAGMA table_info(notes)"))
        columns = [row[1] for row in result]

        # Add keywords column
        if "keywords" not in columns:
            session.execute(text("ALTER TABLE notes ADD COLUMN keywords TEXT"))
            print("  Added keywords column to notes table")

        # Add topics column
        if "topics" not in columns:
            session.execute(text("ALTER TABLE notes ADD COLUMN topics TEXT"))
            print("  Added topics column to notes table")

        # Add summary column
        if "summary" not in columns:
            session.execute(text("ALTER TABLE notes ADD COLUMN summary TEXT"))
            print("  Added summary column to notes table")

        # Add category column
        if "category" not in columns:
            session.execute(text("ALTER TABLE notes ADD COLUMN category TEXT"))
            print("  Added category column to notes table")

        session.commit()

    except Exception as e:
        print(f"  Warning: Could not add metadata columns: {e}")
        session.rollback()


def migration_v4_add_note_tags(session: Session) -> None:
    """Add tags field to notes table for account/client organization."""
    from sqlalchemy import text

    try:
        # Check existing columns
        result = session.execute(text("PRAGMA table_info(notes)"))
        columns = [row[1] for row in result]

        # Add tags column
        if "tags" not in columns:
            session.execute(text("ALTER TABLE notes ADD COLUMN tags TEXT"))
            print("  Added tags column to notes table")

        session.commit()

    except Exception as e:
        print(f"  Warning: Could not add tags column: {e}")
        session.rollback()


def migration_v5_add_focus_order(session: Session) -> None:
    """Add focus_order column to todos table for focus list feature."""
    from sqlalchemy import text

    try:
        # Check if column exists
        result = session.execute(text("PRAGMA table_info(todos)"))
        columns = [row[1] for row in result]

        if "focus_order" not in columns:
            session.execute(text("ALTER TABLE todos ADD COLUMN focus_order INTEGER"))
            print("  Added focus_order column to todos table")
        else:
            print("  focus_order column already exists, skipping")

        session.commit()

    except Exception as e:
        print(f"  Warning: Could not add focus_order column: {e}")
        session.rollback()


def migration_v6_add_emails_table(session: Session) -> None:
    """Add emails table for email generation feature."""
    from sqlalchemy import text

    try:
        # Check if emails table exists
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
        )
        if result.fetchone():
            print("  emails table already exists, skipping")
            return

        # Create emails table
        session.execute(
            text("""
            CREATE TABLE emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                recipient TEXT,
                context_note_ids TEXT,
                template_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        )
        session.commit()
        print("  Created emails table")

    except Exception as e:
        print(f"  Warning: Could not create emails table: {e}")
        session.rollback()


# List of all migrations in order
MIGRATIONS: List[Migration] = [
    Migration(
        version=1,
        description="Initial schema",
        up=migration_v1_initial,
    ),
    Migration(
        version=2,
        description="Add due_date to todos",
        up=migration_v2_add_due_date,
    ),
    Migration(
        version=3,
        description="Add metadata fields to notes",
        up=migration_v3_add_note_metadata,
    ),
    Migration(
        version=4,
        description="Add tags to notes",
        up=migration_v4_add_note_tags,
    ),
    Migration(
        version=5,
        description="Add focus_order to todos",
        up=migration_v5_add_focus_order,
    ),
    Migration(
        version=6,
        description="Add emails table",
        up=migration_v6_add_emails_table,
    ),
]


def get_current_version(session: Session) -> int:
    """Get the current schema version from the database."""
    try:
        metadata = (
            session.query(Metadata).filter(Metadata.key == "schema_version").first()
        )
        if metadata:
            return int(metadata.value)
        return 0
    except Exception:
        # Database might not exist yet
        return 0


def set_schema_version(session: Session, version: int) -> None:
    """Set the schema version in the database."""
    metadata = (
        session.query(Metadata).filter(Metadata.key == "schema_version").first()
    )
    if metadata:
        metadata.value = str(version)
    else:
        metadata = Metadata(key="schema_version", value=str(version))
        session.add(metadata)
    session.commit()


def run_migrations() -> None:
    """Run all pending migrations."""
    # First, ensure the database and tables exist
    init_db()

    session = get_session()
    try:
        current_version = get_current_version(session)
        target_version = CURRENT_SCHEMA_VERSION

        if current_version == target_version:
            print(f"✓ Database is up to date (version {current_version})")
            return

        if current_version > target_version:
            print(
                f"⚠️  Warning: Database version ({current_version}) is newer than app version ({target_version})"
            )
            return

        # Run migrations
        for migration in MIGRATIONS:
            if migration.version > current_version:
                print(f"  Running migration v{migration.version}: {migration.description}")
                migration.up(session)
                set_schema_version(session, migration.version)

        print(f"✓ Migrations complete. Database is now at version {target_version}")

    except Exception as e:
        session.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        session.close()


def reset_database() -> None:
    """Reset the database (drop all tables and recreate)."""
    from terminal_todos.db.connection import reset_db

    print("⚠️  Resetting database (dropping all tables)...")
    reset_db()

    # Set initial version
    session = get_session()
    try:
        set_schema_version(session, CURRENT_SCHEMA_VERSION)
        print(f"✓ Database reset complete. Version {CURRENT_SCHEMA_VERSION}")
    finally:
        session.close()
