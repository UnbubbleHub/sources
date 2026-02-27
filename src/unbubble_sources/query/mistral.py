from __future__ import annotations

import json
import os
from typing import Any, Iterable

from mistralai import Mistral
from mistralai.models import SystemMessage, UserMessage  # typed messages

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


def _chunks_to_text(chunks: Iterable[Any]) -> str:
    parts: list[str] = []
    for c in chunks:
        text = getattr(c, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)


def _content_to_text(content: Any) -> str:
    # Mistral chat message content can be a string or a list of chunks. [web:116]
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return _chunks_to_text(content)
    return ""


def _strip_markdown_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # Drop the opening fence line (``` or ```json)
        parts = s.split("\n", 1)
        if len(parts) == 2:
            s = parts[1]
        # Drop the closing fence
        s = s.rsplit("```", 1)[0]
    return s.strip()


class MistralQueryGenerator:
    """Generate search queries using Mistral chat completions. [web:116]"""

    def __init__(
        self,
        *,
        model: str = "mistral-small-latest",
        api_key: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not self._api_key:
            raise ValueError("Missing MISTRAL_API_KEY (set env var or pass api_key=...).")
        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    async def generate(
        self, event: NewsEvent, *, num_queries: int = 10
    ) -> tuple[list[SearchQuery], Usage]:
        user_content = f"News event: {event.description}"
        if event.date:
            user_content += f"\nDate: {event.date}"
        if event.context:
            user_content += f"\nAdditional context: {event.context}"

        messages = [
            SystemMessage(content=self._system_prompt.format(num_queries=num_queries)),
            UserMessage(content=user_content),
        ]

        async with Mistral(api_key=self._api_key) as client:
            res = await client.chat.complete_async(
                model=self._model,
                messages=messages,
                stream=False,
            )
            if res is None:
                raise RuntimeError("Mistral returned no response")

        raw = _strip_markdown_fences(_content_to_text(res.choices[0].message.content))
        items = json.loads(raw)

        queries = [SearchQuery(text=i["text"], intent=i["intent"]) for i in items]

        # Usage can be missing depending on settings; default to 0. [web:308]
        prompt_tokens = int(getattr(res.usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(res.usage, "completion_tokens", 0) or 0)

        usage = Usage(
            api_calls=[
                APICallUsage(
                    model=self._model,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    cache_creation_input_tokens=0,
                    cache_read_input_tokens=0,
                )
            ]
        )

        return queries, usage
