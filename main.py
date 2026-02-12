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
    log: bool = False
    log_dir: str = "logs"

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
    pipeline, run_logger, _price_cache = create_from_config(
        config,
        log_override=args.log if args.log else None,
        log_dir_override=args.log_dir if args.log_dir != "logs" else None,
    )
    event = NewsEvent(description=args.query)

    logger.info(f"Running pipeline for: {args.query}")
    logger.info(f"Config: {args.config}")

    articles, usage = await pipeline.run(event)

    print(f"\nFound {len(articles)} unique articles:\n")
    for i, article in enumerate(articles, 1):
        logger.info(f"{i}. {article.title}")
        logger.info(f"   Source: {article.source}")
        logger.info(f"   URL: {article.url}")
        if article.published_at:
            logger.info(f"   Published: {article.published_at}")

    # Log usage summary (cost is already computed by the pipeline via PriceCache)
    logger.info("\n--- Usage Summary ---")
    logger.info(f"API calls: {len(usage.api_calls)}")
    logger.info(f"Input tokens: {usage.input_tokens:,}")
    logger.info(f"Output tokens: {usage.output_tokens:,}")
    if usage.cache_creation_input_tokens:
        logger.info(f"Cache write tokens: {usage.cache_creation_input_tokens:,}")
    if usage.cache_read_input_tokens:
        logger.info(f"Cache read tokens: {usage.cache_read_input_tokens:,}")
    if usage.web_searches:
        logger.info(f"Web searches: {usage.web_searches}")
    if usage.gnews_requests:
        logger.info(f"GNews requests: {usage.gnews_requests}")
    logger.info(f"Estimated cost: ${usage.estimated_cost:.4f}")

    # Log file path if logging was enabled (pipeline calls finish_run internally)
    if run_logger and run_logger.last_log_path:
        logger.info(f"\nRun log written to: {run_logger.last_log_path}")


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
        default=Path("configs/default.yaml"),
        help="Path to YAML config file (default: configs/default.yaml)",
    )
    parser.add_argument(
        "--log",
        action="store_true",
        default=False,
        help="Enable intermediate pipeline logging to JSON file",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Directory for log files (default: logs/)",
    )

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    ns = parser.parse_args()
    config_path: Path = ns.config if ns.config else get_default_config_path()

    try:
        args = CLIArgs(
            query=ns.query,
            config=config_path,
            log=ns.log,
            log_dir=ns.log_dir,
        )
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
