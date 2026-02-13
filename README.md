# Unbubble Sources

**Surface diverse, high-quality perspectives on any news event.**

Unbubble Sources takes a news event as input and returns sources (news articles, tweets, …) representing a range of viewpoints, helping users break out of information bubbles.

## Quick Start

```bash
# Install
git clone https://github.com/your-org/unbubble.git
cd unbubble/sources
uv sync

# Run
export CLAUDE_API_KEY=your-anthropic-key
uv run python main.py "Climate summit negotiations"

# Use a different pipeline config
uv run python main.py "Climate summit negotiations" -c configs/claude_e2e.yaml

# Enable intermediate logging (writes a JSON file per run)
uv run python main.py "Climate summit negotiations" --log
uv run python main.py "Climate summit negotiations" --log --log-dir my_logs/
```

### Programmatic usage

```python
import asyncio
from unbubble_sources import load_config, create_from_config, NewsEvent, Article, Tweet
from unbubble_sources.pricing import fetch_model_prices, estimate_usage_cost

async def main():
    config = load_config("configs/default.yaml")
    pipeline, run_logger = create_from_config(config)
    event = NewsEvent(description="Climate summit negotiations")
    sources, usage = await pipeline.run(event)

    for src in sources:
        if isinstance(src, Article):
            print(f"[article] {src.title} ({src.source})")
        elif isinstance(src, Tweet):
            print(f"[tweet] @{src.author_handle}: {src.text[:80]}")

    # Cost estimation
    prices = await fetch_model_prices()
    cost = estimate_usage_cost(
        usage.api_calls, usage.gnews_requests, prices,
        x_api_requests=usage.x_api_requests,
        exa_requests=usage.exa_requests,
    )
    print(f"Estimated cost: ${cost:.4f}")

asyncio.run(main())
```

## Configuration

Pipelines are configured via YAML. Two types are available:

**Composable** (`type: composable`) — chain generators, an aggregator, and searchers for full control:

```yaml
pipeline:
  type: composable
  generators:
    - type: claude       # uses Claude API to expand queries
    # - type: noop       # pass-through (no API call, free)
  aggregator:
    type: pca
    n_components: 5
  searchers:
    - type: claude
    - type: x          # X/Twitter search (requires TWITTER_BEARER_TOKEN)
    - type: exa        # Exa neural search (requires EXA_API_KEY)
```

**Claude E2E** (`type: claude_e2e`) — single Claude call with web search, simpler and faster:

```yaml
pipeline:
  type: claude_e2e
  target_articles: 10
```

### Environment variables

| Variable | Required | Description | Where to get |
|---|---|---|---|
| `CLAUDE_API_KEY` | Yes | Anthropic API key | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| `GNEWS_API_KEY` | Only for GNews searcher | [gnews.io](https://gnews.io/) API key | [gnews.io/dashboard](https://gnews.io/dashboard) |
| `TWITTER_BEARER_TOKEN` | Only for X searcher | X/Twitter API v2 bearer token | [developer.x.com](https://developer.x.com/en/portal/dashboard) |
| `EXA_API_KEY` | Only for Exa searcher | [exa.ai](https://exa.ai/) API key | [dashboard.exa.ai](https://dashboard.exa.ai/api-keys) |

## Usage Tracking & Cost Estimation

Every pipeline run returns a `Usage` object alongside the sources, tracking:

- **API calls**: per-call token counts (input, output, cache read/write) and model IDs
- **Web searches**: number of Claude web search tool invocations
- **GNews requests**: number of GNews API HTTP requests
- **X API requests**: number of X/Twitter API HTTP requests
- **Exa requests**: number of Exa API search requests

Costs are estimated by dynamically fetching the latest pricing from the Anthropic docs. A hardcoded fallback is used if the fetch fails.

## Run Logging

Pass `--log` to write a JSON file per run with the input, output, and usage of every pipeline stage:

```bash
uv run python main.py "Climate summit negotiations" --log
# → logs/run_2026-02-12T14-30-00.json
```

The log file contains a `stages` array — one entry per pipeline element (query generation, aggregation, search, deduplication) — each with serialized input/output, usage breakdown, and wall-clock duration.

You can also enable logging via YAML config:

```yaml
pipeline:
  type: composable
  # ...
logging:
  enabled: true
  log_dir: logs
```

## Roadmap

- Metadata extraction: AI-generated perspective and quality signals per article
- Diversity ranking: select articles that maximize perspective coverage
- Iterative search: identify under-represented viewpoints and search for more

## Contributing

1. Fork, branch, make changes, add tests
2. `uv run pytest -v && uv run ruff check . && uv run mypy src/`
3. Open a PR

### Ideas

- Additional search backends (NewsAPI, Bing News, Reddit, etc.)
- Alternative query generators (OpenAI, local LLMs)
- Perspective/quality scoring and ranking

## License

MIT License -- Copyright (c) 2026 Unbubble Contributors
