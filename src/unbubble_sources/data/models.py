"""Core data models for Unbubble."""

from dataclasses import dataclass, field
from enum import StrEnum


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
    published_at: str | None = None
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
class AnnotatedSource:
    """A source paired with its LLM-extracted perspective annotation.

    Wraps the original ``Source`` (Article or Tweet) alongside computed
    metadata used for diversity ranking.
    """

    source: Source
    annotation: PerspectiveAnnotation
    relevance_score: float = 0.0


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

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            api_calls=self.api_calls + other.api_calls,
            gnews_requests=self.gnews_requests + other.gnews_requests,
            x_api_requests=self.x_api_requests + other.x_api_requests,
            exa_requests=self.exa_requests + other.exa_requests,
            estimated_cost=self.estimated_cost + other.estimated_cost,
        )

    def __iadd__(self, other: "Usage") -> "Usage":
        self.api_calls.extend(other.api_calls)
        self.gnews_requests += other.gnews_requests
        self.x_api_requests += other.x_api_requests
        self.exa_requests += other.exa_requests
        self.estimated_cost += other.estimated_cost
        return self
