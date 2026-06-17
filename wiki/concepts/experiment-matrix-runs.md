# Experiment Matrix — Run Catalog

Companion to [[concepts/experiment-matrix]] (T19). The parent page owns
the **design** — axes, run families, per-RQ mapping, policies. This page
owns the **enumerated catalog**: the concrete network-timeline parameter
tables (§2), the adversary triple tables (§3), and the run-count budget
(§4). Split per `docs/wiki-spec.md` § Page size; precedent
[[concepts/network-model]] / [[concepts/network-model-phases]].

Read the parent page first; this page assumes its axes and run families
(A — Scaling, B — Delay, C — Adversarial) as given.

## 1. Conventions

- Timelines and triples here are the values loaded into the experiment
  YAML (schema owned by T27, [[concepts/reproducibility]]).
- Delay-distribution `kind` / `params` follow the catalogue of
  [[concepts/network-model-phases]] §2; drop and partition follow §3 / §4
  of that page.
- Adversary `(adversary_id, protocol_id, f)` triples follow
  [[concepts/adversary-model-runtime]] §2 for the intensity unit.
- All delays are in milliseconds of simulator model time.

## 2. Network timeline catalog

A timeline is a contiguous phase sequence ([[concepts/network-model-phases]]
§5). Each entry below is one `network_phase_id` value. `E[delay]` is the
mean of the phase's delay distribution — the quantity the FFG coherence
rule ([[concepts/experiment-matrix]] §5) keys on.

| `network_phase_id` | Phases | Delay distribution | `p_drop` | Partition | `E[delay]` | Used by |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| `static-baseline` | one, `[0, ∞)` | `constant`, `delay = 10` | 0 | none | 10 ms | Family A; Family C; RQ1 `constant` point |
| `delay-uniform` | one, `[0, ∞)` | `uniform`, `low = 100, high = 500` | 0 | none | 300 ms | Family B (T46 moderate) |
| `delay-exponential` | one, `[0, ∞)` | `exponential`, `mean = 300` | 0 | none | 300 ms | Family B (RQ1 memoryless-tail point) |
| `delay-heavy-tail` | one, `[0, ∞)` | `heavy_tail`, `scale, shape` set so the 1–5 s band carries the mass | 0 | none | ≈ 3 s | Family B (T47 heavy delay) |
| `delay-heavy-tail-loss` | one, `[0, ∞)` | as `delay-heavy-tail` | `∈ {0.05, 0.10, 0.20}` | none | ≈ 3 s | Family B (T47 loss sub-sweep) |
| `partial-sync-gst` | two: async `[0, GST)`, partial-sync `[GST, ∞)` | async: `heavy_tail`; post-GST: `uniform`, `low = 50, high = 250` | 0 | async phase: one sustained partition; healed at GST | post-GST ≈ 150 ms | Family B (synchrony-model stress) |

The `delay-heavy-tail-loss` row is a single timeline run three times,
once per `p_drop` value — that is the T47 "5–20% loss" sub-sweep.
`partial-sync-gst` is the timeline that exercises the partial-synchrony
assumption faithfully ([[concepts/synchrony-models]]): the partition and
heavy-tail delay before GST suspend finality, and the protocols are
expected to recover after the healed boundary.

### FFG `slot_duration` pairing

Per [[concepts/experiment-matrix]] §5, every FFG run requires
`slot_duration ≥ 4 · E[delay]`. The FFG `slot_duration` therefore
rescales per timeline (the analogue of Snowman `K`-rescaling per `n`):

| `network_phase_id` | `E[delay]` | FFG `slot_duration` | Regime |
| :-- | :-- | :-- | :-- |
| `static-baseline` | 10 ms | **100 ms** (calibration default) | coherent at default |
| `delay-uniform` | 300 ms | **1 200 ms** | rescaled |
| `delay-exponential` | 300 ms | **1 200 ms** | rescaled |
| `delay-heavy-tail` | ≈ 3 s | **12 000 ms** | rescaled (≈ Ethereum production slot) |
| `delay-heavy-tail-loss` | ≈ 3 s | **12 000 ms** | rescaled |
| `partial-sync-gst` | post-GST ≈ 150 ms | **1 000 ms** | rescaled; keyed to the post-GST regime where FFG is expected to finalise |

For `partial-sync-gst` the rule is applied to the *post-GST* `E[delay]`:
the pre-GST async phase is, by the partial-synchrony contract, a regime
where FFG is not expected to finalise, so it does not constrain the slot
choice. These `slot_duration` values extend the
`{50, 100, 500} ms` sensitivity sweep of
[[concepts/metric-reconciliation]] § Calibration defaults upward; the
"(or larger)" clause of its FFG coherence constraint authorises the
extension.

## 3. Adversary run catalog

Family C ([[concepts/experiment-matrix]] §3) draws `(adversary_id,
protocol_id, f)` triples from the generic capabilities of
[[concepts/adversary-model]] §§3–5. The intensity unit of `f` is
per-protocol ([[concepts/adversary-model-runtime]] §2): replicas for
PBFT and Narwhal+Tusk, stake for Casper FFG, validators for Snowman.

| Capability (catalog §) | Task | Protocols | Intensity grid `f` |
| :-- | :-- | :-- | :-- |
| `delay-emission` (§3) | T51 — delayed voters | PBFT, Casper FFG, Snowman, Narwhal+Tusk | `{0.10, 0.20, 0.30}` |
| `withhold-participation` (§4) | T52 — non-participating validators | PBFT, Casper FFG, Snowman, Narwhal+Tusk | `{0.10, 0.20, 0.33}` |
| `equivocate-vote` (§5) | T53 — equivocating nodes | PBFT, Casper FFG, Snowman, Narwhal+Tusk | `{0.10, 0.20, 0.33}`; **PBFT and Casper FFG additionally `{0.40, 0.50}`** |

That is **12 `(adversary, protocol)` pairs**. The above-threshold
`f ∈ {0.40, 0.50}` points exist only for PBFT and Casper FFG: T53 and
T54 require runs past `f > 1/3` to expose the safety cliff that
[[concepts/adversary-model]] §5 / §7.3 documents (PBFT routes
equivocation through view change; Casper FFG's accountable-safety
slashing becomes observable only above threshold). Snowman and
Narwhal+Tusk cannot fork below threshold and are not swept above it
here.

Each `(adversary, protocol, f)` triple runs on the `static-baseline`
network at `n = 10` (Family C fixed axes). The Snowman `β ∈ {3, 5}`
RQ4-only safety sweep ([[concepts/metric-reconciliation]] § Calibration
defaults) applies to every Snowman triple, so Snowman safety becomes
empirically observable; those rows carry `β ≠ 15` and are excluded from
cross-protocol throughput tables.

### Uncovered catalog surfaces

[[concepts/adversary-model]] defines 18 valid pairs; the 12 above leave
**6 uncovered**, with no Week-10 experiment task:

| Uncovered surface | Catalog § | Pairs |
| :-- | :-- | :-- |
| `disrupt-leader` | §6 | PBFT, Casper FFG, Narwhal+Tusk (Snowman `N/A`) — 3 |
| Snowman colluding sub-sampler | §7.1 | 1 |
| Narwhal+Tusk data-availability withholding | §7.2 | 1 |
| Casper FFG slashable-equivocation refinements | §7.3 | 1 |

Resolution is a human roadmap decision recorded in `TASKS.md` § Backlog
— see [[concepts/experiment-matrix]] §8. This catalog enumerates only
the covered 12.

## 4. Combinatorial budget

A planning estimate of the run volume the Week 8–10 tasks must execute,
at `n_runs = 20` (30 for near-threshold Family C points).

| Family | Cells | Seeds | Subtotal |
| :-- | :-- | :-- | :-- |
| **A — Scaling** baseline | 4 protocols × 5 `n` − 1 (Snowman `n=4` excluded) = 19 | 20 | 380 |
| A — RQ3 knob sweep | FFG `slots_per_epoch` (+3) and Narwhal `r` (+2) extra settings × 5 `n` | 20 | ≈ 500 |
| **B — Delay** | 4 protocols × 6 timelines = 24, + heavy-tail-loss 2 extra `p_drop` × 4 | 20 | ≈ 640 |
| **C — Adversarial** | 12 triples × 3 intensity points + PBFT/FFG above-threshold (2 × 2) | 20 / 30 | ≈ 800 |
| C — Snowman `β` RQ4 sweep | Snowman in 3 capabilities × 3 intensity × 1 extra `β` | 20 | ≈ 360 |

Total ≈ **2 700 runs**, exclusive of the peak-throughput offered-load
ramps (each ramp is itself 7 rate-steps × `W = 10 s`, run within
Families A and C). The estimate is for capacity planning only — the
authoritative cell list is the experiment YAML (T27).

## 5. Sources

Enumerated catalog; no primary-literature citations of its own. Values
trace to the parent page and its sources.

**Parent page:**

- [[concepts/experiment-matrix]] (T19) — the design contract this
  catalog instantiates: axes, run families, per-RQ mapping, FFG
  coherence rule, workload and seed policies.

**Inbound (existing wiki pages):**

- [[concepts/network-model-phases]] — delay-distribution catalogue,
  drop model, partition expression, phase timeline rules realised in §2.
- [[concepts/adversary-model]] / [[concepts/adversary-model-runtime]] —
  the capability catalog and per-protocol intensity unit instantiated
  in §3.
- [[concepts/metric-reconciliation]] — calibration defaults and the FFG
  coherence constraint the §2 pairing table extends; the Snowman `β`
  RQ4-only regime.
- [[concepts/synchrony-models]] — the GST narrative the
  `partial-sync-gst` timeline realises.

**Forward references (sibling pages, not yet authored):**

- [[concepts/reproducibility]] (T27) — the experiment YAML schema and
  loader that consume this catalog.
- [[concepts/output-format]] (T40) — the CSV whose `network_phase_id`
  column references §2.

## Revisions

### [2026-06-10] T46 — Family B n-axis doubling + the two T46 timelines

Human decision 2026-06-10 (Week 9) extends Family B from the fixed `n = 10`
of the §4 budget to **`n ∈ {10, 25}`** (recorded as the §3 Revision on
[[concepts/experiment-matrix]]). This doubles the Family B run volume on the
`n` axis. Evidence + the realised first two timelines:
[[experiments/2026-06-10_delay-moderate]].

**Family B budget, restated for `n ∈ {10, 25}`.** Each of the six §2
timelines now runs at two sizes:

| Sub-family | Cells | Seeds | Subtotal |
| :-- | :-- | :-- | :-- |
| 6 timelines × 3 protocols × 2 `n` | 36 | 20 | 720 |
| heavy-tail-loss extra `p_drop` (2) × 3 protocols × 2 `n` | 12 | 20 | 240 |

So Family B is now ≈ **960 runs** (was ≈ 640 at fixed `n = 10`) — the §4
total moves from ≈ 2 700 to ≈ **3 000 runs**. (Narwhal+Tusk stays out of the
delay sweep until T38.1; the counts above are the three in-scope protocols.)

**T46 lands 2 of the 6 timelines** at both sizes: `delay-uniform` +
`delay-exponential` × 3 protocols × `n ∈ {10, 25}` × 20 seeds = **240 runs**
(`results/delay/delay.csv`). The remaining four timelines (heavy-tail, loss,
partial-sync-gst) are T47. Both T46 timelines have `E[delay] = 300 ms`, so
the §2 FFG-slot pairing gives `slot_duration = 1200 ms` for each.

**Family C (adversarial, T51–T56) stays at `n = 10`.** This n-axis
amendment is Family-B-only; the symmetric Family-C-at-`n=25` extension
(which would roughly double the largest family) is a separate human roadmap
decision parked in `TASKS.md` Backlog (2026-06-10) and is **not** folded
into this budget.

### [2026-06-14] T51 — Family C extended to `n ∈ {10,25}` + a swept magnitude axis (supersedes the n=10 freeze above)

Human decisions (2026-06-14 / 2026-06-15) resolve the parked roadmap item: Family
C now runs at **`n ∈ {10, 25}`** and adds a **magnitude axis `m ∈ {2,4,6,8,10}`**
to the `delay-emission` intensity grid, with `f ∈ {0,0.10,0.20,0.30}` (`f=0` =
honest control). The §3 design rationale is on [[concepts/experiment-matrix]]
§Revisions.

**Family C `delay-emission` budget (T51).** 3 protocols × 2 `n` ×
(1 control + 3 `f` × 5 `m` = 16 cells) × 20 seeds = **1920 runs**
(`results/adversary/delayed_voters.csv`). No seed cap was needed — Family C runs
on the fast static-baseline (10 ms) network, so even the heaviest Snowman `n=25`
cell is ~900k events (≈40 s wall), unlike the multi-GB T47 heavy-tail cells; the
tiered scheduler ran the Snowman `n=25` tier at `--heavy-jobs 4`.

**Budget impact.** This adds the 1920-run `delay-emission` block (T52 withhold /
T53 equivocate will add comparable blocks on the same axes). The §4 grand total
above (≈ 3000 runs, the three in-scope protocols) is correspondingly larger; the
Family C portion is no longer the single-`n`, single-magnitude sketch the §4
budget assumed. Evidence: [[experiments/2026-06-14_delayed-voters]].
