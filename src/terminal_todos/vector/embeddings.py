"""Embedding generation using sentence-transformers."""

import os
from typing import List, Optional, Union

# Disable tqdm progress bars to prevent multiprocessing errors in TUI
os.environ["TQDM_DISABLE"] = "1"

# Monkey-patch tqdm to completely disable it
try:
    import tqdm
    import tqdm.std

    # Replace tqdm with a no-op class
    class NoOpTqdm:
        def __init__(self, *args, **kwargs):
            self.iterable = args[0] if args else None
        def __iter__(self):
            return iter(self.iterable) if self.iterable is not None else iter([])
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def update(self, *args, **kwargs):
            pass
        def close(self):
            pass

    # Replace both tqdm and trange
    # trange is just range() with a progress bar, so we replace it with plain range()
    def no_op_trange(*args, **kwargs):
        # Remove tqdm-specific kwargs
        kwargs.pop('desc', None)
        kwargs.pop('disable', None)
        return range(*args)

    tqdm.tqdm = NoOpTqdm
    tqdm.std.tqdm = NoOpTqdm
    tqdm.std.trange = no_op_trange
    tqdm.trange = no_op_trange
except ImportError:
    pass

from sentence_transformers import SentenceTransformer

from terminal_todos.config import get_settings

# Global model instance (lazy loaded)
_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """Get or create the embedding model (lazy loading)."""
    global _model
    if _model is None:
        settings = get_settings()
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_text(text: str) -> List[float]:
    """Generate embedding for a single text."""
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_tensor=False, show_progress_bar=False)
    return embedding.tolist()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts (batch processing)."""
    if not texts:
        return []

    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


def get_embedding_dimension() -> int:
    """Get the dimension of the embedding model."""
    model = get_embedding_model()
    return model.get_sentence_embedding_dimension()


def reset_model() -> None:
    """Reset the model (useful for testing or changing models)."""
    global _model
    _model = None
