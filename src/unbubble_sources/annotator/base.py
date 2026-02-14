"""Protocol for source annotation."""

from typing import Protocol

from unbubble_sources.data import AnnotatedSource, Source, Usage


class SourceAnnotator(Protocol):
    """Interface for annotating sources with perspective metadata."""

    async def annotate(
        self,
        sources: list[Source],
        event_description: str,
    ) -> tuple[list[AnnotatedSource], Usage]:
        """Annotate sources with perspective metadata.

        Args:
            sources: Raw sources to annotate.
            event_description: The news event description for context.

        Returns:
            Tuple of (annotated sources, usage).
        """
        ...
