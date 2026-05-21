"""Scorer protocol.

Scorers are pluggable components that compute typed numeric ``Score``
values for sources after annotation. Rankers and metrics downstream
consume scores by ``name``.

The ``Score`` dataclass itself lives in :mod:`unbubble_sources.data`
alongside the other core data types — its presence on
``AnnotatedSource`` makes it a fundamental shape of pipeline output.

Every score carries its ``provenance`` so the meta-level (*which
component produced this number, with what method*) is inspectable, in
line with the project's "make the meta-level explicit" principle.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from unbubble_sources.data import Score, Source, Usage


@runtime_checkable
class Scorer(Protocol):
    """Interface for components that attach numeric scores to sources.

    A scorer takes a sequence of sources and returns one ``Score`` per
    source in the same order, alongside the API ``Usage`` it incurred.
    Implementations may inspect any attributes the source carries — for
    instance, an ``AnnotatedSource`` exposes its ``annotation`` and any
    pre-existing ``scores``.
    """

    name: str
    """Identifier used in config and logs."""

    async def score(
        self,
        sources: Sequence[Source],
        event_description: str,
    ) -> tuple[list[Score], Usage]:
        """Compute one score per input source.

        Args:
            sources: Sources to score, in deterministic order.
            event_description: The originating news event description,
                for scorers that need it (e.g. relevance scorers).

        Returns:
            ``(scores, usage)`` where ``scores`` has length
            ``len(sources)`` in the same order.
        """
        ...
