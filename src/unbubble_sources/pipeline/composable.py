"""Composable pipeline implementation."""

import asyncio
import logging
import time

from unbubble_sources.aggregator.base import QueryAggregator
from unbubble_sources.data import NewsEvent, SearchQuery, Source, Usage
from unbubble_sources.pricing import PriceCache
from unbubble_sources.query.base import QueryGenerator
from unbubble_sources.run_logger import RunLogger
from unbubble_sources.search.base import SourceSearcher

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
        searchers: List of source searchers.
        num_queries_per_generator: Queries to request from each generator.
        max_results_per_searcher: Max results per query for each searcher.
        run_logger: Optional RunLogger for intermediate result logging.
        price_cache: Optional PriceCache for cost estimation.
    """

    def __init__(
        self,
        generators: list[QueryGenerator],
        aggregator: QueryAggregator,
        searchers: list[SourceSearcher],
        num_queries_per_generator: int = 5,
        max_results_per_searcher: int = 10,
        run_logger: RunLogger | None = None,
        price_cache: PriceCache | None = None,
    ) -> None:
        self._generators = generators
        self._aggregator = aggregator
        self._searchers = searchers
        self._num_queries = num_queries_per_generator
        self._max_results = max_results_per_searcher
        self._run_logger = run_logger
        self._price_cache = price_cache

    async def run(
        self,
        event: NewsEvent,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> tuple[list[Source], Usage]:
        """Execute the composable pipeline.

        Args:
            event: The news event to investigate.
            from_date: Optional start date filter.
            to_date: Optional end date filter.

        Returns:
            Tuple of (diverse deduplicated sources, usage).
        """
        if self._run_logger:
            self._run_logger.start_run("composable", event)

        # Ensure prices are fetched before pipeline starts
        if self._price_cache:
            await self._price_cache.get()

        total_usage = Usage()

        # Step 1: Generate queries from all generators in parallel
        t0 = time.monotonic()
        generation_tasks = [
            gen.generate(event, num_queries=self._num_queries) for gen in self._generators
        ]
        generation_results = await asyncio.gather(*generation_tasks, return_exceptions=True)
        gen_duration = time.monotonic() - t0

        # Collect all successful queries
        all_queries: list[SearchQuery] = []
        for i, result in enumerate(generation_results):
            if isinstance(result, BaseException):
                logger.warning(f"Error in query generation: {str(result)}")
                continue
            queries, gen_usage = result
            if self._price_cache:
                self._price_cache.stamp_usage(gen_usage)
            all_queries.extend(queries)
            total_usage += gen_usage

            if self._run_logger:
                component = type(self._generators[i]).__name__
                self._run_logger.log_stage(
                    stage="query_generation",
                    component=component,
                    input_data=event,
                    output_data=queries,
                    usage=gen_usage,
                    duration_seconds=gen_duration,
                )

        if not all_queries:
            if self._run_logger:
                self._run_logger.finish_run([], total_usage)
            return ([], total_usage)

        # Step 2: Aggregate queries
        t0 = time.monotonic()
        aggregated_queries = await self._aggregator.aggregate(all_queries)
        agg_duration = time.monotonic() - t0

        if self._run_logger:
            self._run_logger.log_stage(
                stage="aggregation",
                component=type(self._aggregator).__name__,
                input_data=all_queries,
                output_data=aggregated_queries,
                usage=None,
                duration_seconds=agg_duration,
            )

        # Step 3: Search with all searchers in parallel
        t0 = time.monotonic()
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
        search_duration = time.monotonic() - t0

        # Step 4: Deduplicate by URL
        seen_urls: set[str] = set()
        sources: list[Source] = []
        pre_dedup_count = 0

        for i, search_result in enumerate(search_results):
            if isinstance(search_result, BaseException):
                logger.warning(f"Error during search: {str(search_result)}")
                continue
            source_list, search_usage = search_result
            if self._price_cache:
                self._price_cache.stamp_usage(search_usage)
            total_usage += search_usage
            pre_dedup_count += len(source_list)

            if self._run_logger:
                component = type(self._searchers[i]).__name__
                self._run_logger.log_stage(
                    stage="search",
                    component=component,
                    input_data=aggregated_queries,
                    output_data=source_list,
                    usage=search_usage,
                    duration_seconds=search_duration,
                )

            for src in source_list:
                if src.url not in seen_urls:
                    seen_urls.add(src.url)
                    sources.append(src)

        if self._run_logger:
            t0_dedup = time.monotonic()
            dedup_duration = time.monotonic() - t0_dedup
            self._run_logger.log_stage(
                stage="deduplication",
                component="url_dedup",
                input_data={"source_count": pre_dedup_count},
                output_data={"source_count": len(sources)},
                usage=None,
                duration_seconds=dedup_duration,
            )
            self._run_logger.finish_run(sources, total_usage)

        return (sources, total_usage)
