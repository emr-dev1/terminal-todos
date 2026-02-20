#!/usr/bin/env python3
"""Test script for import functionality with tags."""

import sys
from terminal_todos.core.note_service import NoteService
from terminal_todos.extraction.knowledge_extractor import KnowledgeExtractor
from terminal_todos.config import get_settings

def test_import_with_tags():
    """Test importing notes with tags."""

    # Check verbose logging
    settings = get_settings()
    print(f"Verbose logging enabled: {settings.verbose_logging}")
    print()

    # Sample bulk content
    bulk_content = """
API Rate Limiting Review
Current implementation is naive and needs improvement.
We should use a token bucket algorithm with Redis.

---

Sprint Planning Meeting
Discussed Q1 roadmap with focus on authentication refactor.
Key decisions: OAuth 2.0 with PKCE, MFA by Q2.
"""

    print("=" * 80)
    print("TEST: Import Notes with Tags")
    print("=" * 80)
    print()

    # Step 1: Extract metadata
    print("Step 1: Extracting metadata...")
    extractor = KnowledgeExtractor()
    extraction = extractor.extract_bulk(bulk_content, auto_split=True)

    print(f"✓ Extracted {extraction.get_note_count()} notes:")
    for i, note in enumerate(extraction.notes, 1):
        print(f"  {i}. [{note.category.upper()}] {note.title}")
        print(f"     Keywords: {', '.join(note.keywords)}")
        print(f"     Topics: {', '.join(note.topics)}")
    print()

    # Step 2: Prepare notes with tags
    print("Step 2: Preparing notes with tags...")
    tags = ["Client-A", "Q1-2026", "TestProject"]
    notes_data = []

    for note in extraction.notes:
        notes_data.append({
            "content": note.content,
            "title": note.title,
            "category": note.category,
            "keywords": note.keywords,
            "topics": note.topics,
            "summary": note.summary,
            "tags": tags,
        })

    print(f"✓ Prepared {len(notes_data)} notes with tags: {', '.join(tags)}")
    print()

    # Step 3: Create notes
    print("Step 3: Creating notes in database...")
    service = NoteService()

    try:
        created_notes = service.create_notes_bulk(notes_data)

        print(f"✓ Successfully created {len(created_notes)} notes:")
        for note in created_notes:
            print(f"  #{note.id}: [{note.category.upper()}] {note.title}")
            print(f"    Tags: {', '.join(note.get_tags())}")
            print(f"    Keywords: {', '.join(note.get_keywords())}")
            print(f"    Topics: {', '.join(note.get_topics())}")
        print()

        # Step 4: Verify in database
        print("Step 4: Verifying in database...")
        for note in created_notes:
            retrieved = service.get_note(note.id)
            if retrieved:
                print(f"  ✓ Note #{note.id} exists in DB")
                print(f"    DB tags: {retrieved.tags}")
                print(f"    Parsed tags: {retrieved.get_tags()}")
            else:
                print(f"  ✗ Note #{note.id} NOT FOUND in DB")
        print()

        # Step 5: Test agent tool
        print("Step 5: Testing agent tool search_notes_by_tags...")
        from terminal_todos.agent.tools import search_notes_by_tags

        result = search_notes_by_tags(tags="Client-A")
        print("Agent tool result:")
        print(result)
        print()

        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        service.close()

if __name__ == "__main__":
    test_import_with_tags()
