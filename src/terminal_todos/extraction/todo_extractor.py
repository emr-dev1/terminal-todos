"""Todo extraction from notes using OpenAI."""

from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from terminal_todos.config import get_settings
from terminal_todos.extraction.schemas import NoteExtraction


class TodoExtractor:
    """Extract todos from notes using OpenAI with structured output."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.llm_model
        self.user_name = settings.user_name

        # Create LLM with structured output
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            temperature=0,  # Deterministic output
        ).with_structured_output(NoteExtraction)

        # Create prompt template with user_name filter
        system_prompt = f"""You are an expert at analyzing notes and extracting actionable todo items.

**IMPORTANT: This note may be pasted from Slack or other chat applications.**
- Ignore timestamps (e.g., "10:30 AM", "2:45 PM", "Jan 14, 2026")
- Ignore the user's name: "{self.user_name}"
- Ignore message metadata and formatting artifacts
- Focus ONLY on the actual content and action items

Your task is to:
1. Extract a clear title or summary for the note
2. Identify all actionable todo items from the note
3. Assign appropriate priority levels (0=normal, 1=high, 2=urgent)

Focus on:
- Action items explicitly mentioned (e.g., "send email", "schedule meeting")
- Tasks assigned to people
- Follow-up items and next steps
- Commitments and deadlines
- Decisions that require action

Do NOT extract:
- General observations or statements
- Questions without clear action needed
- Completed items (unless explicitly stated as pending)
- Timestamps, usernames, or chat metadata

Priority guidelines:
- 0 (normal): Regular tasks, no deadline mentioned
- 1 (high): Tasks with near-term deadlines, important tasks
- 2 (urgent): Tasks with immediate deadlines, blocking issues

Determine the note type based on content:
- "meeting": Meeting notes, discussion summaries
- "brainstorm": Ideas, planning sessions
- "general": General notes, observations
- "project": Project-specific notes"""

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("user", "{note_content}"),
            ]
        )

        # Create the chain
        self.chain = self.prompt | self.llm

    async def extract_async(self, note_content: str) -> NoteExtraction:
        """
        Extract todos from note content (async).

        Args:
            note_content: The note text to analyze

        Returns:
            NoteExtraction with title and todos
        """
        result = await self.chain.ainvoke({"note_content": note_content})
        return result

    def extract(self, note_content: str) -> NoteExtraction:
        """
        Extract todos from note content (sync).

        Args:
            note_content: The note text to analyze

        Returns:
            NoteExtraction with title and todos
        """
        result = self.chain.invoke({"note_content": note_content})
        return result

    def extract_with_retry(
        self, note_content: str, max_retries: int = 3
    ) -> Optional[NoteExtraction]:
        """
        Extract todos with retry logic for API failures.

        Args:
            note_content: The note text to analyze
            max_retries: Maximum number of retry attempts

        Returns:
            NoteExtraction or None if all retries failed
        """
        for attempt in range(max_retries):
            try:
                return self.extract(note_content)
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Extraction failed after {max_retries} attempts: {e}")
                    return None
                print(f"⚠️  Extraction attempt {attempt + 1} failed, retrying...")

        return None

    def chunk_and_extract(
        self, note_content: str, max_tokens: int = 4000
    ) -> NoteExtraction:
        """
        Extract todos from very long notes by chunking.

        Args:
            note_content: The note text to analyze
            max_tokens: Maximum tokens per chunk (rough estimate: ~4 chars per token)

        Returns:
            Combined NoteExtraction from all chunks
        """
        # Rough token estimation
        max_chars = max_tokens * 4

        if len(note_content) <= max_chars:
            # Content fits in one chunk
            return self.extract(note_content)

        # Split into chunks (by paragraphs to avoid cutting sentences)
        paragraphs = note_content.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_length = len(para)
            if current_length + para_length > max_chars and current_chunk:
                # Start new chunk
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        # Extract from each chunk
        all_todos = []
        titles = []

        for i, chunk in enumerate(chunks):
            print(f"  Processing chunk {i+1}/{len(chunks)}...")
            result = self.extract(chunk)
            all_todos.extend(result.todos)
            titles.append(result.title)

        # Combine results
        combined_title = titles[0] if titles else "Untitled Note"

        return NoteExtraction(
            title=combined_title,
            todos=all_todos,
            note_type="general",
        )
