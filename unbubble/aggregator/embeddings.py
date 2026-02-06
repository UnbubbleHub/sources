"""Text embedding utilities for query aggregation."""

from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class TextEmbedder(Protocol):
    """Interface for text embedding models."""

    async def embed(self, texts: list[str]) -> NDArray[np.float32]:
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
        from sentence_transformers import SentenceTransformer

        self._model: SentenceTransformer = SentenceTransformer(model_name)

    async def embed(self, texts: list[str]) -> NDArray[np.float32]:
        """Embed texts using sentence-transformers.

        Note: sentence-transformers is sync, but we wrap for consistent interface.
        """
        embeddings: NDArray[np.float32] = self._model.encode(
            texts, convert_to_numpy=True
        ).astype(np.float32)
        return embeddings
