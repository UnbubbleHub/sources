#!/usr/bin/env python
"""CLI for Unbubble news diversity pipeline."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from pydantic import BaseModel, field_validator

from unbubble_sources.config import create_from_config, get_default_config_path, load_config
from unbubble_sources.data import NewsEvent

logger = logging.getLogger(__name__)


class CLIArgs(BaseModel):
    """Validated CLI arguments."""

    query: str
    config: Path

    @field_validator("config")
    @classmethod
    def config_must_exist(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Config file not found: {v}")
        return v


async def run(args: CLIArgs) -> None:
    """Execute the pipeline with the given configuration.

    Args:
        args: Validated CLI arguments.
    """
    config = load_config(args.config)
    pipeline = create_from_config(config)
    event = NewsEvent(description=args.query)

    logger.info(f"Running pipeline for: {args.query}")
    logger.info(f"Config: {args.config}")

    articles = await pipeline.run(event)

    print(f"Found {len(articles)} unique articles:\n")
    for i, article in enumerate(articles, 1):
        logger.info(f"{i}. {article.title}")
        logger.info(f"Source: {article.source}")
        logger.info(f"URL: {article.url}")
        if article.published_at:
            logger.info(f"Published: {article.published_at}")


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

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    ns = parser.parse_args()
    config_path: Path = ns.config if ns.config else get_default_config_path()

    try:
        args = CLIArgs(query=ns.query, config=config_path)
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
