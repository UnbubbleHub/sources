# Unbubble Sources

**Surface diverse, high-quality perspectives on any news event.**

Unbubble Sources takes a news event as input and returns sources (news articles, tweets, …) representing a range of viewpoints, helping users break out of information bubbles. Each source is annotated with perspective metadata and the final selection is diversity-ranked using MMR.

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
from unbubble_sources import (
    load_config, create_from_config, NewsEvent,
    AnnotatedSource, Article, Tweet,
)

async def main():
    config = load_config("configs/default.yaml")
    pipeline, run_logger, price_cache = create_from_config(config)
    event = NewsEvent(description="Climate summit negotiations")
    sources, usage = await pipeline.run(event)

    for src in sources:
        if isinstance(src, AnnotatedSource):
            inner = src.source
            ann = src.annotation
            print(f"[{ann.political_lean.value}] {inner.url}")
            print(f"  Frames: {[f.value for f in ann.policy_frames]}")
            print(f"  Stance: {ann.stance_summary}")
        elif isinstance(src, Article):
            print(f"[article] {src.title} ({src.source})")
        elif isinstance(src, Tweet):
            print(f"[tweet] @{src.author_handle}: {src.text[:80]}")

    print(f"Estimated cost: ${usage.estimated_cost:.4f}")

asyncio.run(main())
```

## Pipeline

The pipeline has six stages. Stages 5 and 6 (annotation + ranking) are optional and configured via the `annotator` and `ranker` keys.

```
NewsEvent
  → 1. Query generation (expand event into diverse search queries)
  → 2. Query aggregation (deduplicate/diversify via PCA)
  → 3. Multi-source search (Claude, GNews, X/Twitter, Exa — in parallel)
  → 4. URL deduplication
  → 5. Perspective annotation (Claude LLM — extracts metadata per source)
  → 6. MMR diversity ranking (selects top-k diverse + relevant sources)
  → AnnotatedSource[]
```

## Perspective Annotation

Each source is annotated with structured perspective metadata using Claude. The annotation schema draws on validated frameworks from media studies and NLP research.

### Annotation fields

| Field | Type | Framework | Description |
|---|---|---|---|
| `political_lean` | 7-point enum | MBFC scale (Baly et al., 2020) | Far-left to far-right political positioning |
| `policy_frames` | list of enums | Boydstun et al. (2014) Policy Frames Codebook | Up to 3 of 15 generic issue frames |
| `stakeholder_type` | enum | Journalism source diversity | Primary voice: government, corporate, civil society, etc. |
| `stance_summary` | free text | — | 1–2 sentence summary of the source's position |
| `topic` | string | IPTC-inspired | Short topic label (e.g. "climate policy") |
| `geographic_focus` | string | — | Country or region the source focuses on |
| `relevance_score` | float 0–1 | — | How relevant the source is to the queried event |

### Why these frameworks?

**Boydstun's Policy Frames Codebook** (15 frames) was chosen because it is the most widely validated generic framing taxonomy in political communication research, tested across six major U.S. policy domains. Unlike topic-specific codebooks, its frames (economic, morality, fairness, security, etc.) transfer across any news domain.

**MBFC 7-point political lean** was chosen following Baly et al. (2020), who showed that Media Bias/Fact Check ratings are the most reliable publicly available source-level bias labels, and that a 7-point ordinal scale captures meaningful gradations lost by ternary (left/center/right) schemes.

**Stakeholder type** categories come from journalism research on source diversity — who gets quoted in news stories shapes which perspectives readers encounter.

## Diversity Ranking (MMR)

After annotation, sources are re-ranked using **Maximal Marginal Relevance** (Carbonell & Goldstein, 1998):

```
MMR(d) = λ · relevance(d) − (1 − λ) · max_similarity(d, already_selected)
```

MMR iteratively selects sources that balance relevance (how well they match the event) against diversity (how different they are from already-selected sources). The `lambda_param` controls the trade-off:
- `lambda_param=1.0` → pure relevance ranking
- `lambda_param=0.0` → pure diversity
- `lambda_param=0.5` (default) → equal weight

### Perspective distance

The `max_similarity` term uses a weighted multi-dimensional distance across five annotation dimensions:

| Dimension | Weight | Distance metric |
|---|---|---|
| Political lean | 0.30 | Ordinal distance on 7-point scale |
| Policy frames | 0.25 | Jaccard distance on frame sets |
| Stakeholder type | 0.20 | Categorical (same=0, different=1) |
| Geographic focus | 0.15 | Categorical |
| Topic | 0.10 | Categorical |

Weights prioritize political lean and framing differences since these are the dimensions most associated with information bubbles.

### Why MMR?

MMR was chosen because research on news recommender systems shows that a two-stage pipeline (quality filtering → diversity re-ranking) is the dominant approach for reducing filter bubbles, and MMR is the only diversity re-ranking method with statistical evidence of reducing both filter bubbles and misinformation exposure simultaneously. As a submodular function, it provides theoretical guarantees on diversity coverage.

## Configuration

Pipelines are configured via YAML. Two types are available:

**Composable** (`type: composable`) — chain generators, an aggregator, searchers, annotator, and ranker:

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
  annotator:             # optional: perspective annotation via Claude
    type: claude
    model: claude-haiku-4-5-20251001
    batch_size: 20       # sources per API call
  ranker:                # optional: MMR diversity ranking (requires annotator)
    type: mmr
    lambda_param: 0.5    # 0=diversity, 1=relevance
    top_k: 10            # final number of sources to return
```

**Claude E2E** (`type: claude_e2e`) — single Claude call with web search, simpler and faster:

```yaml
pipeline:
  type: claude_e2e
  target_articles: 10
  annotator:
    type: claude
  ranker:
    type: mmr
    lambda_param: 0.5
    top_k: 10
```

To disable annotation and ranking, simply omit the `annotator` and `ranker` keys.

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

Annotation API calls are tracked separately and included in the total cost. Costs are estimated by dynamically fetching the latest pricing from the Anthropic docs. A hardcoded fallback is used if the fetch fails.

## Run Logging

Pass `--log` to write a JSON file per run with the input, output, and usage of every pipeline stage:

```bash
uv run python main.py "Climate summit negotiations" --log
# → logs/run_2026-02-12T14-30-00.json
```

The log file contains a `stages` array — one entry per pipeline element (query generation, aggregation, search, deduplication, annotation, ranking) — each with serialized input/output, usage breakdown, and wall-clock duration.

You can also enable logging via YAML config:

```yaml
pipeline:
  type: composable
  # ...
logging:
  enabled: true
  log_dir: logs
```

## Data Types

### Source types

| Type | Fields | Description |
|---|---|---|
| `Article` | `title`, `url`, `source`, `published_at`, `description` | News article |
| `Tweet` | `tweet_id`, `author_handle`, `text`, `like_count`, ... | X/Twitter post |
| `AnnotatedSource` | `source` (Article\|Tweet), `annotation`, `relevance_score` | Source + perspective metadata |

### Annotation enums

| Enum | Values |
|---|---|
| `PoliticalLean` | `far_left`, `left`, `center_left`, `center`, `center_right`, `right`, `far_right`, `unknown` |
| `PolicyFrame` | `economic`, `capacity_and_resources`, `morality`, `fairness_and_equality`, `legality_constitutionality`, `policy_prescription`, `crime_and_punishment`, `security_and_defense`, `health_and_safety`, `quality_of_life`, `cultural_identity`, `public_opinion`, `political`, `external_regulation`, `other` |
| `StakeholderType` | `government`, `corporate`, `civil_society`, `academic`, `journalist`, `citizen`, `international_org`, `other` |

## References

- Boydstun, A.E., Gross, J.H., Resnik, P., & Smith, N.A. (2014). "Tracking the Development of Media Frames within and across Policy Issues." Carnegie Mellon University. — *Policy Frames Codebook (15 generic frames)*
- Baly, R., Da San Martino, G., Glass, J., & Nakov, P. (2020). "We Can Detect Your Bias: Predicting the Political Ideology of News Media." EMNLP 2020. — *MBFC-derived political lean scale*
- Carbonell, J. & Goldstein, J. (1998). "The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries." SIGIR '98. — *Maximal Marginal Relevance algorithm*

## Roadmap

- Iterative search: identify under-represented viewpoints and search for more
- Source credibility scoring (NewsGuard, Ad Fontes integration)
- Claim-level fact-checking integration

## Contributing

1. Fork, branch, make changes, add tests
2. `uv run pytest -v && uv run ruff check . && uv run mypy src/`
3. Open a PR

### Ideas

- Additional search backends (NewsAPI, Bing News, Reddit, etc.)
- Alternative query generators (OpenAI, local LLMs)
- Source credibility databases (NewsGuard, MBFC API)

## License

MIT License -- Copyright (c) 2026 Unbubble Contributors
