#!/usr/bin/env python
"""CLI for Unbubble news diversity pipeline."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from unbubble.config import create_from_config, get_default_config_path, load_config
from unbubble.query.models import NewsEvent


async def run(query: str, config_path: Path) -> None:
    """Execute the pipeline with the given configuration.

    Args:
        query: Event description or query string.
        config_path: Path to YAML configuration file.
    """
    # Load configuration
    config = load_config(config_path)

    # Create pipeline from config
    pipeline = create_from_config(config)

    # Create event from query
    event = NewsEvent(description=query)

    print(f"Running pipeline for: {query}")
    print(f"Config: {config_path}")
    print()

    # Execute pipeline
    articles = await pipeline.run(event)

    # Print results
    print(f"Found {len(articles)} unique articles:\n")
    for i, article in enumerate(articles, 1):
        print(f"  {i}. {article.title}")
        print(f"     Source: {article.source}")
        print(f"     URL: {article.url}")
        if article.published_at:
            print(f"     Published: {article.published_at}")
        print()


def main() -> None:
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Find diverse news coverage of events.")
    parser.add_argument(
        "query",
        help="Event description or search query",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        help="Path to YAML config file (default: configs/default.yaml)",
    )

    args = parser.parse_args()

    # Resolve config path
    config_path: Path = args.config if args.config else get_default_config_path()

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(run(args.query, config_path))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
