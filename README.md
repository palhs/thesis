# thesis — L1 consensus evaluation

This is a 12-week undergraduate thesis that compares three Layer-1 consensus
protocols — PBFT, Casper FFG, and Snowman — through a deterministic
discrete-event simulator built from scratch. A single repository holds the
source papers, an LLM-maintained wiki, the simulator code, the experiment
results, and the chapter drafts, so every claim in the thesis traces back to a
reproducible run. The project is a collaboration between a human author and
Claude (Anthropic).

## Layout

- `src/` — simulator. Protocol packages (`pbft/`, `pos/` = Casper FFG,
  `snowman/`) plus the shared engine (`scheduler/`, `nodes/`, `network/`,
  `event_log/`, `common/`, `config/`, `workload/`) and the experiment
  drivers (`delay/`, `adversary/`, `output/`).
- `tests/` — unittest suites mirroring `src/`, plus `tests/integration/`.
- `results/` — CSV and plot outputs (git-ignored; `.gitkeep` preserves the dir).
- `wiki/` — knowledge base. **`wiki/index.md` is the catalog of every page.**
- `drafts/` — thesis chapters in markdown.
- `raw/`, `resources/` — immutable source material.
- `docs/` — operating rules imported by `CLAUDE.md`.

## Install

Prerequisites:

- **Python 3.10 or newer** (developed on 3.13).
- **Runtime dependency**: `PyYAML` (the config loader). It is the only thing
  the simulator and the test suite need — install it with
  `pip install -r requirements.txt`.
- **Dev dependencies** (`make install`): `coverage` for `make coverage`, and
  `matplotlib` for figure rendering (`make preview`, `output.plots`). Neither
  is needed to run a simulation.
- **pandoc** (optional): only `make preview` uses it, to render a draft chapter
  to HTML. Install from <https://pandoc.org> (e.g. `brew install pandoc`).
  Skip it if you are not previewing chapters.

```sh
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt                       # runtime deps (PyYAML)
make install                                          # dev deps; == pip install -r requirements-dev.txt
```

## Test

The suites cannot be discovered in one pass (two suites ship a `_helpers.py`
under the same name), so the Makefile runs one suite at a time with the right
`PYTHONPATH`.

```sh
make test          # run every suite
make test-pbft     # run one suite; also: scheduler nodes network event_log
                   #   config common pbft pos snowman output workload
                   #   delay adversary integration
make coverage      # branch coverage across all suites, report only
make clean         # remove __pycache__ and coverage artifacts
```

## Run experiments

Every driver is a module run from the repo root with `src/` on `PYTHONPATH`.
Each writes its CSVs under `results/`. The simulator is deterministic (fixed
seeds), so a run reproduces bit-for-bit.

```sh
# Baseline: run every protocol's scenarios into results/baseline/baseline.csv
# (sequential, single process, no --jobs; ~90s)
PYTHONPATH=src python3 -m output.baseline

# Sweeps (long-running; add --smoke for a 1-seed sanity pass)
PYTHONPATH=src python3 -m delay.sweep --smoke
PYTHONPATH=src python3 -m adversary.sweep --smoke

# Full sweeps, parallelised
PYTHONPATH=src python3 -m delay.sweep --jobs 8
PYTHONPATH=src python3 -m adversary.sweep --jobs 8 --heavy-jobs 1
```

Sweep flags:

- `--jobs N` — run N cells in parallel via a spawn Pool (default 1). Run this
  in a normal terminal, **not** the Claude Code sandbox — multiprocessing
  deadlocks there.
- `--heavy-jobs N` — parallelism for the memory-heavy class only (Snowman
  n≥25, ~5 GB/cell), run as a separate tier after the light cells. Default 1.
  Raising it risks OOM (two ~5 GB cells already exceed 16 GB). `adversary.sweep`
  only.
- `--smoke` — 1-seed sanity pass; finishes in seconds.
- `--fresh` — clear the checkpoint dir and re-run from scratch. Without it, an
  interrupted sweep resumes from the cells already completed.

Sweeps checkpoint per cell and produce byte-identical output regardless of
`--jobs`, so a run interrupted with Ctrl+C can be re-run to continue where it
stopped. `output.baseline` has no `--jobs`; it runs every scenario sequentially
in one process.

## Render figures

Figure rendering needs `matplotlib` and reads the committed CSVs — no re-run
required.

```sh
PYTHONPATH=src python3 -m output.plots            # baseline, with 95% CI bars
PYTHONPATH=src python3 -m output.plots --no-ci    # mean curves only
PYTHONPATH=src python3 -m output.delay_plots
PYTHONPATH=src python3 -m output.adversary_plots

make preview                              # render a draft chapter to inline HTML
make preview FILE=drafts/ch3_methodology.md
```

`make preview` additionally requires **pandoc** on the PATH (see Install) and
the chapter's figure PNGs already rendered on disk.

## Working in the repo

- Agent-facing rules: [`CLAUDE.md`](CLAUDE.md) and [`docs/`](docs/).
- Knowledge base entry point: [`wiki/index.md`](wiki/index.md).
- Active work queue: [`TASKS.md`](TASKS.md).
