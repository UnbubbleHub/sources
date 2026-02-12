import json
import os

import anthropic
from anthropic.types import TextBlock

from unbubble_sources.data import APICallUsage, NewsEvent, SearchQuery, Usage

DEFAULT_SYSTEM_PROMPT = """\
You are a research assistant that generates diverse search queries to find \
articles covering a news event from multiple perspectives.

Given a news event, produce exactly {num_queries} search queries. Each query \
should target a DIFFERENT angle, perspective, or stakeholder viewpoint so that \
the resulting articles span a wide range of opinions and framings.

Consider varying:
- Political/ideological leanings
- Geographic perspectives (local vs international)
- Stakeholder viewpoints (government, opposition, civil society, experts, affected populations)
- Framing (economic, humanitarian, security, legal, historical)
- Source types (official statements, opinion pieces, investigative reports, academic analysis)

Respond with a JSON array of objects, each with:
- "text": the search query string
- "intent": a brief description of what perspective or angle this query targets

Return ONLY the JSON array, no other text.\
"""


class ClaudeQueryGenerator:
    """Generate search queries using Anthropic's Claude API.

    Args:
        model: Anthropic model ID to use.
        api_key: API key (defaults to CLAUDE_API_KEY env var).
        system_prompt: Custom system prompt template. Must contain a
            ``{num_queries}`` placeholder. If *None*, the built-in
            default is used. The prompt must instruct the model to return
            a JSON array of objects with ``"text"`` and ``"intent"`` keys.
    """

    def __init__(
        self,
        *,
        model: str = "claude-haiku-4-5-20251001",
        api_key: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._model = model
        resolved_key = api_key or os.environ.get("CLAUDE_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=resolved_key)
        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    async def generate(
        self, event: NewsEvent, *, num_queries: int = 10
    ) -> tuple[list[SearchQuery], Usage]:
        user_content = f"News event: {event.description}"
        if event.date:
            user_content += f"\nDate: {event.date}"
        if event.context:
            user_content += f"\nAdditional context: {event.context}"

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=self._system_prompt.format(num_queries=num_queries),
            messages=[{"role": "user", "content": user_content}],
        )

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
                ),
            ],
        )

        content_block = response.content[0]
        if not isinstance(content_block, TextBlock):
            raise ValueError(f"Expected TextBlock, got {type(content_block).__name__}")
        raw: str = content_block.text
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        items = json.loads(raw)
        queries = [SearchQuery(text=item["text"], intent=item["intent"]) for item in items]
        return (queries, usage)
