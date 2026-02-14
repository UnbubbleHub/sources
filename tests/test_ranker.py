"""Tests for the MMR diversity ranker."""

import pytest

from unbubble_sources.data import (
    AnnotatedSource,
    Article,
    PerspectiveAnnotation,
    PolicyFrame,
    PoliticalLean,
    StakeholderType,
)
from unbubble_sources.ranker.mmr import (
    MMRRanker,
    _categorical_distance,
    _frame_distance,
    _political_distance,
    perspective_distance,
)

# -- Distance function tests --


def test_political_distance_same() -> None:
    assert _political_distance(PoliticalLean.LEFT, PoliticalLean.LEFT) == 0.0


def test_political_distance_max() -> None:
    d = _political_distance(PoliticalLean.FAR_LEFT, PoliticalLean.FAR_RIGHT)
    assert d == pytest.approx(1.0)


def test_political_distance_one_step() -> None:
    d = _political_distance(PoliticalLean.CENTER, PoliticalLean.CENTER_LEFT)
    assert d == pytest.approx(1 / 6)


def test_political_distance_unknown() -> None:
    assert _political_distance(PoliticalLean.UNKNOWN, PoliticalLean.LEFT) == 0.5
    assert _political_distance(PoliticalLean.LEFT, PoliticalLean.UNKNOWN) == 0.5
    assert _political_distance(PoliticalLean.UNKNOWN, PoliticalLean.UNKNOWN) == 0.5


def test_frame_distance_identical() -> None:
    a = PerspectiveAnnotation(policy_frames=(PolicyFrame.ECONOMIC, PolicyFrame.MORALITY))
    b = PerspectiveAnnotation(policy_frames=(PolicyFrame.ECONOMIC, PolicyFrame.MORALITY))
    assert _frame_distance(a, b) == pytest.approx(0.0)


def test_frame_distance_disjoint() -> None:
    a = PerspectiveAnnotation(policy_frames=(PolicyFrame.ECONOMIC,))
    b = PerspectiveAnnotation(policy_frames=(PolicyFrame.MORALITY,))
    assert _frame_distance(a, b) == pytest.approx(1.0)


def test_frame_distance_partial_overlap() -> None:
    a = PerspectiveAnnotation(policy_frames=(PolicyFrame.ECONOMIC, PolicyFrame.MORALITY))
    b = PerspectiveAnnotation(policy_frames=(PolicyFrame.ECONOMIC, PolicyFrame.POLITICAL))
    # intersection=1 (ECONOMIC), union=3 (ECONOMIC, MORALITY, POLITICAL)
    assert _frame_distance(a, b) == pytest.approx(1.0 - 1 / 3)


def test_frame_distance_both_empty() -> None:
    a = PerspectiveAnnotation(policy_frames=())
    b = PerspectiveAnnotation(policy_frames=())
    assert _frame_distance(a, b) == 0.0


def test_categorical_distance_same() -> None:
    assert _categorical_distance("US", "US") == 0.0


def test_categorical_distance_different() -> None:
    assert _categorical_distance("US", "EU") == 1.0


# -- perspective_distance tests --


def test_perspective_distance_identical() -> None:
    a = PerspectiveAnnotation(
        political_lean=PoliticalLean.CENTER,
        policy_frames=(PolicyFrame.ECONOMIC,),
        stakeholder_type=StakeholderType.JOURNALIST,
        geographic_focus="US",
        topic="climate",
    )
    assert perspective_distance(a, a) == pytest.approx(0.0)


def test_perspective_distance_maximally_different() -> None:
    a = PerspectiveAnnotation(
        political_lean=PoliticalLean.FAR_LEFT,
        policy_frames=(PolicyFrame.ECONOMIC,),
        stakeholder_type=StakeholderType.GOVERNMENT,
        geographic_focus="US",
        topic="climate",
    )
    b = PerspectiveAnnotation(
        political_lean=PoliticalLean.FAR_RIGHT,
        policy_frames=(PolicyFrame.MORALITY,),
        stakeholder_type=StakeholderType.CORPORATE,
        geographic_focus="EU",
        topic="economy",
    )
    d = perspective_distance(a, b)
    # 0.30*1.0 + 0.25*1.0 + 0.20*1.0 + 0.15*1.0 + 0.10*1.0 = 1.0
    assert d == pytest.approx(1.0)


def test_perspective_distance_symmetric() -> None:
    a = PerspectiveAnnotation(
        political_lean=PoliticalLean.LEFT,
        policy_frames=(PolicyFrame.ECONOMIC,),
        stakeholder_type=StakeholderType.ACADEMIC,
    )
    b = PerspectiveAnnotation(
        political_lean=PoliticalLean.RIGHT,
        policy_frames=(PolicyFrame.MORALITY, PolicyFrame.POLITICAL),
        stakeholder_type=StakeholderType.GOVERNMENT,
    )
    assert perspective_distance(a, b) == pytest.approx(perspective_distance(b, a))


# -- MMRRanker tests --


def _make_annotated(
    url: str,
    lean: PoliticalLean,
    frames: tuple[PolicyFrame, ...],
    stakeholder: StakeholderType,
    geo: str,
    relevance: float,
) -> AnnotatedSource:
    return AnnotatedSource(
        source=Article(title=f"Article {url}", url=url, source="example.com"),
        annotation=PerspectiveAnnotation(
            political_lean=lean,
            policy_frames=frames,
            stakeholder_type=stakeholder,
            geographic_focus=geo,
            topic="test",
        ),
        relevance_score=relevance,
    )


@pytest.fixture
def diverse_sources() -> list[AnnotatedSource]:
    return [
        _make_annotated(
            "https://a.com",
            PoliticalLean.LEFT,
            (PolicyFrame.ECONOMIC,),
            StakeholderType.JOURNALIST,
            "US",
            0.9,
        ),
        _make_annotated(
            "https://b.com",
            PoliticalLean.RIGHT,
            (PolicyFrame.MORALITY,),
            StakeholderType.CORPORATE,
            "UK",
            0.8,
        ),
        _make_annotated(
            "https://c.com",
            PoliticalLean.CENTER,
            (PolicyFrame.POLITICAL,),
            StakeholderType.GOVERNMENT,
            "EU",
            0.7,
        ),
        _make_annotated(
            "https://d.com",
            PoliticalLean.LEFT,
            (PolicyFrame.ECONOMIC,),
            StakeholderType.JOURNALIST,
            "US",
            0.85,
        ),  # Similar to source a
        _make_annotated(
            "https://e.com",
            PoliticalLean.FAR_RIGHT,
            (PolicyFrame.SECURITY_AND_DEFENSE,),
            StakeholderType.GOVERNMENT,
            "US",
            0.6,
        ),
    ]


def test_mmr_returns_requested_count(diverse_sources: list[AnnotatedSource]) -> None:
    ranker = MMRRanker(lambda_param=0.5)
    result = ranker.rank(diverse_sources, top_k=3)
    assert len(result) == 3


def test_mmr_first_pick_is_highest_relevance(
    diverse_sources: list[AnnotatedSource],
) -> None:
    ranker = MMRRanker(lambda_param=0.5)
    result = ranker.rank(diverse_sources, top_k=5)
    # Source a has relevance 0.9, should be first
    assert result[0].source.url == "https://a.com"


def test_mmr_prefers_diversity_over_similar(
    diverse_sources: list[AnnotatedSource],
) -> None:
    ranker = MMRRanker(lambda_param=0.5)
    result = ranker.rank(diverse_sources, top_k=3)
    urls = [r.source.url for r in result]
    # Source d is very similar to a, so b and c should be picked before d
    assert "https://b.com" in urls
    assert "https://c.com" in urls


def test_mmr_high_lambda_favors_relevance() -> None:
    """With lambda=1.0, MMR degenerates to pure relevance ranking."""
    sources = [
        _make_annotated(
            "https://a.com",
            PoliticalLean.LEFT,
            (PolicyFrame.ECONOMIC,),
            StakeholderType.JOURNALIST,
            "US",
            0.9,
        ),
        _make_annotated(
            "https://b.com",
            PoliticalLean.LEFT,
            (PolicyFrame.ECONOMIC,),
            StakeholderType.JOURNALIST,
            "US",
            0.8,
        ),
        _make_annotated(
            "https://c.com",
            PoliticalLean.RIGHT,
            (PolicyFrame.MORALITY,),
            StakeholderType.CORPORATE,
            "UK",
            0.7,
        ),
    ]
    ranker = MMRRanker(lambda_param=1.0)
    result = ranker.rank(sources, top_k=3)
    # Pure relevance order
    assert result[0].source.url == "https://a.com"
    assert result[1].source.url == "https://b.com"
    assert result[2].source.url == "https://c.com"


def test_mmr_low_lambda_favors_diversity() -> None:
    """With lambda=0.0, MMR picks maximally diverse sources."""
    sources = [
        _make_annotated(
            "https://a.com",
            PoliticalLean.LEFT,
            (PolicyFrame.ECONOMIC,),
            StakeholderType.JOURNALIST,
            "US",
            0.9,
        ),
        _make_annotated(
            "https://b.com",
            PoliticalLean.LEFT,
            (PolicyFrame.ECONOMIC,),
            StakeholderType.JOURNALIST,
            "US",
            0.8,
        ),
        _make_annotated(
            "https://c.com",
            PoliticalLean.FAR_RIGHT,
            (PolicyFrame.MORALITY,),
            StakeholderType.CORPORATE,
            "UK",
            0.3,
        ),
    ]
    ranker = MMRRanker(lambda_param=0.0)
    result = ranker.rank(sources, top_k=2)
    urls = {r.source.url for r in result}
    # Should pick a (highest relevance first), then c (most diverse) despite low relevance
    assert "https://a.com" in urls
    assert "https://c.com" in urls


def test_mmr_empty_input() -> None:
    ranker = MMRRanker()
    assert ranker.rank([], top_k=5) == []


def test_mmr_top_k_larger_than_input(
    diverse_sources: list[AnnotatedSource],
) -> None:
    ranker = MMRRanker()
    result = ranker.rank(diverse_sources, top_k=100)
    assert len(result) == len(diverse_sources)


def test_mmr_single_source() -> None:
    source = _make_annotated(
        "https://a.com", PoliticalLean.CENTER, (), StakeholderType.JOURNALIST, "US", 1.0
    )
    ranker = MMRRanker()
    result = ranker.rank([source], top_k=5)
    assert len(result) == 1
    assert result[0].source.url == "https://a.com"
