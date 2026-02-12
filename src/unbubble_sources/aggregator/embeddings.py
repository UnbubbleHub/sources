"""Text embedding utilities for query aggregation."""

from typing import Protocol

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer


class TextEmbedder(Protocol):
    """Interface for text embedding models."""

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Embed a batch of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            Array of shape (len(texts), embedding_dim).
        """
        ...


class SentenceTransformerEmbedder:
    """Embedder using sentence-transformers library."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:

        self._model: SentenceTransformer = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Embed texts using sentence-transformers."""
        embeddings: NDArray[np.float32] = self._model.encode(texts, convert_to_numpy=True).astype(
            np.float32
        )
        return embeddings
