"""Protocol for source ranking."""

from typing import Protocol

from unbubble_sources.data import AnnotatedSource


class SourceRanker(Protocol):
    """Interface for ranking annotated sources by diversity."""

    def rank(
        self,
        sources: list[AnnotatedSource],
        top_k: int,
    ) -> list[AnnotatedSource]:
        """Select the top-k most diverse and relevant sources.

        Args:
            sources: Annotated sources to rank.
            top_k: Number of sources to return.

        Returns:
            Ranked list of top-k sources.
        """
        ...
