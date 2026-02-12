"""Dynamic pricing for Anthropic models.

Fetches model pricing from the Anthropic docs page and provides cost
estimation utilities. Falls back to hardcoded prices when offline.
"""

import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

PRICING_URL = "https://docs.anthropic.com/en/docs/about-claude/pricing"
WEB_SEARCH_PRICE_PER_SEARCH = 10.0 / 1000  # $10 per 1,000 searches
GNEWS_REQUEST_PRICE = 0.0  # free tier


@dataclass(frozen=True)
class ModelPricing:
    """Per-model pricing in USD per million tokens."""

    input_per_mtok: float
    output_per_mtok: float
    cache_write_per_mtok: float
    cache_read_per_mtok: float


# Hardcoded fallback (used when fetch fails / offline)
_FALLBACK_PRICES: dict[str, ModelPricing] = {
    "claude-haiku-4-5": ModelPricing(1.0, 5.0, 1.25, 0.10),
    "claude-haiku-3-5": ModelPricing(0.80, 4.0, 1.0, 0.08),
    "claude-haiku-3": ModelPricing(0.25, 1.25, 0.30, 0.03),
    "claude-sonnet-4-5": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "claude-sonnet-4": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "claude-opus-4-6": ModelPricing(5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-5": ModelPricing(5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-1": ModelPricing(15.0, 75.0, 18.75, 1.50),
    "claude-opus-4": ModelPricing(15.0, 75.0, 18.75, 1.50),
}


def _display_name_to_model_prefix(name: str) -> str:
    """Convert a display name like 'Claude Haiku 4.5' to 'claude-haiku-4-5'."""
    # Remove markdown links like ([deprecated](...)) — use greedy match for nested parens
    name = re.sub(r"\s*\(.*\)", "", name).strip()
    # "Claude Opus 4.6" -> "claude-opus-4-6"
    parts = name.lower().split()
    # Replace dots in version numbers with dashes: "4.5" -> "4-5"
    parts = [p.replace(".", "-") for p in parts]
    return "-".join(parts)


def _parse_price(cell: str) -> float:
    """Parse a price cell like '$1.25 / MTok' into a float."""
    match = re.search(r"\$([0-9]+(?:\.[0-9]+)?)", cell)
    if match:
        return float(match.group(1))
    return 0.0


def _parse_pricing_table(markdown: str) -> dict[str, ModelPricing]:
    """Parse the model pricing markdown table into a dict.

    Expected table columns:
    | Model | Base Input Tokens | 5m Cache Writes | 1h Cache Writes | Cache Hits | Output Tokens |
    """
    prices: dict[str, ModelPricing] = {}

    # Find the model pricing section
    section_match = re.search(
        r"## Model pricing\s*\n(.*?)(?=\n## |\Z)",
        markdown,
        re.DOTALL,
    )
    if not section_match:
        return prices

    section = section_match.group(1)

    # Find table rows (lines starting with |)
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|--") or line.startswith("| Model"):
            continue
        # Skip separator rows
        if re.match(r"\|[-\s|]+\|", line):
            continue

        cells = [c.strip() for c in line.split("|")]
        # Filter empty strings from split
        cells = [c for c in cells if c]

        if len(cells) < 6:
            continue

        model_name = cells[0].strip()
        prefix = _display_name_to_model_prefix(model_name)

        input_price = _parse_price(cells[1])
        cache_write_price = _parse_price(cells[2])  # 5m cache writes
        # cells[3] is 1h cache writes — we skip it
        cache_read_price = _parse_price(cells[4])
        output_price = _parse_price(cells[5])

        if input_price > 0 or output_price > 0:
            prices[prefix] = ModelPricing(
                input_per_mtok=input_price,
                output_per_mtok=output_price,
                cache_write_per_mtok=cache_write_price,
                cache_read_per_mtok=cache_read_price,
            )

    return prices


async def fetch_model_prices() -> dict[str, ModelPricing]:
    """Fetch pricing from Anthropic docs page, parsing the markdown table.

    Falls back to ``_FALLBACK_PRICES`` on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(PRICING_URL)
            response.raise_for_status()
            parsed = _parse_pricing_table(response.text)
            if parsed:
                logger.info("Fetched live pricing for %d models", len(parsed))
                return parsed
            logger.warning("Could not parse pricing table, using fallback prices")
    except Exception:
        logger.warning("Failed to fetch pricing, using fallback prices", exc_info=True)

    return dict(_FALLBACK_PRICES)


def get_model_pricing(
    model_id: str,
    prices: dict[str, ModelPricing],
) -> ModelPricing:
    """Look up pricing by model ID using prefix matching.

    E.g. ``'claude-haiku-4-5-20251001'`` matches ``'claude-haiku-4-5'``.
    Falls back to cheapest known model (Haiku 4.5) if no match found.
    """
    # Try exact match first
    if model_id in prices:
        return prices[model_id]

    # Try prefix matching: find the longest prefix key that matches
    best_match: str | None = None
    for key in prices:
        if model_id.startswith(key) and (best_match is None or len(key) > len(best_match)):
            best_match = key

    if best_match is not None:
        return prices[best_match]

    # Fallback to Haiku 4.5 pricing
    logger.warning("No pricing found for model '%s', using Haiku 4.5 fallback", model_id)
    return _FALLBACK_PRICES.get(
        "claude-haiku-4-5",
        ModelPricing(1.0, 5.0, 1.25, 0.10),
    )


def estimate_api_call_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int,
    cache_read_input_tokens: int,
    web_searches: int,
    prices: dict[str, ModelPricing],
) -> float:
    """Estimate cost in USD for a single API call."""
    pricing = get_model_pricing(model, prices)
    cost = 0.0
    cost += (input_tokens / 1_000_000) * pricing.input_per_mtok
    cost += (output_tokens / 1_000_000) * pricing.output_per_mtok
    cost += (cache_creation_input_tokens / 1_000_000) * pricing.cache_write_per_mtok
    cost += (cache_read_input_tokens / 1_000_000) * pricing.cache_read_per_mtok
    cost += web_searches * WEB_SEARCH_PRICE_PER_SEARCH
    return cost


def estimate_usage_cost(
    api_calls: list[object],
    gnews_requests: int,
    prices: dict[str, ModelPricing],
) -> float:
    """Estimate total cost in USD for accumulated usage.

    Args:
        api_calls: List of APICallUsage objects.
        gnews_requests: Number of GNews API requests.
        prices: Model pricing dict from fetch_model_prices().
    """
    from unbubble_sources.data.models import APICallUsage

    total = 0.0
    for call in api_calls:
        if not isinstance(call, APICallUsage):
            continue
        total += estimate_api_call_cost(
            model=call.model,
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            cache_creation_input_tokens=call.cache_creation_input_tokens,
            cache_read_input_tokens=call.cache_read_input_tokens,
            web_searches=call.web_searches,
            prices=prices,
        )
    total += gnews_requests * GNEWS_REQUEST_PRICE
    return total
