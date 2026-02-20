"""Semantic search functionality."""

from typing import Any, Dict, List, Optional

from terminal_todos.vector.store import VectorStore


class SemanticSearch:
    """Semantic search wrapper with relevance scoring."""

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()

    def search_todos(
        self,
        query: str,
        k: int = 10,
        completed: Optional[bool] = None,
        relevance_threshold: float = 0.2,
        min_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search todos with relevance filtering.

        Args:
            query: Search query
            k: Number of results to return
            completed: Filter by completion status (None = all)
            relevance_threshold: Default threshold (not used unless min_threshold set)
            min_threshold: Optional strict minimum threshold for filtering

        Returns:
            List of search results with relevance scores, sorted by relevance
        """
        results = self.vector_store.search_todos(query, k=k, completed=completed)

        # Add relevance score to all results
        scored_results = []
        for result in results:
            # Convert distance to relevance score (0-1, higher = more relevant)
            distance = result.get("distance", 0)
            relevance = 1 / (1 + distance)
            result["relevance"] = relevance

            # Only apply strict filtering if min_threshold is explicitly set
            if min_threshold is None or distance <= min_threshold:
                scored_results.append(result)

        # Sort by relevance (highest first)
        scored_results.sort(key=lambda x: x["relevance"], reverse=True)

        return scored_results

    def search_notes(
        self,
        query: str,
        k: int = 10,
        relevance_threshold: float = 0.2,
        min_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search notes with relevance filtering.

        Args:
            query: Search query
            k: Number of results to return
            relevance_threshold: Default threshold (not used unless min_threshold set)
            min_threshold: Optional strict minimum threshold for filtering

        Returns:
            List of search results with relevance scores, sorted by relevance
        """
        results = self.vector_store.search_notes(query, k=k)

        # Add relevance score to all results
        scored_results = []
        for result in results:
            # Convert distance to relevance score (0-1, higher = more relevant)
            distance = result.get("distance", 0)
            relevance = 1 / (1 + distance)
            result["relevance"] = relevance

            # Only apply strict filtering if min_threshold is explicitly set
            if min_threshold is None or distance <= min_threshold:
                scored_results.append(result)

        # Sort by relevance (highest first) and return top K
        scored_results.sort(key=lambda x: x["relevance"], reverse=True)

        return scored_results

    def search_all(
        self,
        query: str,
        k: int = 10,
        relevance_threshold: float = 0.5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search both todos and notes.

        Returns:
            Dictionary with 'todos' and 'notes' keys containing results
        """
        return {
            "todos": self.search_todos(query, k=k, relevance_threshold=relevance_threshold),
            "notes": self.search_notes(query, k=k, relevance_threshold=relevance_threshold),
        }

    def find_similar_todos(self, todo_content: str, k: int = 5) -> List[Dict[str, Any]]:
        """Find similar todos to the given content."""
        return self.search_todos(todo_content, k=k, completed=None)

    def find_similar_notes(self, note_content: str, k: int = 5) -> List[Dict[str, Any]]:
        """Find similar notes to the given content."""
        return self.search_notes(note_content, k=k)
