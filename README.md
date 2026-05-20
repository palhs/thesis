# thesis — L1 consensus evaluation

A 12-week thesis comparing four Layer-1 consensus protocols (PBFT, Casper FFG,
Snowman, Narwhal+Tusk) by discrete-event simulation. The repository holds the
sources, the LLM-maintained wiki, the simulator code, experiment results, and
chapter drafts in one tree.

## Layout

- `src/` — simulator (`scheduler/`, `nodes/`, `network/`, `event_log/`).
- `tests/` — unittest suites mirroring `src/`, plus `tests/integration/`.
- `configs/` — YAML experiment configs (populated by T27).
- `results/` — CSV and plot outputs (git-ignored; `.gitkeep` preserves the dir).
- `wiki/` — knowledge base. **`wiki/index.md` is the catalog of every page.**
- `drafts/` — thesis chapters in markdown.
- `raw/`, `resources/` — immutable source material.
- `docs/` — operating rules imported by `CLAUDE.md`.

## Quickstart

Requires Python 3.10 or newer. The simulator itself has no runtime
dependencies; the coverage tool is the only development dependency.

```sh
pip install -r requirements-dev.txt

make test          # run every suite
make test-nodes    # run one suite (scheduler|nodes|network|event_log|integration)
make coverage      # branch coverage across all suites, report only
make clean         # remove __pycache__, .coverage, .pytest_cache, htmlcov
```

## Working in the repo

- Agent-facing rules: [`CLAUDE.md`](CLAUDE.md) and [`docs/`](docs/).
- Knowledge base entry point: [`wiki/index.md`](wiki/index.md).
- Active work queue: [`TASKS.md`](TASKS.md).
