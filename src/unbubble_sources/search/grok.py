"""X/Twitter search using the xAI Grok API (x_search tool).

Uses the xAI Responses API with the ``x_search`` server-side tool, which
searches X posts without requiring a Twitter API bearer token.  Only an
``XAI_API_KEY`` is needed.

Reference:
    https://docs.x.ai/docs/guides/live-search
"""

import asyncio
import json
import logging
import os

import httpx

from unbubble_sources.data import APICallUsage, SearchQuery, Source, Tweet, Usage
from unbubble_sources.url import extract_domain

GROK_RESPONSES_URL = "https://api.x.ai/v1/responses"
DEFAULT_MODEL = "grok-4-1-fast"

logger = logging.getLogger(__name__)


class GrokSearcher:
    """Search for X posts using the xAI Grok API x_search tool.

    Uses the ``x_search`` server-side tool available through the xAI Responses
    API.  This allows searching X posts without a Twitter API bearer token —
    only an xAI API key is required.

    The model is prompted to return structured JSON so that tweet metadata
    (URL, author, text, engagement counts) can be extracted programmatically.

    Args:
        api_key: xAI API key (defaults to ``XAI_API_KEY`` env var).
        model: Grok model to use (default: ``grok-4-1-fast``).
        max_results_per_query: Target number of tweets to return per query.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_results_per_query: int = 10,
    ) -> None:
        self._api_key = api_key or os.environ.get("XAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "xAI API key required. "
                "Pass api_key or set XAI_API_KEY env var."
            )
        self._model = model
        self._max_results = max_results_per_query

    async def search(
        self,
        queries: list[SearchQuery],
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        max_results_per_query: int = 10,
    ) -> tuple[list[Source], Usage]:
        """Search X posts matching the given queries.

        Args:
            queries: List of search queries to execute.
            from_date: Start date filter (ISO format, e.g. ``"2026-01-01"``).
            to_date: End date filter (ISO format).
            max_results_per_query: Maximum tweets to return per query.

        Returns:
            Tuple of (deduplicated tweets, usage).
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            tasks = [
                self._search_single(
                    client,
                    query,
                    from_date=from_date,
                    to_date=to_date,
                    max_results=max_results_per_query,
                )
                for query in queries
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: set[str] = set()
        sources: list[Source] = []
        total_usage = Usage()

        for result in results:
            if isinstance(result, BaseException):
                logger.warning(f"Error in GrokSearcher query: {result}")
                continue
            tweets, usage = result
            total_usage += usage
            for tweet in tweets:
                if tweet.url not in seen_urls:
                    seen_urls.add(tweet.url)
                    sources.append(tweet)

        return (sources, total_usage)

    async def _search_single(
        self,
        client: httpx.AsyncClient,
        query: SearchQuery,
        *,
        from_date: str | None,
        to_date: str | None,
        max_results: int,
    ) -> tuple[list[Tweet], Usage]:
        """Execute a single x_search query via the Grok Responses API."""
        date_context = ""
        if from_date and to_date:
            date_context = f" posted between {from_date} and {to_date}"
        elif from_date:
            date_context = f" posted from {from_date} onwards"
        elif to_date:
            date_context = f" posted up to {to_date}"

        prompt = (
            f"Search X for posts about: {query.text}{date_context}\n\n"
            f"Find up to {max_results} relevant, diverse posts. "
            "Return ONLY a JSON array (no other text) where each element has:\n"
            '- "url": full X post URL (https://x.com/<handle>/status/<id>)\n'
            '- "author_handle": username without @\n'
            '- "author_name": display name\n'
            '- "text": full post text\n'
            '- "published_at": ISO timestamp if available, else null\n'
            '- "like_count": integer\n'
            '- "retweet_count": integer\n'
            '- "reply_count": integer\n'
        )

        payload = {
            "model": self._model,
            "input": [{"role": "user", "content": prompt}],
            "tools": [{"type": "x_search"}],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        response = await client.post(GROK_RESPONSES_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        usage = self._parse_usage(data)
        tweets = self._parse_tweets(data, query)
        return (tweets[:max_results], usage)

    def _parse_usage(self, data: dict[str, object]) -> Usage:
        """Extract token usage from a Responses API response."""
        usage_data = data.get("usage", {})
        if not isinstance(usage_data, dict):
            return Usage()
        input_tokens = int(usage_data.get("input_tokens", 0) or 0)
        output_tokens = int(usage_data.get("output_tokens", 0) or 0)
        return Usage(
            api_calls=[
                APICallUsage(
                    model=self._model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            ]
        )

    def _parse_tweets(self, data: dict[str, object], query: SearchQuery) -> list[Tweet]:
        """Extract tweets from a Responses API response.

        Tries two strategies in order:
        1. Parse the model's text output as JSON (preferred — we asked for JSON).
        2. Fall back to scanning output items for any tool result content.
        """
        # Strategy 1: find text output blocks and parse as JSON
        output_items = data.get("output", [])
        if isinstance(output_items, list):
            for item in output_items:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "message":
                    for content_block in item.get("content", []):
                        if not isinstance(content_block, dict):
                            continue
                        if content_block.get("type") == "output_text":
                            text = content_block.get("text", "")
                            if isinstance(text, str):
                                tweets = self._try_parse_json_tweets(text, query)
                                if tweets:
                                    return tweets

        # Strategy 2: tool result blocks may contain raw post data
        if isinstance(output_items, list):
            for item in output_items:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "tool_result":
                    content = item.get("content", "")
                    if isinstance(content, str):
                        tweets = self._try_parse_json_tweets(content, query)
                        if tweets:
                            return tweets

        logger.warning("GrokSearcher: could not parse structured tweet data from response")
        return []

    def _try_parse_json_tweets(self, text: str, query: SearchQuery) -> list[Tweet]:
        """Attempt to parse a JSON array of tweet objects from a text string."""
        # Strip markdown code fences if present
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            items = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            return []

        if not isinstance(items, list):
            return []

        tweets: list[Tweet] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            author_handle = str(item.get("author_handle", "")).strip()
            tweets.append(
                Tweet(
                    url=url,
                    source=extract_domain(url) or "x.com",
                    published_at=item.get("published_at") or None,  # type: ignore[arg-type]
                    query=query,
                    tweet_id=_extract_tweet_id(url),
                    author_handle=author_handle,
                    author_name=str(item.get("author_name", "")).strip(),
                    text=str(item.get("text", "")).strip(),
                    retweet_count=int(item.get("retweet_count", 0) or 0),
                    like_count=int(item.get("like_count", 0) or 0),
                    reply_count=int(item.get("reply_count", 0) or 0),
                )
            )
        return tweets


def _extract_tweet_id(url: str) -> str:
    """Extract the tweet/status ID from an X post URL.

    E.g. ``https://x.com/user/status/123456`` → ``"123456"``.
    Returns empty string if extraction fails.
    """
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2 and parts[-2] == "status":
        return parts[-1]
    return ""
