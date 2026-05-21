"""Core data models for Unbubble."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Forward reference only: MetricResult lives in unbubble_sources.metrics,
    # which itself imports from this module. The dataclass field below is
    # typed as the runtime-erased forward reference so we keep a clean
    # one-way dependency: metrics -> data, never the reverse at runtime.
    from unbubble_sources.metrics.base import MetricResult


class PolicyFrame(StrEnum):
    """Boydstun et al. (2014) Policy Frames Codebook — 15 generic frames.

    Reference:
        Boydstun, A.E., Gross, J.H., Resnik, P., & Smith, N.A. (2014).
        "Tracking the Development of Media Frames within and across Policy
        Issues." Carnegie Mellon University.
    """

    ECONOMIC = "economic"
    CAPACITY_AND_RESOURCES = "capacity_and_resources"
    MORALITY = "morality"
    FAIRNESS_AND_EQUALITY = "fairness_and_equality"
    LEGALITY_CONSTITUTIONALITY = "legality_constitutionality"
    POLICY_PRESCRIPTION = "policy_prescription"
    CRIME_AND_PUNISHMENT = "crime_and_punishment"
    SECURITY_AND_DEFENSE = "security_and_defense"
    HEALTH_AND_SAFETY = "health_and_safety"
    QUALITY_OF_LIFE = "quality_of_life"
    CULTURAL_IDENTITY = "cultural_identity"
    PUBLIC_OPINION = "public_opinion"
    POLITICAL = "political"
    EXTERNAL_REGULATION = "external_regulation"
    OTHER = "other"


class StakeholderType(StrEnum):
    """Stakeholder categories for source diversity analysis."""

    GOVERNMENT = "government"
    CORPORATE = "corporate"
    CIVIL_SOCIETY = "civil_society"
    ACADEMIC = "academic"
    JOURNALIST = "journalist"
    CITIZEN = "citizen"
    INTERNATIONAL_ORG = "international_org"
    OTHER = "other"


class PoliticalLean(StrEnum):
    """Political lean on a 7-point scale (MBFC-derived).

    Reference:
        Baly, R., Da San Martino, G., Glass, J., & Nakov, P. (2020).
        "We Can Detect Your Bias: Predicting the Political Ideology of
        News Media." EMNLP 2020.
    """

    FAR_LEFT = "far_left"
    LEFT = "left"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    RIGHT = "right"
    FAR_RIGHT = "far_right"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NewsEvent:
    """A news event or factual claim to investigate."""

    description: str
    date: str | None = None
    context: str | None = None


@dataclass(frozen=True)
class SearchQuery:
    """A search query generated from a news event."""

    text: str
    intent: str


@dataclass(frozen=True)
class Source:
    """Base type for any retrieved source (article, tweet, etc.)."""

    url: str
    source: str
    published_at: datetime | None = None
    query: SearchQuery | None = None


@dataclass(frozen=True)
class Article(Source):
    """A news article retrieved from search."""

    title: str = ""
    description: str | None = None


@dataclass(frozen=True)
class Tweet(Source):
    """A tweet retrieved from X/Twitter search."""

    tweet_id: str = ""
    author_handle: str = ""
    author_name: str = ""
    text: str = ""
    retweet_count: int = 0
    like_count: int = 0
    reply_count: int = 0


@dataclass(frozen=True)
class PerspectiveAnnotation:
    """LLM-extracted perspective metadata for a source.

    Each field captures a different dimension of the source's perspective,
    based on validated frameworks from media studies:

    - ``political_lean``: MBFC 7-point scale (Baly et al., 2020).
    - ``policy_frames``: Boydstun et al. (2014) Policy Frames Codebook.
    - ``stakeholder_type``: Primary stakeholder voice in the source.
    - ``stance_summary``: Free-text summary of the source's position.
    - ``topic``: IPTC-style topic label for the source.
    - ``geographic_focus``: Country/region the source focuses on.
    """

    political_lean: PoliticalLean = PoliticalLean.UNKNOWN
    policy_frames: tuple[PolicyFrame, ...] = ()
    stakeholder_type: StakeholderType = StakeholderType.OTHER
    stance_summary: str = ""
    topic: str = ""
    geographic_focus: str = ""


@dataclass(frozen=True)
class Score:
    """A typed numeric score attached to a source.

    Scores are produced by :class:`unbubble_sources.scoring.Scorer`
    components (and by annotators that bundle scoring with annotation,
    such as :class:`unbubble_sources.annotator.ClaudeAnnotator`).
    Downstream consumers — rankers, metrics, the diversity report —
    look up scores by ``name``.

    Attributes:
        name: Short identifier used to look the score up
            (e.g. ``"relevance"``, ``"compass_x"``, ``"credibility"``).
        value: The numeric value.
        range: Optional ``(min, max)`` declaring the score's valid
            interval. ``None`` means unbounded or domain-dependent.
        unit: Optional human-readable unit (e.g. ``"probability"``).
            ``None`` for dimensionless scores.
        provenance: Free-text label naming the component that produced
            the score (e.g. ``"ClaudeAnnotator"``, ``"MBFCLookup"``).
            Required for auditability per the project's "make the
            meta-level explicit" principle.
    """

    name: str
    value: float
    range: tuple[float, float] | None = None
    unit: str | None = None
    provenance: str = ""


@dataclass(frozen=True)
class AnnotatedSource:
    """A source paired with perspective annotation and typed scores.

    Wraps the original ``Source`` (Article or Tweet) alongside its
    symbolic ``PerspectiveAnnotation`` and any numeric ``scores``
    attached by annotators or downstream scorers. Use
    :meth:`get_score` to retrieve a score by name.

    Note:
        ``relevance_score`` is a **transitional** duplicate of the
        ``Score`` named ``"relevance"`` carried in :attr:`scores`. It
        exists only so the existing ``livedemo/`` frontend (which
        reads ``relevance_score`` from the wire JSON) keeps working
        during the migration. New Python code should read relevance via
        ``source.get_score("relevance").value``; the float field will
        be removed once the frontend migrates. Annotator implementations
        must keep the two in sync — see ``ClaudeAnnotator`` for the
        canonical pattern.
    """

    source: Source
    annotation: PerspectiveAnnotation
    scores: tuple[Score, ...] = ()
    relevance_score: float = 0.0
    """Transitional. Mirror of ``get_score("relevance").value``.
    Removed once the livedemo frontend migrates to ``scores``."""

    def get_score(self, name: str) -> Score | None:
        """Look up a score by name.

        Args:
            name: The ``Score.name`` to find (e.g. ``"relevance"``).

        Returns:
            The first matching score, or ``None`` if no score with
            that name is attached.
        """
        for s in self.scores:
            if s.name == name:
                return s
        return None


@dataclass(frozen=True)
class APICallUsage:
    """Usage from a single API call — carries model info for price lookup."""

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    web_searches: int = 0


@dataclass
class Usage:
    """Accumulated API usage across pipeline components."""

    api_calls: list[APICallUsage] = field(default_factory=list)
    gnews_requests: int = 0
    x_api_requests: int = 0
    exa_requests: int = 0
    estimated_cost: float = 0.0

    @property
    def input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.api_calls)

    @property
    def output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.api_calls)

    @property
    def cache_creation_input_tokens(self) -> int:
        return sum(c.cache_creation_input_tokens for c in self.api_calls)

    @property
    def cache_read_input_tokens(self) -> int:
        return sum(c.cache_read_input_tokens for c in self.api_calls)

    @property
    def web_searches(self) -> int:
        return sum(c.web_searches for c in self.api_calls)

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            api_calls=self.api_calls + other.api_calls,
            gnews_requests=self.gnews_requests + other.gnews_requests,
            x_api_requests=self.x_api_requests + other.x_api_requests,
            exa_requests=self.exa_requests + other.exa_requests,
            estimated_cost=self.estimated_cost + other.estimated_cost,
        )

    def __iadd__(self, other: Usage) -> Usage:
        self.api_calls.extend(other.api_calls)
        self.gnews_requests += other.gnews_requests
        self.x_api_requests += other.x_api_requests
        self.exa_requests += other.exa_requests
        self.estimated_cost += other.estimated_cost
        return self


@dataclass(frozen=True)
class DiversityReport:
    """The meta-level summary of a pipeline run.

    Captures *which axes of diversity the pipeline tried to cover, by
    what criteria, over how many sources*. Always populated by the
    pipeline (independent of which metrics are configured) so that the
    contestable structure of any run is observable from outside.

    Attributes:
        axes_considered: Annotation dimensions used by the ranker
            (e.g. ``["political_lean", "policy_frames", "stakeholder_type",
            "geographic_focus", "topic"]``). Empty if no ranker ran.
        weights: Per-dimension weights of the distance function. Empty
            if no ranker ran.
        ranker: Name of the ranker class that ran, or ``None``.
        ranker_params: Parameters of the ranker (e.g.
            ``{"lambda_param": 0.5}``).
        annotator: Name of the annotator class that ran, or ``None``.
        fallback_annotator_used: True iff the main annotator was
            absent and the fallback path ran instead.
        source_count: Number of sources in the final output.
        lean_distribution: Count of sources per ``PoliticalLean`` value
            in the final output (label → count).
    """

    axes_considered: tuple[str, ...] = ()
    weights: dict[str, float] = field(default_factory=dict)
    ranker: str | None = None
    ranker_params: dict[str, Any] = field(default_factory=dict)
    annotator: str | None = None
    fallback_annotator_used: bool = False
    source_count: int = 0
    lean_distribution: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    """The complete result of a pipeline run.

    Wraps the final source set with the accumulated ``Usage``, the
    list of computed ``MetricResult``s, and the always-populated
    ``DiversityReport``. This dataclass is what
    :meth:`unbubble_sources.pipeline.base.Pipeline.run` returns.

    Attributes:
        sources: Final pipeline sources (annotated and ranked when
            those steps were configured; raw otherwise).
        usage: Accumulated API/HTTP usage across all stages.
        metrics: Successful per-metric results, in metric-config
            order. Empty if no metrics were configured.
        diversity_report: Always-populated meta-level summary of the
            run.
    """

    sources: list[Source]
    usage: Usage
    metrics: list[MetricResult] = field(default_factory=list)
    diversity_report: DiversityReport = field(default_factory=DiversityReport)
