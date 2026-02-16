"""Claude-based source annotator using structured JSON output."""

import asyncio
import json
import logging
import os

import anthropic

from unbubble_sources.data import (
    AnnotatedSource,
    APICallUsage,
    Article,
    PerspectiveAnnotation,
    PolicyFrame,
    PoliticalLean,
    Source,
    StakeholderType,
    Tweet,
    Usage,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a media analysis expert. For each news source provided, extract \
structured perspective metadata. Respond ONLY with a JSON array (no markdown \
fences, no commentary).

For each source, produce an object with these fields:
- "political_lean": one of: far_left, left, center_left, center, center_right, \
right, far_right, unknown
- "policy_frames": array of 1-3 frames from: economic, capacity_and_resources, \
morality, fairness_and_equality, legality_constitutionality, \
policy_prescription, crime_and_punishment, security_and_defense, \
health_and_safety, quality_of_life, cultural_identity, public_opinion, \
political, external_regulation, other
- "stakeholder_type": one of: government, corporate, civil_society, academic, \
journalist, citizen, international_org, other
- "stance_summary": 1-2 sentence summary of the source's position on the event
- "topic": short topic label (e.g. "climate policy", "immigration")
- "geographic_focus": primary country or region
- "relevance_score": float 0.0-1.0 measuring how directly and substantively \
the source covers the specific event. Use the full range of the scale:
  - 0.9-1.0: A primary source — the source is a direct participant, eyewitness, \
or the originator of the news (e.g. the official press release announcing a \
policy, a firsthand account from someone involved, the leaked document itself).
  - 0.7-0.8: In-depth original reporting — a dedicated article or thread that \
thoroughly reports on the event with original investigation, exclusive quotes, \
or significant new context not found elsewhere (e.g. an investigative piece \
with insider interviews, a detailed breakdown adding substantial new insight).
  - 0.5-0.6: Standard secondary coverage — a straightforward report on the event \
that covers the key facts but mostly aggregates or repackages information from \
other sources without much original analysis (e.g. a wire-service-style recap, \
a news article that summarizes what other outlets have already reported).
  - 0.3-0.4: Brief or shallow mention — the source acknowledges the event but \
covers it only superficially, or the event is a minor part of a broader piece \
(e.g. a weekly news roundup with one paragraph on the event, a related-topic \
article that briefly mentions it for context).
  - 0.2: Tangential — the source's main topic is adjacent to the event but the \
event itself is not the focus; the connection requires some inference \
(e.g. an article about broader industry trends that doesn't name the event \
but discusses its consequences indirectly).
  - 0.1: Barely related — the source covers the same general domain or theme \
but does not discuss this specific event; the connection is only thematic \
(e.g. a general op-ed about immigration policy when the event is a specific \
border incident, a background explainer published before the event occurred).
  - 0.0: Completely unrelated — the source has no meaningful connection to the \
event whatsoever.

Return a JSON array with one object per source, in the same order as the input.\
"""


def _source_to_prompt_text(source: Source, index: int) -> str:
    """Format a source for inclusion in the annotation prompt."""
    parts = [f"Source {index + 1}:"]
    parts.append(f"  URL: {source.url}")
    parts.append(f"  Publisher: {source.source}")
    if source.published_at:
        parts.append(f"  Published: {source.published_at}")
    if isinstance(source, Article):
        if source.title:
            parts.append(f"  Title: {source.title}")
        if source.description:
            parts.append(f"  Description: {source.description}")
    elif isinstance(source, Tweet):
        if source.author_handle:
            parts.append(f"  Author: @{source.author_handle} ({source.author_name})")
        if source.text:
            parts.append(f"  Text: {source.text}")
    return "\n".join(parts)


def _parse_annotation(raw: dict[str, object]) -> tuple[PerspectiveAnnotation, float]:
    """Parse a single annotation dict from the LLM response.

    Returns:
        Tuple of (annotation, relevance_score).
    """
    political_lean_str = str(raw.get("political_lean", "unknown"))
    try:
        political_lean = PoliticalLean(political_lean_str)
    except ValueError:
        political_lean = PoliticalLean.UNKNOWN

    raw_frames = raw.get("policy_frames", [])
    frames: list[PolicyFrame] = []
    if isinstance(raw_frames, list):
        for f in raw_frames:
            try:
                frames.append(PolicyFrame(str(f)))
            except ValueError:
                continue

    stakeholder_str = str(raw.get("stakeholder_type", "other"))
    try:
        stakeholder = StakeholderType(stakeholder_str)
    except ValueError:
        stakeholder = StakeholderType.OTHER

    relevance = 0.0
    raw_relevance = raw.get("relevance_score", 0.0)
    if isinstance(raw_relevance, (int, float)):
        relevance = max(0.0, min(1.0, float(raw_relevance)))

    annotation = PerspectiveAnnotation(
        political_lean=political_lean,
        policy_frames=tuple(frames),
        stakeholder_type=stakeholder,
        stance_summary=str(raw.get("stance_summary", "")),
        topic=str(raw.get("topic", "")),
        geographic_focus=str(raw.get("geographic_focus", "")),
    )
    return annotation, relevance


class ClaudeAnnotator:
    """Annotate sources with perspective metadata using Claude.

    Sends a batch of sources to Claude and parses structured JSON annotations.
    Supports batching to stay within context limits.

    Args:
        model: Anthropic model to use.
        api_key: API key (defaults to CLAUDE_API_KEY env var).
        batch_size: Max sources per API call.
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        api_key: str | None = None,
        batch_size: int = 20,
    ) -> None:
        resolved_key = api_key or os.environ.get("CLAUDE_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=resolved_key)
        self._model = model
        self._batch_size = batch_size

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
        if not sources:
            return ([], Usage())

        # Split into batches
        batches: list[list[Source]] = []
        for i in range(0, len(sources), self._batch_size):
            batches.append(sources[i : i + self._batch_size])

        # Process batches concurrently
        tasks = [self._annotate_batch(batch, event_description) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_annotated: list[AnnotatedSource] = []
        total_usage = Usage()

        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.warning("Annotation batch %d failed: %s", i, result)
                # Fall back to default annotations for this batch
                for source in batches[i]:
                    all_annotated.append(
                        AnnotatedSource(
                            source=source,
                            annotation=PerspectiveAnnotation(),
                            relevance_score=0.0,
                        )
                    )
                continue
            annotated, usage = result
            all_annotated.extend(annotated)
            total_usage += usage

        return (all_annotated, total_usage)

    async def _annotate_batch(
        self,
        sources: list[Source],
        event_description: str,
    ) -> tuple[list[AnnotatedSource], Usage]:
        """Annotate a single batch of sources."""
        source_texts = [_source_to_prompt_text(s, i) for i, s in enumerate(sources)]
        user_prompt = (
            f"News event: {event_description}\n\n"
            f"Annotate these {len(sources)} sources:\n\n" + "\n\n".join(source_texts)
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract usage
        web_searches = 0
        server_tool_use = getattr(response.usage, "server_tool_use", None)
        if server_tool_use is not None:
            web_searches = getattr(server_tool_use, "web_search_requests", 0) or 0

        usage = Usage(
            api_calls=[
                APICallUsage(
                    model=self._model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    cache_creation_input_tokens=getattr(
                        response.usage, "cache_creation_input_tokens", 0
                    )
                    or 0,
                    cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0)
                    or 0,
                    web_searches=web_searches,
                ),
            ],
        )

        # Parse the JSON response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        annotations = self._parse_response(response_text, len(sources))

        # Pair sources with annotations
        annotated: list[AnnotatedSource] = []
        for source, (annotation, relevance) in zip(sources, annotations, strict=True):
            annotated.append(
                AnnotatedSource(
                    source=source,
                    annotation=annotation,
                    relevance_score=relevance,
                )
            )

        return (annotated, usage)

    def _parse_response(
        self, text: str, expected_count: int
    ) -> list[tuple[PerspectiveAnnotation, float]]:
        """Parse the JSON array from Claude's response.

        Falls back to default annotations if parsing fails.
        """
        # Strip markdown fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last fence lines
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse annotation JSON, using defaults")
            return [(PerspectiveAnnotation(), 0.0)] * expected_count

        if not isinstance(parsed, list):
            logger.warning("Annotation response is not a list, using defaults")
            return [(PerspectiveAnnotation(), 0.0)] * expected_count

        results: list[tuple[PerspectiveAnnotation, float]] = []
        for item in parsed:
            if isinstance(item, dict):
                results.append(_parse_annotation(item))
            else:
                results.append((PerspectiveAnnotation(), 0.0))

        # Pad or truncate to match expected count
        while len(results) < expected_count:
            results.append((PerspectiveAnnotation(), 0.0))

        return results[:expected_count]
