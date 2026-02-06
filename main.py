#!/usr/bin/env python
"""CLI for testing query generation and news search."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from unbubble import ClaudeQueryGenerator, GNewsSearcher, NewsEvent


async def run(
    description: str,
    date: str | None,
    context: str | None,
    num_queries: int,
    model: str,
    max_results: int,
    skip_search: bool,
) -> None:
    event = NewsEvent(description=description, date=date, context=context)
    generator = ClaudeQueryGenerator(model=model)

    print(f"Generating {num_queries} queries for: {event.description}")
    if event.date:
        print(f"Date: {event.date}")
    if event.context:
        print(f"Context: {event.context}")
    print()

    queries = await generator.generate(event, num_queries=num_queries)

    print("Generated queries:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q.text}")
        print(f"     -> {q.intent}\n")

    if skip_search:
        print("Skipping search (--skip-search flag set or GNEWS_API_KEY not set)")
        return

    # Search for articles
    print("-" * 60)
    print(f"Searching for articles (max {max_results} per query)...\n")

    searcher = GNewsSearcher()
    articles = await searcher.search(
        queries,
        from_date=event.date,
        max_results_per_query=max_results,
    )

    print(f"Found {len(articles)} unique articles:\n")
    for i, article in enumerate(articles, 1):
        print(f"  {i}. {article.title}")
        print(f"     Source: {article.source}")
        print(f"     URL: {article.url}")
        if article.published_at:
            print(f"     Published: {article.published_at}")
        if article.query:
            print(f"     Found via: {article.query.text[:50]}...")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate diverse search queries and search for news articles."
    )
    parser.add_argument(
        "description",
        nargs="?",
        default="US-Cuba diplomatic tensions over migration policy",
        help="Description of the news event (default: sample event)",
    )
    parser.add_argument(
        "-d",
        "--date",
        help="Date of the event (e.g., 2026-02-01). Also used as search from_date.",
    )
    parser.add_argument(
        "-c",
        "--context",
        help="Additional context for the event",
    )
    parser.add_argument(
        "-n",
        "--num-queries",
        type=int,
        default=5,
        help="Number of queries to generate (default: 5)",
    )
    parser.add_argument(
        "-m",
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Anthropic model to use (default: claude-haiku-4-5-20251001)",
    )
    parser.add_argument(
        "-r",
        "--max-results",
        type=int,
        default=5,
        help="Max results per query (default: 5)",
    )
    parser.add_argument(
        "--skip-search",
        action="store_true",
        default=not os.environ.get("GNEWS_API_KEY"),
        help="Skip the search step (default: true if GNEWS_API_KEY not set)",
    )

    args = parser.parse_args()

    try:
        asyncio.run(
            run(
                description=args.description,
                date=args.date,
                context=args.context,
                num_queries=args.num_queries,
                model=args.model,
                max_results=args.max_results,
                skip_search=args.skip_search,
            )
        )
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
