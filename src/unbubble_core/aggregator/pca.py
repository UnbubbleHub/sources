"""PCA-based query aggregation."""

import numpy as np

from unbubble_core.aggregator.embeddings import SentenceTransformerEmbedder
from unbubble_core.data import SearchQuery


class PCAAggregator:
    """Aggregate queries using PCA-based diversity selection.

    Algorithm:
    1. Embed all query texts into dense vectors
    2. Compute PCA to find top K principal components
    3. For each principal component direction, select the query
       with highest cosine similarity to that direction
    4. Return K unique, maximally diverse queries

    Args:
        n_components: Number of diverse queries to return.
        sentence_transformer_model: Model name for sentence-transformers.
    """

    def __init__(
        self,
        n_components: int = 5,
        sentence_transformer_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._n_components = n_components
        self._embedder = SentenceTransformerEmbedder(sentence_transformer_model)

    async def aggregate(self, queries: list[SearchQuery]) -> list[SearchQuery]:
        """Select diverse queries using PCA-based selection.

        Args:
            queries: Input queries to aggregate.

        Returns:
            List of K most diverse queries.
        """
        if len(queries) <= self._n_components:
            return queries

        # Step 1: Embed all query texts
        texts = [q.text for q in queries]
        embeddings = self._embedder.embed(texts)

        # Step 2: Center the embeddings (required for PCA)
        centered = embeddings - embeddings.mean(axis=0)

        # Step 3: Compute PCA via SVD
        # U @ S @ Vt = centered
        # V contains the principal components (rows of Vt)
        _, _, vt = np.linalg.svd(centered, full_matrices=False)

        # Get top K principal components
        k = min(self._n_components, len(vt))
        principal_components = vt[:k]  # Shape: (k, embedding_dim)

        # Step 4: For each PC, find the query with highest cosine similarity
        selected_indices: list[int] = []

        embedding_norms = np.linalg.norm(embeddings, axis=1)

        for pc in principal_components:
            # Compute cosine similarity between PC and all embeddings
            pc_norm = float(np.linalg.norm(pc))
            if pc_norm == 0:
                continue

            similarities = embeddings @ pc / (embedding_norms * pc_norm + 1e-10)

            # Find query with highest absolute similarity (direction or opposite)
            abs_similarities = np.abs(similarities)

            # Select best match not already selected
            sorted_indices = np.argsort(abs_similarities)[::-1]
            for idx_np in sorted_indices:
                idx = int(idx_np)
                if idx not in selected_indices:
                    selected_indices.append(idx)
                    break

        return [queries[i] for i in selected_indices]


class NoOpAggregator:
    """Pass-through aggregator that returns queries unchanged."""

    async def aggregate(self, queries: list[SearchQuery]) -> list[SearchQuery]:
        """Return queries unchanged.

        Args:
            queries: Input queries.

        Returns:
            Same queries, unchanged.
        """
        return queries
