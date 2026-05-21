# Planned Features

A living list of the work the team has in mind for Unbubble Sources. Items are organised by theme. The intent is to be transparent about the direction of the project so external contributors can find good places to help and so design decisions can be contested early. Anything here that you have opinions about — please open an issue or a discussion.

## Status legend

- **[x] Done** — landed in `main`.
- **[~] In progress** — on a branch or active design.
- **[ ] Planned** — agreed direction, no work started.
- **[?] Idea** — under consideration; needs scoping or discussion.

Since we anticipate the architecture will need refactoring into subpackages (see below), items are also tagged with their **intended package home**:

- **[core]** — shared vocabulary package.
- **[sources]** — `unbubble-sources`, this retrieval pipeline.
- **[eval]** — scorer-evaluation tooling.
- **[livedemo]** — the Next.js front-end under `livedemo/`.

The **Branch** column on each table is empty until an item is picked up. When you start work on an item, put your branch name there in the same PR so other contributors can see it's claimed.

---

## Architectural direction

Integrating future annotation and evaluation tools cleanly may require a refactoring pass.

---

## First metrics — scalar + visual

The user-facing payoff of the foundation work. The visual ones double as the demonstration of the project's "make the perspective space visible" thesis.

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Ship a lean-entropy scalar metric | [core] | | Validate the new metrics pipeline end-to-end with the smallest possible real metric, and give users a single number describing how spread out the political lean of their results is. Trivial to implement (Shannon entropy of the `political_lean` distribution); valuable as a regression check on every PR that changes ranking or annotation. No visualization. |
| [ ] | Ship the first political-compass visualization | [core] | | Headline visual metric for the project's "make the perspective space visible" thesis — every contested-query run gets a scatter plot in compass coordinates the user can interpret directly. First version uses only what's already in `PerspectiveAnnotation`: x-axis from `political_lean` linearly mapped, y-axis heuristically derived from `policy_frames` (`security_and_defense` + `crime_and_punishment` → authoritarian; `fairness_and_equality` + `quality_of_life` → libertarian). Labelled clearly as approximate; replaced by a proper field once the schema-upgrade item below lands. |
| [ ] | Render `scatter_2d` metrics in the live demo | [livedemo] | | Unlocks every future 2-D visual metric in one frontend change. A generic React renderer reads any `MetricResult` whose `visualization == "scatter_2d"` and plots its `data.points` payload — the same code then serves the political compass, the future Nolan chart, Eysenck two-axis, and embedding scatter. New visual metrics ship with zero frontend work after this lands. |

## Article genre — 7-type taxonomy

A complementary axis of diversity: which **genre** of article a source is (breaking news vs. opinion vs. fact-check, etc.). News and opinion shape perception through different mechanisms; treating them as equivalent flattens information that downstream metrics could use.

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Add article-genre annotation and a coverage metric | [core] for annotator + enum + metric; [sources] for locale configs | | Today the pipeline treats wire-news, op-eds, fact-checks and explainers as interchangeable, which they are not — news shapes perception by which facts it presents, opinion by what it argues about those facts. Adding genre as a first-class annotation lets metrics ask whether a contested-query result is fact-supply-heavy or argument-supply-heavy, and lets future rankers balance the two. Implementation: a deterministic URL-pattern annotator with per-locale config (`configs/locales/{en,it,es,fr,de}.yaml`); a 7-value `article_genre` enum on `PerspectiveAnnotation`; a `GenreCoverageMetric` reporting per-genre distribution plus the fact-supply / argument-supply ratio. Also the first non-Claude annotator — validates that the Scorer / Metric architecture admits deterministic implementations cleanly. |

## Schema upgrade for the compass

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Replace the political-compass heuristic y-axis with a proper annotation | [core] for schema + enum; [sources] for the Claude annotator prompt update | | The first political-compass metric derives its y-axis heuristically from policy frames; that mapping is convenient but indirect and easy to dispute. Adding `authority_lean` as a first-class annotation field — produced by Claude alongside the existing perspective dimensions — gives the compass a y-axis as defensible as its x-axis. Touches the `PerspectiveAnnotation` schema and enum, the Claude annotator prompt, the tests, and the political-compass metric's value derivation. |

## More metrics

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Add scalar coverage metrics for frames, stakeholders, geography | [core] | | Diversity on `political_lean` alone isn't enough: a query might return ten sources from the same stakeholder type (all government, all corporate), all framed economically, all geographically US-centric — and still look balanced on lean alone. These scalars surface those gaps as single numbers per run. Three metrics, one per dimension: `FrameCoverageMetric`, `StakeholderDiversityMetric`, `GeographicDiversityMetric`. |
| [ ] | Add an embedding-based scatter metric | [core] | | The political compass is theory-driven (you have to pick the axes); embedding-based scatter is data-driven (the axes fall out of the data). Shipping both gives users a useful cross-check: if the data-driven view and the theory-driven compass tell different stories about a query, that's a finding worth investigating. Implementation: embed stance summaries, project to 2-D via PCA or UMAP, emit `scatter_2d` using the same payload shape as the compass. |

## Cross-project integration with sibling repos

Connects Sources to the rest of [Unbubble Hub](https://unbubblehub.org).

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Add a searcher for GDELT Pulse | [sources] | | Sources runs only against live commercial APIs today (Claude `web_search`, GNews, Exa, X, Grok). The org also runs [GDELT Pulse](https://github.com/UnbubbleHub/gdelt-pulse), which indexes GDELT's 15-minute global news feed with its own annotations. Adding a searcher for it makes Unbubble Hub's own data a first-class option in any pipeline config — no extra API key, no commercial rate limits, indexed by the org, and useful for replication studies. |
| [ ] | Score sources against Glance's misinformation labels | [core] | | Sources currently ranks by relevance and diversity but has no view on whether any individual result has been flagged as misinformation elsewhere. [Glance](https://github.com/UnbubbleHub/glance) maintains an open misinformation-labelling database — joining against it on the URL or domain gives every result a credibility flag, surfaced as a `Score` with provenance `"GlanceScorer"`. Downstream metrics or filters can use it without coupling to Glance's specific schema, and any other project depending on Glance benefits from the same wrapper. |

<a id="monorepo-restructure"></a>

## Monorepo restructure

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [?] | Extract a shared core package from this repo | [core] + [sources] | | As the project grows beyond the retrieval pipeline — generic scorers and metrics, scorer-evaluation tooling, primitives that sibling Unbubble Hub projects can reasonably depend on — the single-package layout may start to hold the team back. Splitting the canonical primitives into a separate package that all sibling projects can depend on would remove that bottleneck without changing how Sources itself works. The exact shape of the refactor — monorepo workspace, separate repos, a single shared package, something else — is still **under discussion**; the file-move plan below is one concrete proposal, not a commitment. |

**File-move plan (mechanical, no behaviour change):**

- Move to `packages/core/src/unbubble_core/data/models.py`: `Score`, `Source`, `Article`, `Tweet`, `PerspectiveAnnotation` and its enums (`PolicyFrame`, `PoliticalLean`, `StakeholderType`), `AnnotatedSource`, `NewsEvent`, `SearchQuery`, `Usage`, `APICallUsage`.
- Move to `packages/core/`: the entire `scoring/` and `metrics/` sub-packages (incl. `MetricsRunner` and the `NoOpMetric` placeholder).
- Keep in `packages/sources/`: `RunResult`, `DiversityReport`, the entire pipeline (`composable`, `claude_e2e`, `_report`), every searcher / generator / aggregator / annotator / ranker implementation, `config/`, `pricing.py`, `run_logger.py`, `stream_logger.py`, `main.py`, the live demo.
- Rewrite `unbubble_sources/__init__.py` re-exports to forward from `unbubble_core.*`.
- Top-level workspace `pyproject.toml` (uv workspace member list); per-package `pyproject.toml` with its own dependencies.

**Sequencing:** must come **after** the livedemo frontend migrates off the transitional `AnnotatedSource.relevance_score` float (see "Smaller cleanups" below) so `AnnotatedSource` lands in `core` without the sources-specific shim. Also worth doing **before** the scorer-eval thread starts shipping code, to avoid having to move it twice.

**Risks:** existing import paths (`from unbubble_sources import …`) will break for downstream users — version-bump and document carefully. The Vercel deployment in `livedemo/api/requirements.txt` will need to pin both new package names.

## Evaluation harness

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Build an evaluation harness with ground-truth fixtures | [eval] | | Today any quantitative claim about annotation quality, ranker quality, or metric stability has to be made by hand. An evaluation package with hand-labelled fixtures for a handful of representative contested queries — plus standard runners for classification accuracy, Cohen's κ, and ablation sweeps — turns those claims into something CI can check. Required to back any rigorous external evaluation. |

---

## Smaller cleanups (good "first issue" material)

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Move `exa-py` and `mistralai` into optional extras | [sources] | | Sources is documented as Vercel-deployable, but `exa-py` and `mistralai` are hard dependencies even though only one searcher / generator each needs them. That contradicts the README's "searchers are optional" framing and bloats the base install. Move both to `[project.optional-dependencies]` and wrap their module-level imports with the `try/except` pattern used in `aggregator/embeddings.py`. Open question: granular `[exa]` / `[mistral]` extras vs a combined `[searchers]` group — defer to PR author. |
| [ ] | Drop the transitional `AnnotatedSource.relevance_score` field | [sources] then [core] | | The legacy `relevance_score` float on `AnnotatedSource` is kept as a transitional duplicate of `scores.get_score("relevance").value` so the existing livedemo frontend keeps working without a wire-format change. Once the frontend migrates (`livedemo/app/types.ts`, `components/SourcesTable.tsx`, `components/StageDetails.tsx`, `demo-run.json`), the field can go and `AnnotatedSource` becomes single-sourced — the cleaner shape it was always meant to have. Synchronise with the monorepo restructure so `AnnotatedSource` lands in `core` without the sources-specific shim. |
| [ ] | Add a registry pattern for pluggable components | [sources] | | Adding a new searcher / generator / aggregator / annotator / ranker today touches three files in lock-step: the implementation, the Pydantic config-union in `config/models.py`, and the factory branch in `config/factory.py`. A `@register_searcher("…")` decorator (etc.) collapses this to one file — each plugin declares itself, the Pydantic discriminator is built programmatically, the factory dispatch is automatic. Drops contributor onboarding cost meaningfully. |
| [ ] | Type pipeline constructors on protocols, not concrete classes | [sources] | | Both pipelines today take `annotator: ClaudeAnnotator \| None` and `ranker: MMRRanker \| None` even though the corresponding protocols (`SourceAnnotator`, `SourceRanker`) already exist. This silently blocks alternative implementations — a future MBFC-based annotator can't be plugged in without changing the pipeline signature. Switching to the protocols makes everything genuinely drop-in. |
| [ ] | Extract `perspective_distance` into its own module with config-driven weights | [core] for the distance class; [sources] for the MMR ranker that consumes it | | The weights that decide MMR's diversity — political_lean 0.30, policy_frames 0.25, stakeholder 0.20, geographic_focus 0.15, topic 0.10 — are hardcoded constants in `mmr.py`. That's exactly the kind of buried meta-level decision the project's transparency principle says should be exposed. Lifting them into a `PerspectiveDistance` class that owns the weights and per-dimension callables, configurable from YAML, makes the choice contestable at config time without code changes. |
| [ ] | De-duplicate the annotate-then-rank tail across pipelines | [sources] | | `ComposablePipeline` and `ClaudeE2EPipeline` end with the same ~40 lines: optionally annotate, optionally rank, run metrics, build the diversity report. A `PostProcessor` (or similar) shared between both eliminates the divergence risk — any future pipeline type plugs into the same tail. |
| [ ] | Surface a pre-run cost estimate as a library API | [sources] | | The live demo headlines "~$0.20 per run" as a user expectation, but the Python API offers no way to ask for that estimate before kicking off a run. That hurts iteration in notebooks (you can't tell whether a sweep will cost $1 or $1000 ahead of time) and means the live-demo string can drift from reality. A `pipeline.estimate_cost(event, config)` that returns a dollar range based on pricing tables + configured components fixes both. |

## New searchers (longer-term)

All `[sources]` — searchers are pipeline components, not shared vocabulary.

| Status | Item | Branch | Description |
|---|---|---|---|
| [?] | Add searchers for NewsAPI and Bing News | | Two of the most-used commercial news APIs, with broader source coverage than the searchers currently shipped. Gives users a third- and fourth-party view to cross-reference against Claude's and Exa's. |
| [?] | Add a Reddit searcher | | Surfaces citizen and non-mainstream voices that commercial-news searchers undersample — particularly important on contested questions where the editorial line of major outlets is uniform. |
| [?] | Add a curated source-list searcher | | Lets a user constrain retrieval to a hand-picked set of domains (e.g. `solarpunk-magazines.yaml`, `southern-european-press.yaml`). Built by scoping an existing searcher (Exa or GNews) to the list. Was in `planning/plan_en.md` as a future idea. |
| [?] | Add an RSS / Atom feed searcher | | Press releases, niche publications and small outlets are typically reachable only via RSS — commercial news indices skip them. An RSS/Atom searcher closes that hole and unlocks long-tail sources the rest of the project's searchers can't see. |
| [?] | Add a local-archive (static-corpus) searcher | | Lets a user search a fixed corpus (HuggingFace dataset, JSONL file) for reproducible studies — useful for replicating an experiment six months later when the live web has moved on. Generalised by the static-corpus support work in the research thread below. |
| [?] | Run an iterative search loop | | After one ranking pass, check which annotation dimensions are under-represented (e.g. no `right` lean in the top-k) and run a second, targeted query to fill the gap. Most direct expression of the project's "make the perspective space visible" principle — the tool actively shopping for what it's missing. |

## New scorers (longer-term)

Most of these are alternative implementations of the `Scorer` protocol. They work on any text and have no pipeline assumptions, so they live in `[core]` unless noted otherwise.

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [?] | Add domain-lookup scorers for political bias (MBFC, AllSides) | [core] | | Domain-lookup scoring is deterministic, free, and defensible — much more so than LLM-inferred `political_lean`. For sources whose domain is rated by MBFC or AllSides, look up the label and emit it as a `Score`; let the Claude annotator fill in only the gaps. Reduces both cost and inter-run variance. |
| [?] | Add quality / credibility scorers (NewsGuard, Ad Fontes) | [core] | | Quality of a source is a different question from where it sits on the political spectrum. Two well-known commercial rating services (NewsGuard, Ad Fontes Media Bias Chart) score sources on reliability / quality / factuality — wrapping them as `Scorer` implementations lets metrics and rankers distinguish "is this trustworthy" from "what perspective is it". |
| [?] | Add an embedding-based diversity ranker | [core] for the embedding / scoring side; [sources] for the ranker variant | | The current MMR diversity dimension depends on the symbolic enum schema (`political_lean`, frames, …); a pure-embedding ranker using stance-summary vectors is a useful complement. If the two rankers agree on a query, the symbolic schema is doing real work; if they disagree, that's a finding worth investigating. |
| [?] | Add an NLI-based stance scorer | [core] | | Today "relevance" is a single Claude-emitted number per source. NLI (natural language inference) lets us compute a more structured signal: how much does the article body support, contradict, or remain neutral on the specific claim in the event description. Cheap, deterministic, and orthogonal to perspective. |
| [?] | Compute multi-rater scorer agreement | [eval] | | Once we have multiple annotators (Claude + open-weights local LLM, or Claude + URL-based deterministic) we can report inter-annotator agreement (Cohen's κ) per dimension. Stops us from pretending one annotator's judgement is ground truth. Not a `Scorer` itself — an evaluation artefact about scorers. |

## Experimentation UX

For the researcher / non-developer audience the project is targeting. All `[sources]` — they wrap the pipeline.

| Status | Item | Branch | Description |
|---|---|---|---|
| [?] | Add YAML config inheritance via `extends:` | | Tweaking one knob in a preset today means cloning the whole `default.yaml` and editing. An `extends:` key would let users base their config on a preset and override just the fields they care about. Drops the friction for "try this with a slightly different lambda" workflows. |
| [?] | Allow `--set` CLI overrides for any config field | | `uv run python main.py "query" --set pipeline.ranker.lambda_param=0.7` lets users sweep a single parameter without writing a new YAML for each value. Pairs naturally with the sweep helper below. |
| [?] | Ship an explore notebook | | A notebook (`notebooks/explore.ipynb`) that loads a config, runs the pipeline, and surfaces every intermediate stage as a DataFrame for interactive inspection. The current `--log` flag dumps the same information to JSON but requires gluing in a notebook to be usable; shipping the notebook makes the inspection workflow first-class. |
| [?] | Ship a parameter-sweep helper | | `scripts/sweep.py` runs the pipeline across a grid of parameter values and reports the configured metrics, so users can answer questions like "is `lambda_param=0.5` better than `0.3` for this query?" without rewriting their config loop each time. |
| [?] | Ship an interactive config wizard | | For non-developer researchers: an interactive `python -m unbubble_sources.wizard` that asks a handful of questions (target cost, depth, languages, …) and writes the matching YAML. Removes the "learn the YAML schema first" barrier. |

## Conceptual / design-level

Not single issues, but principles that should shape future work.

- **Question-type awareness.** Sources is for *substantively contested questions* — questions where reasonable people, looking at the same evidence, legitimately arrive at different positions because they weigh different considerations. On factual questions ("when did the French Revolution begin", "is human activity warming the Earth") diversity-ranking is the wrong answer — it would amount to misinformation dressed as fairness. Either the tool should know the difference, or the UX / docs should be explicit that it is a misuse.
- **Meta-level explicit, everywhere.** Every annotation, score, ranking decision, and metric must be inspectable and contestable. This is the project's hardest principle and it should keep shaping reviewer questions — if a PR makes the meta-level *less* visible (more hardcoded weights, less configurable axes, hidden filtering), reviewers should push back. See `CONTRIBUTING.md` for the full framing.

---

## Research thread: compass-based retrieval-diversity audit

A focused programme that uses the political compass as a *diagnostic instrument* — first to audit existing retrievers on contested geopolitical and economic policy queries, then to ship a proof-of-concept compass-aware re-ranker that improves coverage where audits reveal gaps. Builds on the scoring and metrics primitives and consumes the political-compass metric (extended to two genuine axes).

### Thesis

A retrieval system can satisfy standard relevance metrics — top-k relevance, MRecall, click-through — while systematically failing to surface the range of substantive positions on a contested question. The compass turns that failure into something **visible and measurable**: each document is placed in a two-axis space (economic left ↔ right, social libertarian ↔ authoritarian) so coverage gaps become coordinates rather than vibes. The proposed contributions are:

- **Primary:** a diagnostic framework for retrieval diversity, validated through inter-model reliability, external markers from political-science work, and human annotation, applied to audit existing retrievers and reveal failure modes that are invisible to current metrics.
- **Secondary:** a proof-of-concept compass-aware re-ranker demonstrating that the framework enables practical system improvement.

### Driving research questions

These are working questions and will be refined as the harnesses mature:

- **Scorer reliability.** Can multiple LLMs reliably place documents on the compass, with stable agreement across models and consistency with established external markers from political-science work?
- **Natural distribution.** What is the natural distribution of contested-topic news articles on the compass? Are all four quadrants meaningfully populated?
- **Audit.** Do retrievers with similar performance on existing diversity metrics produce systematically different compass coverage profiles? What failure modes are revealed?
- **Re-ranker.** Can a compass-aware re-ranker improve coverage over baseline retrievers, and at what cost to topical relevance?
- **Utility.** Do domain experts and journalists find compass coverage profiles actionable as diagnostics of retrieval quality?

### Infrastructure prerequisites

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Index and search static corpora | [sources] | | The audit needs a deterministic, replicable corpus — production searchers all hit live web APIs (Claude `web_search`, GNews, Exa) and so are non-reproducible six months later. Build a `LocalCorpusSearcher` family that indexes a HuggingFace dataset or a JSONL file and answers queries with relevance ranking: `BM25Searcher`, `ContrieverSearcher` (dense), one `InstructionTunedSearcher` (e.g. an E5/Promptagator-style model). Useful well beyond the audit thread — replication studies, evaluation fixtures, offline development. |
| [ ] | Generate queries from documents | [sources] | | The audit needs a query set built from the corpus itself, since contested-question queries are the unit of analysis. Inverts the existing `QueryGenerator` direction (event → queries). A new `DocumentQueryGenerator` protocol takes a `Source` (article body + metadata) and produces candidate questions the document answers, filtered to contested-question shape. |
| [ ] | Compare multiple retrievers on a shared query set | [sources] | | Auditing is fundamentally a comparison exercise: same queries, different retrievers, see which coverage profiles diverge. Today the pipeline runs one retriever at a time. Sibling to the planned sweep helper but with retriever-as-axis rather than parameter-as-axis. |
| [ ] | Collect compass annotations from internal annotators | [eval] | | Human annotation is the ground-truth-equivalent against which we validate LLM scoring. A lightweight tool — CSV ingestion, instruction-sheet template, per-annotator schema validation, inter-annotator-agreement reporting — is enough for collaborator-scale (~5–20 annotators). Not a full crowdsourcing setup. |
| [ ] | Compute statistical agreement and retrieval metrics | [eval] | | The audit reports Krippendorff's alpha agreement, MRecall, inter-model reliability statistics (Cohen's κ per dimension, agreement-on-quadrant). Builds on the broader evaluation-harness item above — the audit thread is its first concrete consumer. |

### Scorers

New `Scorer` implementations attaching `Score` objects to `AnnotatedSource.scores`, with provenance making the producer visible. All `[core]` — generic text-scorers don't depend on the retrieval pipeline.

| Status | Item | Branch | Description |
|---|---|---|---|
| [ ] | Score documents on the political compass with an LLM | | The central scoring primitive of the thread. Structured-prompt LLM scorer emitting two `Score`s per document: `Score(name="compass_economic")` and `Score(name="compass_social")`, each on `[-1.0, 1.0]`, with `provenance` identifying the LLM and prompt variant. Supports zero-shot and few-shot. The intended prompt asks the model to identify claims about (a) the role of government in the economy and market intervention, and (b) authority, civil liberties and traditional values, score those claims separately, and aggregate — mirroring how the standard political-compass test triangulates positions from many specific propositions rather than asking for them directly. |
| [ ] | Aggregate multi-LLM scores while keeping disagreement | | One LLM's compass score is one opinion. The thread runs the same prompt through several LLMs and keeps the inter-model disagreement as *uncertainty information* rather than averaging it away. A `ConsensusScorer` aggregates outputs from multiple sibling scorers and emits the consensus value plus a per-document disagreement score (e.g. `Score("compass_economic_disagreement", …)`). Downstream metrics can then visualise both. |
| [ ] | Score documents against MBFC / AllSides / Ad Fontes | | The external-marker validation harness needs lookup-based scorers as a baseline against which LLM scores are checked for construct validity. Same primitive as the longer-term scorers listed above; called out here so the audit thread's prerequisites are visible in one place. |

### Metrics

New `Metric` implementations consuming the compass scores. All emit `MetricResult`s of the appropriate `visualization` kind so the frontend renderer can show them without per-metric code.

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Measure compass quadrant coverage | [core] | | The headline coverage scalar: how many of the four compass quadrants contain at least one retrieved document. Includes a configurable centrist deadzone around the origin so ambiguous documents don't claim quadrants they're not really in. |
| [ ] | Measure per-axis pole coverage on the compass | [core] | | Complementary to quadrant coverage: a boolean per axis recording whether both poles are represented in the retrieved set. Useful when quadrant coverage is high but the distribution is collapsed along one axis. |
| [ ] | Compute compass entropy | [core] | | Shannon entropy of the joint distribution of retrieved documents binned on the compass. Captures uniformity-of-coverage in a single number, complementary to the binary quadrant / per-axis measures. |
| [ ] | Measure divergence from the corpus natural distribution | [core] | | Coverage in absolute terms can mislead if the corpus itself is lop-sided. KL or Jensen-Shannon divergence between the retrieved distribution and the corpus's natural distribution corrects for that — how *different* is what you got from what you'd get sampling uniformly. The natural-distribution snapshot is itself a fixture produced once per corpus. |
| [ ] | Render retrieved documents as a compass scatter | [core] | | The visual headline of every audit report: a `scatter_2d` metric placing every retrieved document at its compass coordinates with per-point metadata (URL, title, publisher). Generalises the first heuristic political-compass metric to consume real `CompassScorer` output rather than the policy-frame heuristic. |
| [ ] | Compute MRecall alongside the compass suite | [sources] | | The audit's central claim — "two retrievers can have the same MRecall and different compass coverage" — requires running both side by side. Standard retrieval-evaluation metric (retrieved set vs. ground-truth relevant set), so retrieval-specific and lives in `sources`. |

### Re-ranker

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Re-rank for compass-distance diversity | [sources] | | Once the audit identifies coverage gaps, the natural next question is whether a *re-ranker* informed by the compass can close them at acceptable cost to relevance. A variant of the existing `MMRRanker` using Euclidean compass distance in `[-1, 1]²` as the diversity dimension (instead of, or alongside, the symbolic `perspective_distance`). Trade-off parameter `lambda_param` controls the relevance ↔ diversity balance; the evaluation harness sweeps it to produce a trade-off curve. |

### Workflows and scripts

End-to-end orchestration scripts that compose the pieces above. Each is a CLI / notebook entry point under `scripts/` or `notebooks/`. The package split runs cleanly along the *kind of question* each script answers: retrieval quality lives in `[sources]`, scorer quality in `[eval]`.

| Status | Item | Tag | Branch | Description |
|---|---|---|---|---|
| [ ] | Build the contested-query test set | [sources] | | First step in the audit. Filters one or more retrieval corpora (e.g. CC-News, NELA-GT, a multilingual conflict-coverage set) by topic keywords (migration, climate, energy, trade, geopolitics), extracts topics / entities / relationships from each document, and uses an LLM to generate contested-question queries the document plausibly answers. Output: `(documents, queries)` fixtures consumed by every later harness. |
| [ ] | Measure compass-scorer inter-LLM reliability | [eval] | | The first validation of compass scoring. Runs the same `CompassScorer` prompt through several LLMs on a pilot set, computes inter-model agreement, supports iterating on the prompt until agreement stabilises. Output: a documented scoring methodology with reliability statistics — without it, every later claim about compass coverage is unfounded. |
| [ ] | Compare human and LLM compass annotations | [eval] | | The second validation of compass scoring. Compares human annotations collected via the annotation tool against LLM scores on the same documents. Reports Krippendorff's alpha agreement and produces side-by-side disagreement reports for prompt iteration. |
| [ ] | Validate compass scores against published markers | [eval] | | The third validation. Joins documents to MBFC / AllSides / Ad Fontes ratings (where source matching applies) and compares LLM + human scores against those markers. Reports construct-validity statistics. See "Open methodology questions" below for the economic-axis caveat. |
| [ ] | Map the corpus natural compass distribution | [eval] | | Before reporting coverage gaps we need a baseline of what coverage looks like by default. Scores documents from the retrieval corpus with the validated `CompassScorer`, plots the joint distribution, identifies densely / sparsely / empty quadrants. Output: an empirically grounded baseline used by `CompassDivergenceMetric`. |
| [ ] | Audit retrievers' compass coverage | [sources] | | The central empirical result of the paper. For each contested query, runs each retriever (BM25, Contriever, instruction-tuned), scores top-k results on the compass, computes `MRecallMetric` and the compass-coverage suite, produces per-query / per-retriever coverage profiles with scatter-plot visualisations. Identifies cases where MRecall and compass coverage diverge. |
| [ ] | Evaluate the compass-aware re-ranker | [sources] | | The proof-of-concept practical contribution. Applies the compass-aware MMR re-ranker on top of the strongest baseline identified in the audit. Sweeps `lambda_param`, reports trade-off curves between coverage and topical relevance. |
| [ ] | Test robustness across compass scorers | [eval] + [sources] | | A finding that depends on a single LLM as scorer is fragile. Repeats the audit and re-ranker evaluation with at least one alternative LLM as scorer; reports whether the qualitative findings hold. |
| [ ] | Generate audit and re-ranker reports for expert review | [eval] + [sources] | | The audit can only call something a failure mode if domain experts agree it is one. Produces audit reports and re-ranker outputs for a selected query set, formatted for review by journalists and domain experts. Collects expert agreement on declared failure modes and on re-ranker output quality. |

### Open methodology questions

These are not blockers but need design discussion before the corresponding harness runs.

- **The economic axis lacks a widely-cited external marker.** MBFC, AllSides, and Ad Fontes all rate political bias on a single left ↔ right scale; none isolates the economic dimension. Possible approaches: derive an economic proxy from policy-frame distribution; use Manifesto Project rile scores where party-attributed text is available; run a separate expert-annotation pass restricted to the economic axis. To be picked before the external-marker validation harness lands.
- **Centrist deadzone size** for quadrant coverage is a tunable parameter affecting how many documents are excluded from quadrant counting. Default and reporting convention to be set with the first natural-distribution analysis.
- **Static vs live retrieval corpus.** Audit experiments need deterministic, replicable corpora; the production pipeline uses live web APIs. The static-corpus searchers above are the answer, but introduce a duplication of retrieval logic that should be reviewed before committing — possibly via a shared `Index` abstraction that both live and static searchers can sit on top of.
- **Multilingual scope.** Some candidate corpora are multilingual; the article-genre work already flags that journalistic norms differ across locales. The compass-scoring prompt and external markers may also need per-locale calibration.

### Sequencing

Items in the thread have hard dependencies. A reasonable order, with each step assuming the previous is at least partially landed:

- Scalar and political-compass metric foundations.
- Static-corpus support and the BM25 / dense / instruction-tuned searchers.
- Compass scorer plus the scorer-reliability harness.
- Annotation tool plus the human-AI alignment harness.
- External-marker scorers and validation harness.
- Natural-distribution analyzer.
- Retriever-audit harness — central paper result.
- Compass-aware re-ranker and its evaluation harness.
- Cross-scorer robustness check.
- Expert review and report generator.

### Concentration of risk

If the retriever-audit harness does *not* reveal divergence between MRecall and compass coverage, the diagnostic contribution is weakened. The thread still produces useful artefacts either way — the scorer methodology, the human-AI alignment results, the annotation dataset, the natural-distribution baseline, the re-ranker, and a negative finding is itself worth publishing. Worth noting before committing to the harness in case a smaller-scale pilot is preferable first.

---

## How to contribute to one of these

Most items above are not yet open as GitHub issues. If something here catches your eye:

- Open an issue describing what you want to take on. A sketch of the design is helpful but not required.
- Wait for a maintainer to ack before starting work, so we don't duplicate effort.
- Use the naming convention `<initials>/<feature>` for your branch.
- In the same PR (or in a follow-up doc-only commit), fill in the **Branch** column for the item you're taking, so other contributors can see it's claimed.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full PR loop and coding conventions.
