# Unbubble — Project Plan

## Overview

Given a news event or claim (e.g. "US/Cuba tensions, 1 Feb 2026"), the system retrieves a set of articles about that event, each annotated with AI-generated metadata (opinion stance, claim support, perspective, tone, relevance, ...). It then returns a ranked list that maximises perspective diversity while favouring high-quality sources.

## Metadata

Two categories of AI-generated metadata:

1. **Perspective metadata** — position each article in a "perspective space" so we can select a set of articles that is as diverse as possible.
2. **Quality / relevance metadata** — score each article so that, among articles with similar perspectives, we can prefer the most reliable ones (e.g. official statements from involved parties > opinion pieces > secondary re-posts).

## Pipeline

### Step 1 — Article search

**Goal:** given an event/claim, return a broad list of candidate articles for further analysis.

**Initial approach:**
1. Generate multiple search queries from the input event (different models / prompts produce different queries).
2. Deduplicate and cluster queries using embedding similarity.
3. Run queries against one or more search engines.
4. Aggregate results and remove duplicate articles.

Design principle: define clean interfaces and API wrappers so the query-generation and search strategies are pluggable.

**Future ideas:**
- Search specific curated source lists.
- Use multiple search engines (Google, Bing, specialized news APIs).

### Step 2 — Metadata extraction

For each candidate article, extract:

- **Perspective metadata:** stance, framing, viewpoint dimensions — used to map articles in perspective space.
- **Quality / relevance metadata:** source authority, directness (primary vs. secondary), factual support — used for ranking within similar perspectives.

### Step 3 — Selection & ranking

**Goal:** return a final list of articles that covers the broadest possible range of perspectives, prioritising quality.

**Approach:**
1. **Diversity metric** — maximise coverage in perspective space (e.g. convex-hull volume or similar).
2. **Ranking** — among articles with comparable perspectives, sort by relevance/quality score.

**Future idea — iterative search:** after the first selection round, identify under-represented perspectives and run targeted searches to fill gaps.

## Open questions

- How to define and measure "perspective space" concretely.
- Which quality signals are most predictive of source reliability.
- How to balance diversity vs. quality in the final ranking.
