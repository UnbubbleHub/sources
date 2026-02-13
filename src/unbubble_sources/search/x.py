"""X/Twitter search using the official API v2."""

import asyncio
import logging
import os

import httpx

from unbubble_sources.data import SearchQuery, Source, Tweet, Usage

X_API_URL = "https://api.twitter.com/2/tweets/search/recent"

logger = logging.getLogger(__name__)


class XSearcher:
    """Search for tweets using the X/Twitter API v2.

    Uses the ``tweets/search/recent`` endpoint which returns tweets from the
    last 7 days.  Requires a bearer token with at least Basic access.

    Args:
        bearer_token: X API bearer token (defaults to TWITTER_BEARER_TOKEN env var).
        max_results_per_query: Default max results per query (10-100, default 10).
    """

    def __init__(
        self,
        *,
        bearer_token: str | None = None,
        max_results_per_query: int = 10,
    ) -> None:
        self._bearer_token = bearer_token or os.environ.get("TWITTER_BEARER_TOKEN")
        if not self._bearer_token:
            raise ValueError(
                "X API bearer token required. "
                "Pass bearer_token or set TWITTER_BEARER_TOKEN env var."
            )
        self._max_results = max_results_per_query

    async def search(
        self,
        queries: list[SearchQuery],
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        max_results_per_query: int = 10,
    ) -> tuple[list[Source], Usage]:
        """Search for tweets matching the given queries.

        Args:
            queries: List of search queries to execute.
            from_date: Start date filter (ISO format, e.g. "2026-01-01").
            to_date: End date filter (ISO format).
            max_results_per_query: Maximum tweets to return per query (10-100).

        Returns:
            Tuple of (deduplicated tweets, usage).
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
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
        successful_requests = 0

        for result in results:
            if isinstance(result, BaseException):
                logger.warning(f"Error processing X query. Error: {result}")
                continue
            successful_requests += 1
            for tweet in result:
                if tweet.url not in seen_urls:
                    seen_urls.add(tweet.url)
                    sources.append(tweet)

        usage = Usage(x_api_requests=successful_requests)
        return (sources, usage)

    async def _search_single(
        self,
        client: httpx.AsyncClient,
        query: SearchQuery,
        *,
        from_date: str | None,
        to_date: str | None,
        max_results: int,
    ) -> list[Tweet]:
        """Execute a single X API search query."""
        params: dict[str, str | int] = {
            "query": query.text,
            "max_results": min(max(max_results, 10), 100),
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        if from_date:
            params["start_time"] = _to_rfc3339(from_date)
        if to_date:
            params["end_time"] = _to_rfc3339(to_date)

        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        response = await client.get(X_API_URL, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Build author lookup from includes
        authors: dict[str, dict[str, str]] = {}
        for user in data.get("includes", {}).get("users", []):
            authors[user["id"]] = {
                "username": user.get("username", ""),
                "name": user.get("name", ""),
            }

        tweets: list[Tweet] = []
        for item in data.get("data", []):
            tweet_id = item["id"]
            author_id = item.get("author_id", "")
            author_info = authors.get(author_id, {})
            author_handle = author_info.get("username", "")
            metrics = item.get("public_metrics", {})

            tweets.append(
                Tweet(
                    url=f"https://x.com/{author_handle}/status/{tweet_id}",
                    source="x.com",
                    published_at=item.get("created_at"),
                    query=query,
                    tweet_id=tweet_id,
                    author_handle=author_handle,
                    author_name=author_info.get("name", ""),
                    text=item.get("text", ""),
                    retweet_count=metrics.get("retweet_count", 0),
                    like_count=metrics.get("like_count", 0),
                    reply_count=metrics.get("reply_count", 0),
                )
            )
        return tweets


def _to_rfc3339(date_str: str) -> str:
    """Convert ISO date (YYYY-MM-DD) to RFC 3339 for the X API.

    If the string already contains a ``T`` (i.e. is already RFC 3339-ish),
    it is returned unchanged.
    """
    if "T" in date_str:
        return date_str
    return f"{date_str}T00:00:00Z"
