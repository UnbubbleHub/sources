# Unbubble Sources

**Surface diverse, high-quality perspectives on any news event.**

Unbubble Sources takes a news event as input and returns articles representing a range of viewpoints, helping users break out of information bubbles.

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
```

### Programmatic usage

```python
import asyncio
from unbubble_sources import load_config, create_from_config, NewsEvent

async def main():
    config = load_config("configs/default.yaml")
    pipeline = create_from_config(config)
    event = NewsEvent(description="Climate summit negotiations")
    articles = await pipeline.run(event)
    for article in articles:
        print(f"{article.title} ({article.source})")

asyncio.run(main())
```

## Configuration

Pipelines are configured via YAML. Two types are available:

**Composable** (`type: composable`) — chain generators, an aggregator, and searchers for full control:

```yaml
pipeline:
  type: composable
  generators:
    - type: claude
  aggregator:
    type: pca
    n_components: 5
  searchers:
    - type: claude
```

**Claude E2E** (`type: claude_e2e`) — single Claude call with web search, simpler and faster:

```yaml
pipeline:
  type: claude_e2e
  target_articles: 10
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `CLAUDE_API_KEY` | Yes | Anthropic API key |
| `GNEWS_API_KEY` | Only for GNews searcher | [gnews.io](https://gnews.io/) API key |

## Roadmap

- Metadata extraction: AI-generated perspective and quality signals per article
- Diversity ranking: select articles that maximize perspective coverage
- Iterative search: identify under-represented viewpoints and search for more

## Contributing

1. Fork, branch, make changes, add tests
2. `uv run pytest -v && uv run ruff check . && uv run mypy src/`
3. Open a PR

### Ideas

- Additional search backends (NewsAPI, Bing News, etc.)
- Alternative query generators (OpenAI, local LLMs)
- Perspective/quality scoring and ranking

## License

MIT License -- Copyright (c) 2026 Unbubble Contributors
