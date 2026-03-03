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
        relevance_threshold: float = 0.35,
        min_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search todos with relevance filtering.

        Args:
            query: Search query
            k: Number of results to return
            completed: Filter by completion status (None = all)
            relevance_threshold: Minimum relevance score (0-1) to include a result.
                                  relevance = 1 / (1 + L2_distance), so 0.35 ≈ distance ≤ 1.86.
            min_threshold: Optional distance-space upper bound (overrides relevance_threshold
                           when set — lower distance = better match).

        Returns:
            List of search results with relevance scores, sorted by relevance
        """
        results = self.vector_store.search_todos(query, k=k, completed=completed)

        scored_results = []
        for result in results:
            distance = result.get("distance", 0)
            relevance = 1 / (1 + distance)
            result["relevance"] = relevance

            if min_threshold is not None:
                # Caller supplied an explicit distance-space cutoff
                if distance <= min_threshold:
                    scored_results.append(result)
            else:
                # Use the relevance-space threshold (the normal path)
                if relevance >= relevance_threshold:
                    scored_results.append(result)

        scored_results.sort(key=lambda x: x["relevance"], reverse=True)

        return scored_results

    def search_notes(
        self,
        query: str,
        k: int = 10,
        relevance_threshold: float = 0.35,
        min_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search notes with relevance filtering.

        Args:
            query: Search query
            k: Number of results to return
            relevance_threshold: Minimum relevance score (0-1) to include a result.
            min_threshold: Optional distance-space upper bound (overrides relevance_threshold).

        Returns:
            List of search results with relevance scores, sorted by relevance
        """
        results = self.vector_store.search_notes(query, k=k)

        scored_results = []
        for result in results:
            distance = result.get("distance", 0)
            relevance = 1 / (1 + distance)
            result["relevance"] = relevance

            if min_threshold is not None:
                if distance <= min_threshold:
                    scored_results.append(result)
            else:
                if relevance >= relevance_threshold:
                    scored_results.append(result)

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
