# Contributing to Unbubble Sources

Thanks for considering a contribution. Unbubble Sources is part of [Unbubble
Hub](https://unbubblehub.org), an open research initiative for tools that
fight social polarization. The project is small, friendly, and explicitly
research-oriented — most contributions land through conversation as much as
through code.

This document is the **external-facing** guide: it covers what the project
values, how to get involved, the pull-request loop, and the conventions a
contribution should respect. If anything below is unclear, opening an issue
is itself a useful contribution.

---

## What the project is trying to do

Sources is for **substantively contested questions** — questions where
reasonable people, looking at the same evidence, legitimately arrive at
different positions because they weigh different considerations (industrial
policy, energy strategy, immigration, taxation, foreign policy, …). For
these questions the goal is *not* to surface a "correct" answer but to make
the **space of substantive positions partially visible** so a reader can form
their own judgment with awareness of what they would otherwise miss.

This shapes design choices throughout the codebase. Three principles to keep
in mind when proposing changes:

- **Transparency over cleverness.** Every annotation, score, and ranking
  decision should be inspectable. If a choice (a weight, a threshold, a
  prompt) is buried inside code, future contributors and users cannot
  contest it. Prefer YAML-configurable parameters and explicit provenance
  over hidden defaults.
- **Plurality over correctness.** The system tries to span the range of
  legitimate positions rather than identify the "right" one. Be cautious
  with features that filter, suppress, or rank-down whole classes of
  sources.
- **Open, auditable, reproducible.** Outputs should be reproducible from
  config + inputs. Avoid hidden state. When you cache, cache transparently.
  When you call an LLM, log the prompt and the parsed result.

These aren't slogans — they map directly onto reviewer questions. If a PR
makes the meta-level *less* visible (more hardcoded weights, less
configurable axes, hidden filtering), reviewers will push back.

---

## Ways to contribute
There
is room for contributions of many kinds:

- **Code** — new searchers, query generators, annotators, scorers, metrics,
  rankers, tests, bug fixes, performance work, doc improvements.
- **Datasets** — hand-labeled ground-truth fixtures for evaluation (we will
  need these for the metrics work and the paper). A few dozen labeled
  sources for one or two contested topics is genuinely useful.
- **Research notes** — write up an analysis of how the pipeline performs on
  a topic you know well; surface where it gets things right or wrong.
- **Translations and locale calibration** — the annotation prompts and (in
  future) URL-genre heuristics behave differently across journalistic
  cultures. Native speakers of Italian, Spanish, French, German, and others
  are valuable here.
- **Issues and feedback** — opening a well-described issue, even without a
  fix, is a real contribution.

If you're not sure where to start, open an issue describing what you'd like
to work on, or reach out via the channels on the [Unbubble Hub
homepage](https://unbubblehub.org).

---

## Getting set up

Detailed setup is in the [README](../README.md). The short version:

```bash
git clone https://github.com/UnbubbleHub/sources.git
cd sources
uv sync --all-extras   # base + ml + dev
export CLAUDE_API_KEY=...
uv run pytest -v
uv run python main.py "Climate summit negotiations"
```

Python 3.11+ is required. The project uses [uv](https://github.com/astral-sh/uv)
as its package manager.

A few notes:

- The default config uses `PCAAggregator`, which depends on
  `sentence-transformers` and `torch`. Without the `ml` extras, use a
  config that sets `aggregator: {type: noop}` or use `claude_e2e.yaml`.
- The `[dev]` extras include `pytest`, `mypy`, `ruff` — needed for the CI
  checks described below.
- Tests do not make real network calls. If you add a test that requires
  one, mock the API boundary instead.

---

## The pull-request loop

1. **Open an issue first** for anything more than a one-line fix. This is
   how we coordinate and avoid duplicated work. Describe what you intend
   to do, ideally with a sketch of the design. Maintainers will respond
   quickly with thoughts or questions.
2. **Fork and branch.** Branch from `main`. Use a short, descriptive name;
   prefixing with your initials is conventional in this repo
   (e.g. `lc/exa-search`, `dlb/genre-annotator`).
3. **Keep PRs focused.** One concern per PR. A refactor and a new feature
   should be two PRs. Smaller PRs get reviewed faster and merged with less
   friction.
4. **Run the dev checks locally before pushing:**

   ```bash
   uv run ruff check .
   uv run ruff format .
   uv run mypy src/
   uv run pytest -v
   ```

   CI runs the same three checks (`ruff check`, `mypy src/`, `pytest -v`)
   and will block a merge if any fail.
5. **Update documentation.** If you changed behaviour visible to users,
   update the `README.md`. If you added a contributor-facing process or a
   new convention, update this file.
6. **Open the PR** against `main` with a clear title and a description
   that explains the *why*, not just the *what*. Link the issue. List any
   follow-ups you're deliberately deferring.
7. **Address review comments.** Reviewers may push back on the design
   itself, not just the implementation — that's expected, and welcome. If
   a discussion gets long, consider splitting the PR.

---

## Coding conventions

- **Type-annotate everything.** `mypy --strict` must pass.
- **Imports at the top of the file**, ordered stdlib → third-party →
  `unbubble_sources.*`. Enforced by ruff/isort. Lazy imports are reserved
  for optional ML dependencies (see `aggregator/embeddings.py` for the
  pattern).
- **Frozen dataclasses** for core data types (in `data/models.py`). `Usage`
  is the deliberate exception — it accumulates.
- **Pydantic models** for configuration. Discriminated unions via
  `type: Literal[...]` + `Field(discriminator="type")`.
- **Protocol-based interfaces** for every pipeline stage
  (`QueryGenerator`, `SourceSearcher`, `SourceAnnotator`, `SourceRanker`,
  `QueryAggregator`). Implementations satisfy the protocol structurally.
- **Async everywhere I/O happens.** Concurrency via `asyncio.gather`.
- **No `print()` in library code.** Use `logging.getLogger(__name__)`.
  `main.py` is the only place that may write to stdout.
- **Individual searcher / generator failures are logged and skipped**, not
  raised. One failing backend should not abort a whole run.
- **No new hardcoded weights or thresholds in code.** If you need a
  knob, make it a config field. If the behaviour reflects a design
  decision, document it in code *and* in the README.

### Adding a new component

The pattern is the same for any new searcher, generator, aggregator,
annotator, or ranker:

1. Implement the corresponding `Protocol` from `<package>/base.py` in a
   new file under `src/unbubble_sources/<package>/`.
2. Add a Pydantic config model in `src/unbubble_sources/config/models.py`
   with a `type: Literal[...]` discriminator, and extend the union type.
3. Add the instantiation branch in `src/unbubble_sources/config/factory.py`.
4. Export the class from `src/unbubble_sources/__init__.py` and add it to
   `__all__`. If the class has heavy or optional dependencies, use the
   lazy-import path (`__getattr__`) instead of a direct import.
5. Add tests under `tests/test_<name>.py`. Mock the API boundary; do not
   make real network calls.
6. Add an example YAML config under `configs/` if it exercises a new
   capability.
7. Update the README's environment variables, config, and capabilities
   tables.

A concrete worked example for adding a search backend:

1. Create `src/unbubble_sources/search/mybackend.py` with a class that
   implements the `SourceSearcher` protocol from
   `src/unbubble_sources/search/base.py`.
2. Add a `MyBackendSearcherConfig` Pydantic model to
   `src/unbubble_sources/config/models.py` with
   `type: Literal["mybackend"]`, and extend the `SearcherConfig`
   discriminated union.
3. Add the instantiation branch in
   `src/unbubble_sources/config/factory.py` (inside `create_searcher`).
4. Export the class from `src/unbubble_sources/__init__.py` and add it to
   `__all__`. If the class pulls in an optional SDK, use the
   lazy-import path (`__getattr__` at the bottom of `__init__.py`).
5. Add `configs/with_mybackend.yaml` exercising the new searcher.
6. Add `tests/test_mybackend_searcher.py`, mocking the SDK at its boundary.
7. Update `README.md` with the new environment variable and a row in the
   searcher table.

---

## Tests, types, lint

All three must pass before a PR is mergeable:

```bash
uv run pytest -v
uv run mypy src/
uv run ruff check .
```

Conventions:

- Tests are standalone `def test_*` functions, not classes.
- Use module-level `@pytest.fixture` for shared setup.
- `pytest-asyncio` is configured in `auto` mode — `async def test_*`
  works directly.
- Mock external APIs at the SDK boundary (e.g. `anthropic.AsyncAnthropic`),
  not at HTTP.
- One test file per source module under `tests/`, mirroring the package
  layout.

---

## Working with API keys and secrets

Do not commit `.env` files, real API keys, or sample run logs that contain
secrets. The repo's `.gitignore` covers the standard cases, but please
double-check any new fixture files. If you suspect a key has been leaked,
revoke and rotate it immediately, then notify the maintainers privately
(do **not** open a public issue — that amplifies the leak).

The `livedemo/` subproject talks to the library through an HTTP boundary
and has its own auth conventions documented in `livedemo/AGENTS.md`.

---

## Licensing

Unbubble Sources is licensed under the
[GNU Affero General Public License v3.0 or later](../LICENSE)
(AGPL-3.0-or-later), in line with the Unbubble Hub policy that
information-integrity tools should be open, transparent, and accessible.

By contributing, you agree that your contributions will be licensed under
the same terms. If you embed Unbubble Sources in a network-accessible
service, the AGPL requires you to make the source of your modified
version available to users of that service — read the
[LICENSE](../LICENSE) carefully if this affects your deployment plans.

For substantial contributions (new components, new pipeline stages),
maintainers may ask you to add yourself to a `CONTRIBUTORS` file or to be
credited in the academic paper depending on the nature of the work.

---

## A note on dependencies

The base install must stay lightweight (so Sources can run in serverless
environments like Vercel Python functions, which cap bundles at 500 MB
uncompressed). Heavy or optional dependencies — `torch`,
`sentence-transformers`, `transformers`, large model artifacts — must be
declared in `[project.optional-dependencies]` and lazy-imported. Today the
`ml` extra holds the PCA-aggregator dependencies; future extras (`evaluate`,
`local-llm`, …) should follow the same pattern.

If you find an existing hard dependency that should be optional, that's a
welcome bug report or PR.

---

## Roadmap pointers

If you're looking for a place to contribute, the README's "Roadmap" and
"Ideas" sections are a good start. Larger architectural changes currently
in design — a `Scorer` / `Metric` protocol pair, a `RunResult` wrapper,
deterministic URL-based article-genre annotation, a political-compass
metric, an evaluation harness — will land as separate issues with linked
design notes. If any of those sound interesting, please reach out before
starting work so we can avoid stepping on each other.

---

## Where to ask questions

- GitHub issues for code, bugs, and feature discussions.
- The links on the [Unbubble Hub homepage](https://unbubblehub.org) for
  broader project conversations.
- The [Substack](https://unbubblehub.substack.com) for project updates and
  research notes.

Thanks for being here.
