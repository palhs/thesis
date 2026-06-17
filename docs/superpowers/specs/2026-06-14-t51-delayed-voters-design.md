# T51 — Delayed-voters adversary + Family C delay-emission sweep — Design

Status: design, awaiting human review before plan.
Role: Engineer. Task: T51 (`[~]` In Progress).
Date: 2026-06-14.

## 1. Goal & scope

Bootstrap the simulator's **adversary-injection subsystem** and use it to run
the Week-10 Family C **`delay-emission`** experiment ("delayed voters /
intentionally slow nodes", [[concepts/adversary-model]] §3). A configurable
fraction of validators become *slow voters* — they hold every outbound
emission by a fixed multiple of their own protocol's round cadence — and we
measure the impact on time-to-finality across PBFT, Casper FFG, and Snowman.

This is the **first** task that fills the opaque `Node.adversary` slot with a
working strategy. It therefore lands a reusable injection seam that T52
(withhold) and T53 (equivocate) extend.

**In scope.** The `delay-emission` capability only; 3 protocols (PBFT, Casper
FFG, Snowman); `n ∈ {10, 25}`; the static-baseline network (Family C fixed
axis); the new `src/adversary/` package; one results CSV + plots; the
experiment wiki page; the wiki amendments listed in §10.

**Out of scope.** `withhold-participation` (T52), `equivocate-vote` (T53),
`disrupt-leader` (catalogued, no task — `TASKS.md` Backlog 2026-06-14
stretch flag); Narwhal+Tusk (deferred until T38.1); the streaming reducer
(deferred — `TASKS.md` Backlog 2026-06-12; the tiered scheduler is the
agreed mitigation).

## 2. Contracts consulted (the "what")

- [[concepts/adversary-model]] §3 — `delay-emission` binding semantics
  (PBFT: gate PREPARE/COMMIT broadcast; Casper FFG: gate attestation
  broadcast; Snowman: gate QUERY-RESPONSE send). Liveness class; safety
  unaffected.
- [[concepts/adversary-model-runtime]] §2 (intensity unit = fraction of
  nodes/stake/validators), §4 (`DelayProfile` reference sketch), §5
  (determinism).
- [[concepts/node-model]] §9 — adversary attachment surface: the
  `self.adversary` slot and the `delayer` row ("gate `broadcast` / `send`").
- [[concepts/experiment-matrix]] §3 (Family C fixed axes), §5 (FFG slot
  coherence), §6 (workload), §7 (seed policy).
- [[concepts/experiment-matrix-runs]] §3 (delay-emission intensity grid),
  §4 (budget).
- [[concepts/network-model]] §6 — **network is honest-only**; all adversary
  semantics attach at the Node level (binding constraint on §3 below).
- [[concepts/sweep-harness]] — `common.sweep.run_grid_tiered` (the agreed
  memory-aware driver).

Code precedents reused verbatim in shape: `src/delay/runners.py`,
`src/delay/sweep.py`, `src/delay/heavy.py`, `src/delay/clip.py`,
`src/config/factory.py::build_run`, `src/network/network.py::Network.bind`.

## 3. Architecture: the adversary-injection seam

### 3.1 The mechanism

`Network.bind(node)` wires each node's honest `send` / `broadcast` lambdas
onto `Network.submit_unicast` / `submit_broadcast`. The honest network must
stay honest ([[concepts/network-model]] §6), so the adversary attaches by
**re-wrapping a slow node's bound outbound API after `build_run`**, not by
editing the network, the scheduler, or any protocol FSM:

```
handle = build_run(config, seed, make)        # honest nodes; Network.bind done
inject_delay(handle, slow_ids, mult, ref_by_node)   # NEW — re-wrap slow nodes
result, logger = run_to_completion(handle, t_max=...)
```

For each slow node `inject_delay` does:

```
node.adversary = DelayProfile(nodes=slow_ids, intensity=f, mult=m)  # fill the slot
honest_send, honest_broadcast = node.send, node.broadcast
ref = ref_by_node[node.id]            # the node's protocol round cadence (s)
node.send      = lambda dst, type, payload, t: honest_send(dst, type, payload, t + m*ref)
node.broadcast = lambda type, payload, t:      honest_broadcast(type, payload, t + m*ref)
```

The slow node's message is *emitted late* by exactly `m·ref`; the honest
network then adds its normal delivery delay on top. Because the multiplier is
**fixed** (§5), the shift is a deterministic constant — no adversary RNG is
needed for this capability (see §8).

### 3.2 Why this seam

- **No source edits to network/scheduler/protocols.** Only the new
  `src/adversary/` package + filling the existing `Node.adversary` slot. All
  frozen baselines (T40/T41/T46/T47) are untouched.
- **Honest network preserved.** The wrap lives in `src/adversary/`, attaching
  at the Node outbound API — exactly the [[concepts/node-model]] §9 `delayer`
  cell. This is a *pragmatic realization* of the §9 "FSM dispatches through
  `self.adversary`" contract for the delay capability: since delay neither
  changes payloads nor drops/forks messages, intercepting at the bound
  `send`/`broadcast` is behaviourally identical to FSM-level dispatch and far
  less invasive. Recorded as a Revision (§10). T52/T53 will need deeper FSM
  hooks; T51 does not.

### 3.3 Slow-node selection

Slow set = the **highest-id `⌊f·n⌋` nodes**. Rationale: PBFT's view-0 primary
is node 0, so highest-id selection keeps the attack on *backups* (delay of
PREPARE/COMMIT votes), not the leader — keeping this `delay-emission`, not
`disrupt-leader`. Honest caveat to record: in **Casper FFG** the proposer
rotates by slot, so a fixed slow node is occasionally the proposer and will
delay those proposals too — an unavoidable partial overlap, reported in the
experiment page. Snowman is leaderless, so no overlap.

## 4. Components — new package `src/adversary/`

- `profiles.py` — `DelayProfile` (frozen dataclass): `nodes: tuple[int,...]`,
  `intensity: float` (f), `mult: float` (m), `kind = "delay-emission"`.
  Mirrors the [[concepts/adversary-model-runtime]] §4 sketch, trimmed to what
  delay needs.
- `inject.py` — `inject_delay(handle, slow_ids, mult, ref_by_node)`: the §3.1
  wrap. Pure, no I/O. A no-op when `slow_ids` is empty (the f=0 control path
  → byte-identical to honest; §8 invariant).
- `select.py` — `slow_node_ids(n, f) -> tuple[int,...]` = highest-id `⌊f·n⌋`.
- `config.py` — Family C constants: static-baseline timeline (constant 10 ms),
  `N_VALUES=(10,25)`, `F_VALUES=(0.0,0.10,0.20,0.30)`, `M_VALUES=(2.0,5.0,10.0)`,
  `SEEDS=range(20)`, per-protocol cadence refs, window/buffer (probe-set),
  PBFT `vc_delay` (probe-set, realistic so delay-tripped view-changes are
  observable).
- `runners.py` — `run_{pbft,ffg,snowman}(n, f, m, seed)`: build honest on the
  static-baseline timeline (the `src/delay/runners.py` pattern), then
  `inject_delay` on the slow set. Returns the `(records, result, meta)`
  triple the reducers consume. `RUNNERS` dispatch table.
- `sweep.py` — orchestrator: grid = protocols × `N_VALUES` × `F_VALUES` ×
  `M_VALUES` × seeds (with f=0 carrying no m — see §5), driven through
  `run_grid_tiered` (`is_heavy = snowman & n≥25`, `--heavy-jobs 1`); clip;
  reduce; post-grid `finality_delay_ratio` pass; write CSV. CLI:
  `--probe / --smoke / --jobs / --heavy-jobs / --fresh / --out`.

## 5. Experiment design

Two swept axes (per the human 2026-06-14 decisions):

- **Intensity** `f ∈ {0.00, 0.10, 0.20, 0.30}` — fraction of slow nodes.
  `f=0.00` is the honest **control** (0 slow nodes, no magnitude). At n=10 →
  {0,1,2,3} slow nodes; at n=25 → {0,2,5,7}. The realized fraction is
  reported (it differs slightly from the nominal at n=25 due to the floor).
- **Magnitude** `m ∈ {2, 5, 10}` — fixed delay multiple of the protocol's
  round cadence, applied per emission (Design 2: discrete points spanning the
  task's "2–10×" band, so a dose–response curve is plottable). `m` applies
  only to `f>0` cells.

Per `(protocol, n, seed)`: `1` control + `3 f × 3 m = 9` attack cells = **10
cells**. Grid = 3 protocols × 2 n × 10 × 20 seeds = **1200 runs** before any
seed cap. Snowman n=25 may be seed-capped (~8, T47 precedent) if the probe
projects an impractical wall-clock.

Per-protocol cadence reference (`ref`, the `meta.interval`):

| Protocol | `ref` on static-baseline |
| :-- | :-- |
| PBFT | propose cadence = 1.0 s |
| Snowman | slot = 1.0 s |
| Casper FFG | slot_duration = 0.1 s (default; static-baseline E[delay]=10 ms satisfies slot ≥ 4·E[delay]) |

So a slow node holds each emission by `m·ref`: PBFT/Snowman 2/5/10 s; FFG
0.2/0.5/1.0 s. The asymmetry (FFG's shorter cadence) is reported, not hidden.

## 6. Metrics & output schema

CSV = the 18-column T40 projection (via `_generic_cols` + the per-protocol
reducers, exactly as `src/delay/sweep.py`) + a Family-C annotation block:

| Column | Meaning |
| :-- | :-- |
| `adversary_strategy` | `"delay-emission"` (or `"none"` for f=0) |
| `byzantine_fraction` | nominal f |
| `slow_node_count` | realized `⌊f·n⌋` |
| `delay_mult` | m (NaN for f=0) |
| `finality_delay_ratio` | headline — see below |
| `clipped_fraction` | tail past W / in-scope (reported) |
| `run_horizon_s` | W + buffer |

**Headline `finality_delay_ratio`** (post-grid pass, mirroring
`heavy.py::_finalization_rates`): for an attack cell,
`commit_latency_ms(cell) / commit_latency_ms(control)` at the same
`(protocol, n, seed)` where the control is the `f=0` row; control rows = 1.0;
NaN if the control did not finalize. `commit_latency_ms` is the
cross-protocol-comparable column ([[concepts/output-format]] §13).

**Secondary (already in the reducers):** `success_rate`, `finalized_instances`,
`view_change_count` (PBFT — does delay trip rotation?). At `f < 1/3` liveness
is expected to hold (latency inflates, no stall); reported either way.

**Plots** (`src/output/` companion, `delay_plots.py` STYLE): (a)
`finality_delay_ratio` vs `m` at fixed f (the dose–response curve), (b) vs f
at fixed m, per protocol and n; optionally an f×m heatmap.

## 7. Calibration, window/buffer, tiered scheduler

**Probe-first** (agreed plan). `sweep.py --probe` times one cell per
`(protocol, n=10)` at the worst magnitude (`m=10`, slowest), prints
first-decision latency, clipped fraction, PBFT view-change count, and a
projected full-grid wall-clock. From the probe:
- set `WINDOW_S` so every protocol finalizes ≥ 25 in-window-started decisions
  with clipped fraction < 5 % (the T46 guard; Family C is fast so this should
  be comfortable);
- set `BUFFER_S ≥` the slowest settling (≤ `10·ref` + one honest round);
- set PBFT `vc_delay` realistic (≈ 3× honest round) so a slow backup that
  pushes a vote past it trips an *observable* view-change (the §3 invariant),
  but honest cells do not rotate;
- if projected wall-clock > ~3 h, cap Snowman n=25 seeds to ~8.

Reuse `src/delay/clip.py::clip_records` unchanged. Use `run_grid_tiered` with
`is_heavy = (proto=="snowman" and n>=25)` and `--heavy-jobs 1` so peak memory
is bounded (the agreed mitigation; the streaming reducer stays deferred).

## 8. Determinism contract

- **Fixed magnitude ⇒ deterministic shift.** `m·ref` is a constant; the wrap
  only shifts `t_sent`. No adversary RNG is consumed, so each slow node's
  protocol RNG stream is identical to honest — the node is *only late*. Same
  `(config, seed)` → byte-identical event log. (The per-node adversary RNG of
  [[concepts/adversary-model-runtime]] §5 is needed only by capabilities with
  randomized choices, e.g. T53's equivocation subset — deferred to those
  tasks.)
- **f=0 ≡ honest.** With an empty slow set `inject_delay` is a no-op, so an
  f=0 cell is byte-identical to a plain honest static-baseline run — a tested
  invariant (§9) and the validity anchor for the `finality_delay_ratio`
  denominator.
- **jobs=1 ≡ jobs=N.** Inherited from the `run_grid` per-cell determinism
  (each cell independent + seeded), as proven for T46.1.

## 9. Testing strategy (TDD)

`tests/adversary/`:
- `test_select.py` — `slow_node_ids` returns highest-id `⌊f·n⌋`; f=0 → empty;
  excludes node 0 for all f<1 at n∈{10,25} (PBFT primary protection).
- `test_inject.py` — after `inject_delay`, a slow node's emission is delivered
  exactly `m·ref` later than the same honest emission (deterministic);
  non-slow nodes are byte-identical to honest; empty slow set is a no-op.
- `test_profiles.py` — `DelayProfile` shape/immutability.
- `test_determinism.py` — same `(n,f,m,seed)` → byte-identical records over
  two runs; an f=0 cell is byte-identical to the honest baseline runner.
- `test_e2e.py` — a small `(n=4 or 7, f, m)` integration run finalizes and a
  slow-voter run has `commit_latency_ms ≥` its f=0 control (monotone sanity).
- `test_sweep.py` — `--jobs 1 ≡ --jobs 2` byte-identical on a 1-seed smoke
  grid; `finality_delay_ratio` post-pass arithmetic.

Gate: `make test` green; the existing baselines remain byte-identical (no
shared-infra edits, so this is expected and asserted).

## 10. Wiki deliverables

- **New** `wiki/experiments/2026-06-14_delayed-voters.md` — config, seeds,
  commit hash, re-run commands, raw-result location, calibration (probe
  numbers), findings paragraph, and the **Auggie verification** section
  recording the verification gap (auggie MCP unavailable → Grep/Glob
  substitute; precedent: the T41 page).
- **Revision** on [[concepts/adversary-model]] §3 — `delay-emission` now has a
  runtime realization (the bind-seam wrap); the bind-seam-vs-FSM-dispatch
  decision for the delay capability.
- **Revision** on [[concepts/adversary-model-runtime]] §4/§5 — `DelayProfile`
  implemented in `src/adversary/profiles.py`; fixed-magnitude delay needs no
  adversary RNG (the §5 per-node RNG deferred to randomized capabilities).
- **Revision** on [[concepts/node-model]] §9 — delay realized at the bound
  outbound API via post-build wrap, not FSM dispatch (pragmatic for delay).
- **Revision** on [[concepts/experiment-matrix]] §3 and
  [[concepts/experiment-matrix-runs]] §3/§4 — Family C gains `n ∈ {10,25}`
  (the approved extension), the **magnitude axis** `m ∈ {2,5,10}` for
  delay-emission (refines the matrix's "2–10×" band into a swept axis), and
  the `f=0` control point; budget bumped. Resolves the 2026-06-10 Backlog
  item naming T51.
- `wiki/index.md` + `wiki/log.md` updated.

## 11. Open questions / risks

- **Magnitude granularity.** Decision 2026-06-14: **default `{2,5,10}` (3
  points)** = 1200 runs; the probe's projected wall-clock decides whether to
  upgrade to `{2,4,6,8,10}` (5 points, 1920 runs, +60%) before the full sweep
  commits — a one-line `M_VALUES` change.
- **Snowman n=25 cost.** Bounded by the tiered scheduler; wall-clock still the
  risk → probe + seed cap.
- **Casper proposer overlap** (§3.3) — reported, not eliminated.
- **FFG cadence asymmetry** (§5) — a real finding (FFG couples to its slot),
  surfaced on the plots.

## 12. Verification (auggie gap)

The Engineer role mandates `mcp__auggie__codebase-retrieval` pre/post edit.
auggie is **unavailable** in this environment. Substitute: Grep/Glob for the
structural search (pickup-index, plan, post-edit re-query), and log each
substituted query + result in the experiment page's **Auggie verification**
section (precedent: the T41 page). This is the proof-of-verification artifact
for the task.
