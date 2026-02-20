"""ChromaDB vector store operations."""

from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from terminal_todos.config import get_settings
from terminal_todos.vector.embeddings import embed_text

# Global ChromaDB client
_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create the ChromaDB persistent client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(
            path=str(settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_or_create_collection(name: str):
    """Get or create a collection by name."""
    client = get_chroma_client()
    return client.get_or_create_collection(name=name)


class VectorStore:
    """Vector store wrapper for todos and notes."""

    def __init__(self):
        self.client = get_chroma_client()
        self.todos_collection = get_or_create_collection("todos")
        self.notes_collection = get_or_create_collection("notes")

    # Todo operations
    def upsert_todo(
        self, todo_id: int, content: str, completed: bool, created_at: str
    ) -> None:
        """Upsert a todo to the vector store."""
        embedding = embed_text(content)
        doc_id = f"todo_{todo_id}"

        self.todos_collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[
                {
                    "todo_id": todo_id,
                    "completed": completed,
                    "created_at": created_at,
                }
            ],
        )

    def delete_todo(self, todo_id: int) -> None:
        """Delete a todo from the vector store."""
        doc_id = f"todo_{todo_id}"
        try:
            self.todos_collection.delete(ids=[doc_id])
        except Exception:
            # Todo might not exist in vector store
            pass

    def search_todos(
        self,
        query: str,
        k: int = 10,
        completed: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Search todos semantically."""
        query_embedding = embed_text(query)

        # Build where filter
        where = {}
        if completed is not None:
            where["completed"] = completed

        results = self.todos_collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where if where else None,
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted_results.append(
                    {
                        "id": results["ids"][0][i],
                        "todo_id": results["metadatas"][0][i]["todo_id"],
                        "content": results["documents"][0][i],
                        "distance": results["distances"][0][i]
                        if "distances" in results
                        else 0,
                        "metadata": results["metadatas"][0][i],
                    }
                )

        return formatted_results

    # Note operations
    def upsert_note(
        self,
        note_id: int,
        content: str,
        title: Optional[str],
        created_at: str,
        # Enhanced metadata fields
        note_type: Optional[str] = None,
        category: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        summary: Optional[str] = None,
        updated_at: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Upsert a note to the vector store with enhanced metadata."""
        # Combine title, summary, and content for better search
        search_parts = []
        if title:
            search_parts.append(title)
        if summary:
            search_parts.append(summary)
        search_parts.append(content)
        search_text = "\n".join(search_parts)

        embedding = embed_text(search_text)
        doc_id = f"note_{note_id}"

        # Build rich metadata
        metadata = {
            "note_id": note_id,
            "title": title or "",
            "original_content": content,  # IMPORTANT: Store original content separately
            "created_at": created_at,
        }

        # Add new fields if provided
        if note_type:
            metadata["note_type"] = note_type
        if category:
            metadata["category"] = category
        if updated_at:
            metadata["updated_at"] = updated_at
        if summary:
            metadata["summary_preview"] = summary[:200]  # First 200 chars

        # Store keywords, topics, and tags as comma-separated for filtering
        if keywords:
            metadata["keywords"] = ",".join(keywords)
        if topics:
            metadata["topics"] = ",".join(topics)
        if tags:
            metadata["tags"] = ",".join(tags)

        # Store the full search text (title + summary + content) as the document
        # This ensures that when results are returned, the full context is available
        self.notes_collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[search_text],  # Use full search text, not just content
            metadatas=[metadata],
        )

    def delete_note(self, note_id: int) -> None:
        """Delete a note from the vector store."""
        doc_id = f"note_{note_id}"
        try:
            self.notes_collection.delete(ids=[doc_id])
        except Exception:
            # Note might not exist in vector store
            pass

    def search_notes(
        self,
        query: str,
        k: int = 10,
        category: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search notes semantically with optional filters."""
        query_embedding = embed_text(query)

        # Build where filter for category
        where = {}
        if category:
            where["category"] = category

        results = self.notes_collection.query(
            query_embeddings=[query_embedding],
            n_results=k * 2 if keywords else k,  # Get more if filtering by keywords
            where=where if where else None,
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "note_id": results["metadatas"][0][i]["note_id"],
                    "content": results["metadatas"][0][i].get("original_content", results["documents"][0][i]),
                    "title": results["metadatas"][0][i].get("title", ""),
                    "category": results["metadatas"][0][i].get("category", ""),
                    "distance": results["distances"][0][i]
                    if "distances" in results
                    else 0,
                    "metadata": results["metadatas"][0][i],
                }

                # Filter by keywords if provided
                if keywords:
                    note_keywords = results["metadatas"][0][i].get("keywords", "")
                    if note_keywords:
                        note_kw_list = note_keywords.split(",")
                        # Check if any requested keyword matches
                        if any(kw in note_kw_list for kw in keywords):
                            formatted_results.append(result)
                    else:
                        continue
                else:
                    formatted_results.append(result)

            # Trim to requested size
            formatted_results = formatted_results[:k]

        return formatted_results

    def reset(self) -> None:
        """Reset all collections (for testing)."""
        self.client.delete_collection("todos")
        self.client.delete_collection("notes")
        self.todos_collection = get_or_create_collection("todos")
        self.notes_collection = get_or_create_collection("notes")
