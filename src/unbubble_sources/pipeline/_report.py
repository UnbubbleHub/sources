"""Helper to construct the per-run ``DiversityReport``.

Lives in :mod:`unbubble_sources.pipeline` because both pipelines need
it; module-private (leading underscore) so it does not become part of
the public API. Future PRs that make the perspective-distance weights
configurable should source ``_PERSPECTIVE_AXES`` / ``_PERSPECTIVE_WEIGHTS``
from the ranker config instead of hard-coding here.
"""

from collections.abc import Sequence

from unbubble_sources.data import AnnotatedSource, DiversityReport
from unbubble_sources.ranker.mmr import MMRRanker

# Mirrors the weights hard-coded in ``unbubble_sources.ranker.mmr``.
# Kept in sync by convention until a future refactor exposes them from
# the ranker itself.
_PERSPECTIVE_AXES: tuple[str, ...] = (
    "political_lean",
    "policy_frames",
    "stakeholder_type",
    "geographic_focus",
    "topic",
)
_PERSPECTIVE_WEIGHTS: dict[str, float] = {
    "political_lean": 0.30,
    "policy_frames": 0.25,
    "stakeholder_type": 0.20,
    "geographic_focus": 0.15,
    "topic": 0.10,
}


def build_diversity_report(
    *,
    annotator_name: str | None,
    fallback_used: bool,
    ranker: MMRRanker | None,
    ranker_top_k: int,
    annotated_sources: Sequence[AnnotatedSource],
    total_source_count: int,
) -> DiversityReport:
    """Build the run's ``DiversityReport``.

    Args:
        annotator_name: Class name of the annotator that actually ran
            (main or fallback), or ``None`` if no annotation step ran.
        fallback_used: True iff the fallback path produced the
            annotations (rather than the main annotator).
        ranker: The ranker instance, if one ran. Used to record name
            and parameters.
        ranker_top_k: ``top_k`` parameter the ranker was configured with.
        annotated_sources: Annotated sources to derive the
            ``lean_distribution`` from. Pass an empty sequence when no
            annotation ran.
        total_source_count: Length of the pipeline's final source
            list (may differ from ``len(annotated_sources)`` if the
            final list isn't annotated).

    Returns:
        A populated ``DiversityReport``.
    """
    lean_distribution: dict[str, int] = {}
    for src in annotated_sources:
        key = src.annotation.political_lean.value
        lean_distribution[key] = lean_distribution.get(key, 0) + 1

    axes = _PERSPECTIVE_AXES if ranker is not None else ()
    weights = dict(_PERSPECTIVE_WEIGHTS) if ranker is not None else {}
    ranker_name = type(ranker).__name__ if ranker is not None else None
    ranker_params: dict[str, object] = {}
    if ranker is not None:
        # MMRRanker keeps lambda_param as ``_lambda``; expose only the
        # public-meaningful values in the report.
        ranker_params = {
            "lambda_param": getattr(ranker, "_lambda", None),
            "top_k": ranker_top_k,
        }

    return DiversityReport(
        axes_considered=axes,
        weights=weights,
        ranker=ranker_name,
        ranker_params=ranker_params,
        annotator=annotator_name,
        fallback_annotator_used=fallback_used,
        source_count=total_source_count,
        lean_distribution=lean_distribution,
    )
