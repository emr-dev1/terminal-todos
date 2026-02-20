"""Knowledge extraction from bulk note imports using OpenAI."""

import re
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from terminal_todos.config import get_settings
from terminal_todos.extraction.knowledge_schemas import (
    BulkNoteExtraction,
    ExtractedNote,
)


class KnowledgeExtractor:
    """Extract structured knowledge from bulk note imports."""

    # Note delimiters for splitting input
    DELIMITERS = [
        r'\n---+\n',        # Markdown horizontal rules: ---
        r'\n#{3,}\n',       # Triple hash or more: ###
        r'\n\n\n+',         # Triple or more blank lines
    ]

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.llm_model
        self.user_name = settings.user_name

        # Create LLM for single note extraction
        self.single_note_llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            temperature=0,
        ).with_structured_output(ExtractedNote)

        self._create_prompts()

    def _create_prompts(self):
        """Create prompt templates."""

        single_note_system = f"""You are an expert at analyzing notes and extracting structured metadata.

**IMPORTANT FILTERS:**
- Ignore timestamps (e.g., "10:30 AM", "2:45 PM")
- Ignore the user's name: "{self.user_name}"
- Ignore chat metadata and formatting artifacts
- Focus on actual content

**YOUR TASK:**
Extract structured metadata from a note to enable semantic search and organization.

**CATEGORIES (choose the BEST fit):**
- technical: Code, architecture, technical decisions, technical debt
- meeting: Meeting notes, discussions, syncs
- documentation: How-to guides, explanations, documentation
- project: Planning, roadmaps, milestones, project management
- brainstorm: Ideas, creative sessions, proposals
- reference: Links, resources, references, bookmarks
- decision: Decisions made, ADRs (Architecture Decision Records)
- action-items: Follow-ups, next steps (but don't extract as todos)

**KEYWORDS:**
- Extract 3-7 specific, searchable terms (lowercase)
- Focus on technical terms, project names, tools, technologies
- Remove common words (the, and, or, etc.)
- No duplicates

**TOPICS:**
- Extract 2-5 high-level themes
- Examples: "authentication", "API design", "performance", "security"
- Broader than keywords

**SUMMARY:**
- Write 2-3 sentences capturing the essence
- Focus on key decisions, outcomes, or information
- Be concise and informative

**CONSISTENCY:**
- Use lowercase for keywords
- Be consistent with similar notes
- Extract precise, searchable terms"""

        self.single_prompt = ChatPromptTemplate.from_messages([
            ("system", single_note_system),
            ("user", "Extract metadata from this note:\n\n{note_content}"),
        ])

        self.single_chain = self.single_prompt | self.single_note_llm

    def split_notes(self, bulk_content: str) -> List[str]:
        """
        Split bulk input into individual notes using delimiters.

        Args:
            bulk_content: Raw bulk input text

        Returns:
            List of individual note strings
        """
        # Try each delimiter pattern
        for delimiter_pattern in self.DELIMITERS:
            parts = re.split(delimiter_pattern, bulk_content)
            # If we got more than one part, use this delimiter
            if len(parts) > 1:
                # Filter out empty parts
                return [part.strip() for part in parts if part.strip()]

        # No delimiters found - treat as single note
        return [bulk_content.strip()] if bulk_content.strip() else []

    def extract_single(self, note_content: str) -> ExtractedNote:
        """
        Extract metadata from a single note.

        Args:
            note_content: Individual note text

        Returns:
            ExtractedNote with metadata
        """
        result = self.single_chain.invoke({"note_content": note_content})
        # Ensure content is preserved
        result.content = note_content
        return result

    def extract_bulk(self, bulk_content: str, auto_split: bool = True) -> BulkNoteExtraction:
        """
        Extract metadata from bulk note input.

        Args:
            bulk_content: Raw bulk input (may contain multiple notes)
            auto_split: Automatically split by delimiters

        Returns:
            BulkNoteExtraction with list of notes
        """
        if auto_split:
            # Split into individual notes
            note_parts = self.split_notes(bulk_content)
        else:
            # Treat as single note
            note_parts = [bulk_content]

        if not note_parts:
            return BulkNoteExtraction(notes=[])

        # Extract metadata for each note
        extracted_notes = []
        for i, note_content in enumerate(note_parts, 1):
            print(f"  Extracting note {i}/{len(note_parts)}...")
            try:
                extracted = self.extract_single(note_content)
                extracted_notes.append(extracted)
            except Exception as e:
                print(f"  Warning: Failed to extract note {i}: {e}")
                # Create minimal extraction
                extracted_notes.append(ExtractedNote(
                    title=f"Note {i}",
                    summary="Failed to extract metadata",
                    content=note_content,
                    category="reference",
                    keywords=[],
                    topics=[]
                ))

        return BulkNoteExtraction(notes=extracted_notes)

    def extract_with_retry(
        self,
        bulk_content: str,
        max_retries: int = 3,
        auto_split: bool = True
    ) -> Optional[BulkNoteExtraction]:
        """Extract with retry logic for API failures."""
        for attempt in range(max_retries):
            try:
                return self.extract_bulk(bulk_content, auto_split=auto_split)
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Extraction failed after {max_retries} attempts: {e}")
                    return None
                print(f"⚠️  Extraction attempt {attempt + 1} failed, retrying...")
        return None
