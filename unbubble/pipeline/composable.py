"""Composable pipeline implementation."""

from __future__ import annotations

import asyncio
import logging

from unbubble.aggregator.base import QueryAggregator
from unbubble.data import Article, NewsEvent, SearchQuery
from unbubble.query.base import QueryGenerator
from unbubble.search.base import ArticleSearcher

logger = logging.getLogger(__name__)

class ComposablePipeline:
    """Pipeline composed of multiple generators, an aggregator, and multiple searchers.

    Flow:
    1. All generators produce queries in parallel
    2. Aggregator reduces/diversifies the combined query set
    3. All searchers execute the aggregated queries in parallel
    4. Results are deduplicated by URL

    Args:
        generators: List of query generators.
        aggregator: Query aggregator for deduplication/diversification.
        searchers: List of article searchers.
        num_queries_per_generator: Queries to request from each generator.
        max_results_per_searcher: Max results per query for each searcher.
    """

    def __init__(
        self,
        generators: list[QueryGenerator],
        aggregator: QueryAggregator,
        searchers: list[ArticleSearcher],
        num_queries_per_generator: int = 5,
        max_results_per_searcher: int = 10,
    ) -> None:
        self._generators = generators
        self._aggregator = aggregator
        self._searchers = searchers
        self._num_queries = num_queries_per_generator
        self._max_results = max_results_per_searcher

    async def run(
        self,
        event: NewsEvent,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[Article]:
        """Execute the composable pipeline.

        Args:
            event: The news event to investigate.
            from_date: Optional start date filter.
            to_date: Optional end date filter.

        Returns:
            List of diverse, deduplicated articles.
        """
        # Step 1: Generate queries from all generators in parallel
        generation_tasks = [
            gen.generate(event, num_queries=self._num_queries) for gen in self._generators
        ]
        generation_results = await asyncio.gather(*generation_tasks, return_exceptions=True)

        # Collect all successful queries
        all_queries: list[SearchQuery] = []
        for result in generation_results:
            if isinstance(result, BaseException):
                logger.warning(f"Error in query generation: {str(result)}")
                continue
            all_queries.extend(result)

        if not all_queries:
            return []

        # Step 2: Aggregate queries
        aggregated_queries = await self._aggregator.aggregate(all_queries)

        # Step 3: Search with all searchers in parallel
        search_tasks = [
            searcher.search(
                aggregated_queries,
                from_date=from_date,
                to_date=to_date,
                max_results_per_query=self._max_results,
            )
            for searcher in self._searchers
        ]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Step 4: Deduplicate by URL
        seen_urls: set[str] = set()
        articles: list[Article] = []

        for search_result in search_results:
            if isinstance(search_result, BaseException):
                logger.warning(f"Error during search: {str(search_result)}")
                continue
            # search_result is list[Article] at this point
            article_list: list[Article] = search_result
            for article in article_list:
                if article.url not in seen_urls:
                    seen_urls.add(article.url)
                    articles.append(article)

        return articles
