"""Tests for the pricing module."""

import pytest

from unbubble_sources.data import APICallUsage, Usage
from unbubble_sources.pricing import (
    ModelPricing,
    PriceCache,
    _display_name_to_model_prefix,
    _parse_price,
    _parse_pricing_table,
    estimate_api_call_cost,
    estimate_usage_cost,
    get_model_pricing,
)

# -- Unit tests for helpers --


def test_display_name_to_model_prefix_basic() -> None:
    assert _display_name_to_model_prefix("Claude Haiku 4.5") == "claude-haiku-4-5"


def test_display_name_to_model_prefix_with_dots() -> None:
    assert _display_name_to_model_prefix("Claude Opus 4.6") == "claude-opus-4-6"


def test_display_name_to_model_prefix_strips_deprecated() -> None:
    name = "Claude Sonnet 3.7 ([deprecated](/docs/en/about-claude/model-deprecations))"
    assert _display_name_to_model_prefix(name) == "claude-sonnet-3-7"


def test_parse_price_valid() -> None:
    assert _parse_price("$1 / MTok") == 1.0
    assert _parse_price("$3.75 / MTok") == 3.75
    assert _parse_price("$15 / MTok") == 15.0
    assert _parse_price("$0.10 / MTok") == 0.10


def test_parse_price_invalid() -> None:
    assert _parse_price("N/A") == 0.0
    assert _parse_price("") == 0.0


# -- Tests for table parsing --


SAMPLE_TABLE = """\
## Model pricing

Some introductory text.

| Model | Base Input Tokens | 5m Cache Writes | 1h Cache Writes | Cache Hits & Refreshes | Output Tokens |
|-------|-------------------|-----------------|-----------------|----------------------|---------------|
| Claude Haiku 4.5 | $1 / MTok | $1.25 / MTok | $2 / MTok | $0.10 / MTok | $5 / MTok |
| Claude Sonnet 4.5 | $3 / MTok | $3.75 / MTok | $6 / MTok | $0.30 / MTok | $15 / MTok |
| Claude Opus 4.6 | $5 / MTok | $6.25 / MTok | $10 / MTok | $0.50 / MTok | $25 / MTok |

## Third-party platform pricing

Other content here.
"""


def test_parse_pricing_table() -> None:
    prices = _parse_pricing_table(SAMPLE_TABLE)

    assert "claude-haiku-4-5" in prices
    assert "claude-sonnet-4-5" in prices
    assert "claude-opus-4-6" in prices

    haiku = prices["claude-haiku-4-5"]
    assert haiku.input_per_mtok == 1.0
    assert haiku.output_per_mtok == 5.0
    assert haiku.cache_write_per_mtok == 1.25
    assert haiku.cache_read_per_mtok == 0.10

    opus = prices["claude-opus-4-6"]
    assert opus.input_per_mtok == 5.0
    assert opus.output_per_mtok == 25.0


def test_parse_pricing_table_empty() -> None:
    prices = _parse_pricing_table("No pricing table here")
    assert prices == {}


# -- Tests for model pricing lookup --


@pytest.fixture
def sample_prices() -> dict[str, ModelPricing]:
    return {
        "claude-haiku-4-5": ModelPricing(1.0, 5.0, 1.25, 0.10),
        "claude-sonnet-4-5": ModelPricing(3.0, 15.0, 3.75, 0.30),
        "claude-opus-4-6": ModelPricing(5.0, 25.0, 6.25, 0.50),
    }


def test_get_model_pricing_exact(sample_prices: dict[str, ModelPricing]) -> None:
    pricing = get_model_pricing("claude-haiku-4-5", sample_prices)
    assert pricing.input_per_mtok == 1.0


def test_get_model_pricing_prefix(sample_prices: dict[str, ModelPricing]) -> None:
    pricing = get_model_pricing("claude-haiku-4-5-20251001", sample_prices)
    assert pricing.input_per_mtok == 1.0


def test_get_model_pricing_fallback(sample_prices: dict[str, ModelPricing]) -> None:
    pricing = get_model_pricing("unknown-model", sample_prices)
    # Should fall back to Haiku 4.5
    assert pricing.input_per_mtok == 1.0


# -- Tests for cost estimation --


def test_estimate_api_call_cost_tokens_only(
    sample_prices: dict[str, ModelPricing],
) -> None:
    cost = estimate_api_call_cost(
        model="claude-haiku-4-5-20251001",
        input_tokens=1_000_000,  # 1M tokens
        output_tokens=500_000,  # 0.5M tokens
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        web_searches=0,
        prices=sample_prices,
    )
    # 1M * $1/MTok + 0.5M * $5/MTok = $1 + $2.50 = $3.50
    assert abs(cost - 3.50) < 0.001


def test_estimate_api_call_cost_with_web_search(
    sample_prices: dict[str, ModelPricing],
) -> None:
    cost = estimate_api_call_cost(
        model="claude-haiku-4-5-20251001",
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        web_searches=1,
        prices=sample_prices,
    )
    # Token cost is tiny; web search = $0.01
    assert cost > 0.009  # At least the web search cost


def test_estimate_api_call_cost_with_cache(
    sample_prices: dict[str, ModelPricing],
) -> None:
    cost = estimate_api_call_cost(
        model="claude-haiku-4-5-20251001",
        input_tokens=0,
        output_tokens=0,
        cache_creation_input_tokens=1_000_000,
        cache_read_input_tokens=1_000_000,
        web_searches=0,
        prices=sample_prices,
    )
    # 1M * $1.25/MTok + 1M * $0.10/MTok = $1.35
    assert abs(cost - 1.35) < 0.001


def test_estimate_usage_cost_mixed(
    sample_prices: dict[str, ModelPricing],
) -> None:
    api_calls = [
        APICallUsage(
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,
            output_tokens=0,
        ),
        APICallUsage(
            model="claude-sonnet-4-5-20250514",
            input_tokens=1_000_000,
            output_tokens=0,
        ),
    ]
    cost = estimate_usage_cost(api_calls, gnews_requests=0, prices=sample_prices)
    # Haiku: 1M * $1 = $1, Sonnet: 1M * $3 = $3, total = $4
    assert abs(cost - 4.0) < 0.001


def test_estimate_usage_cost_with_gnews(
    sample_prices: dict[str, ModelPricing],
) -> None:
    # GNews is free tier ($0), so cost should just be API call cost
    api_calls = [
        APICallUsage(model="claude-haiku-4-5", input_tokens=1_000_000, output_tokens=0),
    ]
    cost = estimate_usage_cost(api_calls, gnews_requests=10, prices=sample_prices)
    assert abs(cost - 1.0) < 0.001


# -- PriceCache tests --


def test_price_cache_get_sync_raises_without_fetch() -> None:
    cache = PriceCache()
    with pytest.raises(RuntimeError, match="not yet fetched"):
        cache.get_sync()


async def test_price_cache_get_fetches_and_caches() -> None:
    cache = PriceCache()
    prices = await cache.get()
    assert isinstance(prices, dict)
    assert len(prices) > 0
    # Second call returns same object (cached)
    prices2 = await cache.get()
    assert prices is prices2


async def test_price_cache_get_sync_after_fetch() -> None:
    cache = PriceCache()
    await cache.get()
    prices = cache.get_sync()
    assert isinstance(prices, dict)


def test_price_cache_stamp_usage(
    sample_prices: dict[str, ModelPricing],
) -> None:
    cache = PriceCache()
    cache._prices = sample_prices  # pre-populate to avoid network call

    usage = Usage(
        api_calls=[
            APICallUsage(
                model="claude-haiku-4-5-20251001",
                input_tokens=1_000_000,
                output_tokens=0,
            ),
        ],
    )
    assert usage.estimated_cost == 0.0

    cache.stamp_usage(usage)

    # 1M input tokens at $1/MTok = $1.00
    assert usage.estimated_cost == pytest.approx(1.0)


def test_price_cache_stamp_usage_ignores_non_usage() -> None:
    cache = PriceCache()
    cache._prices = {}
    # Should not raise on non-Usage objects
    cache.stamp_usage("not a usage object")
