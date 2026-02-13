"""Pipeline protocol for end-to-end news discovery."""

from typing import Protocol

from unbubble_sources.data import NewsEvent, Source, Usage


class Pipeline(Protocol):
    """Interface for end-to-end news discovery pipelines."""

    async def run(
        self,
        event: NewsEvent,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> tuple[list[Source], Usage]:
        """Execute the pipeline to find diverse sources about an event.

        Args:
            event: The news event to investigate.
            from_date: Optional start date filter.
            to_date: Optional end date filter.

        Returns:
            Tuple of (diverse deduplicated sources, usage).
        """
        ...
