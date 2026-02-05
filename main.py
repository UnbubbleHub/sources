#!/usr/bin/env python
"""CLI for testing the query generator."""

from __future__ import annotations

import argparse
import asyncio
import sys

from unbubble import ClaudeQueryGenerator, NewsEvent


async def run(
    description: str,
    date: str | None,
    context: str | None,
    num_queries: int,
    model: str,
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

    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q.text}")
        print(f"     -> {q.intent}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate diverse search queries for a news event."
    )
    parser.add_argument(
        "description",
        nargs="?",
        default="US-Cuba diplomatic tensions over migration policy",
        help="Description of the news event (default: sample event)",
    )
    parser.add_argument(
        "-d", "--date",
        help="Date of the event (e.g., 2026-02-01)",
    )
    parser.add_argument(
        "-c", "--context",
        help="Additional context for the event",
    )
    parser.add_argument(
        "-n", "--num-queries",
        type=int,
        default=8,
        help="Number of queries to generate (default: 8)",
    )
    parser.add_argument(
        "-m", "--model",
        default="claude-sonnet-4-20250514",
        help="Anthropic model to use (default: claude-sonnet-4-20250514)",
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
            )
        )
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
