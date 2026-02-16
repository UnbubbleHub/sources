"""Maximal Marginal Relevance (MMR) diversity ranker.

Reference:
    Carbonell, J. & Goldstein, J. (1998). "The Use of MMR, Diversity-Based
    Reranking for Reordering Documents and Producing Summaries." SIGIR '98.

MMR balances relevance and diversity:

    MMR(d) = λ · relevance(d) - (1 - λ) · max_similarity(d, selected)

Where max_similarity measures perspective overlap across multiple dimensions
(political lean, frames, stakeholder type, geography).
"""

import logging

from unbubble_sources.data import AnnotatedSource, PerspectiveAnnotation, PoliticalLean

logger = logging.getLogger(__name__)

# Ordered political lean values for computing distance
_POLITICAL_LEAN_ORDER: list[PoliticalLean] = [
    PoliticalLean.FAR_LEFT,
    PoliticalLean.LEFT,
    PoliticalLean.CENTER_LEFT,
    PoliticalLean.CENTER,
    PoliticalLean.CENTER_RIGHT,
    PoliticalLean.RIGHT,
    PoliticalLean.FAR_RIGHT,
]


def _political_distance(a: PoliticalLean, b: PoliticalLean) -> float:
    """Compute normalized distance between two political leans.

    Returns a value in [0.0, 1.0] where 1.0 = maximally different.
    UNKNOWN is treated as 0.5 distance from everything.
    """
    if a == PoliticalLean.UNKNOWN or b == PoliticalLean.UNKNOWN:
        return 0.5
    if a == b:
        return 0.0
    try:
        idx_a = _POLITICAL_LEAN_ORDER.index(a)
        idx_b = _POLITICAL_LEAN_ORDER.index(b)
    except ValueError:
        return 0.5
    max_dist = len(_POLITICAL_LEAN_ORDER) - 1
    return abs(idx_a - idx_b) / max_dist


def _frame_distance(a: PerspectiveAnnotation, b: PerspectiveAnnotation) -> float:
    """Compute Jaccard distance between policy frame sets.

    Returns a value in [0.0, 1.0] where 1.0 = no frame overlap.
    """
    set_a = set(a.policy_frames)
    set_b = set(b.policy_frames)
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    intersection = set_a & set_b
    return 1.0 - len(intersection) / len(union)


def _categorical_distance(val_a: str, val_b: str) -> float:
    """Binary distance for categorical values: 0 if equal, 1 if different."""
    return 0.0 if val_a == val_b else 1.0


def perspective_distance(a: PerspectiveAnnotation, b: PerspectiveAnnotation) -> float:
    """Compute multi-dimensional perspective distance between two annotations.

    Aggregates distances across five dimensions with empirically motivated
    weights that prioritize political lean and framing differences:

    - Political lean (weight=0.30): ordinal distance on MBFC 7-point scale
    - Policy frames (weight=0.25): Jaccard distance on Boydstun frames
    - Stakeholder type (weight=0.20): categorical (same/different)
    - Geographic focus (weight=0.15): categorical (same/different)
    - Topic (weight=0.10): categorical (same/different)

    Returns:
        Float in [0.0, 1.0] where 1.0 = maximally different perspectives.
    """
    political = _political_distance(a.political_lean, b.political_lean)
    frames = _frame_distance(a, b)
    stakeholder = _categorical_distance(a.stakeholder_type.value, b.stakeholder_type.value)
    geography = _categorical_distance(a.geographic_focus, b.geographic_focus)
    topic = _categorical_distance(a.topic, b.topic)

    return 0.30 * political + 0.25 * frames + 0.20 * stakeholder + 0.15 * geography + 0.10 * topic


class MMRRanker:
    """Select diverse sources using Maximal Marginal Relevance.

    MMR iteratively selects sources that are both relevant to the query and
    diverse from already-selected sources. The ``lambda_param`` controls
    the trade-off: higher values favor relevance, lower values favor diversity.

    Reference:
        Carbonell, J. & Goldstein, J. (1998). SIGIR '98.

    Args:
        lambda_param: Trade-off between relevance (1.0) and diversity (0.0).
            Default 0.5 gives equal weight to both.
    """

    def __init__(self, lambda_param: float = 0.5) -> None:
        self._lambda = lambda_param

    def rank(
        self,
        sources: list[AnnotatedSource],
        top_k: int,
    ) -> list[AnnotatedSource]:
        """Select top-k sources maximizing both relevance and diversity.

        Algorithm:
            1. Start with the highest-relevance source.
            2. Iteratively pick the source maximizing:
               MMR(d) = λ · relevance(d) - (1-λ) · max_sim(d, selected)

        Args:
            sources: Annotated sources to rank.
            top_k: Number of sources to select.

        Returns:
            List of top-k diverse, relevant sources.
        """
        if not sources:
            return []

        k = min(top_k, len(sources))
        remaining = list(range(len(sources)))
        selected: list[int] = []

        # First pick: highest relevance
        best_idx = max(remaining, key=lambda i: sources[i].relevance_score)
        selected.append(best_idx)
        remaining.remove(best_idx)

        # Iterative MMR selection
        for _ in range(k - 1):
            if not remaining:
                break

            best_mmr = -float("inf")
            best_candidate = remaining[0]

            for candidate_idx in remaining:
                candidate = sources[candidate_idx]
                relevance = candidate.relevance_score

                # Max similarity to any already-selected source
                max_sim = max(
                    1.0 - perspective_distance(candidate.annotation, sources[s].annotation)
                    for s in selected
                )

                mmr_score = self._lambda * relevance - (1 - self._lambda) * max_sim

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_candidate = candidate_idx

            selected.append(best_candidate)
            remaining.remove(best_candidate)

        return [sources[i] for i in selected]
