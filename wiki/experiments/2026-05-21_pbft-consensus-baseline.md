# PBFT consensus baseline — T29

End-to-end run of the **full PBFT three-phase commit** across the W3
stack: the discrete-event scheduler ([[concepts/simulation-design]], T21),
the shared-layer `Node` ([[concepts/node-model]], T22), the honest
`Network` (T23), the event-log subsystem (T24), and the config/factory
layer (T27), driven by a `PBFTNode` validator. It extends the T28
pre-prepare baseline ([[experiments/2026-05-21_pbft-proposal-baseline]]):
T29 wires the `PREPARE`/`COMMIT` voting phases, commit/finalization, and
the `VIEW-CHANGE` → `NEW-VIEW` recovery path. Not a protocol experiment —
a build-verification baseline. It confirms the three-phase commit reaches
`decided` across the stack and that view-change recovers a stalled
instance without a safety break.

## Configuration

- Code under test: `src/pbft/` on branch `task/T29-pbft-voting`. T29
  modified no upstream `src/` — only `src/pbft/` and its tests. Commit
  hash `TODO(human)` — assigned when the branch is committed (T29 lands as
  one human commit per `docs/workflow.md`).
- `global_seed = 42`; `initial_view = 0`; `propose_delay = 1.0`.

### Scenario A — honest full commit

- `n = 4` (`3f+1`, `f = 1`) and `n = 7` (`f = 2`), run separately;
  workload `[b"X"]` placed on node 0 only.
- Network: a single phase `[0, ∞)`, constant delay `1e-9`, drop rate 0, no
  partitions. The delay is `1e-9` rather than literal zero because the
  network model enforces `t_delivered > t_sent`; `1e-9` is the minimum.
- `vc_delay = 1000.0` — generous, so no instance's view-change timer fires
  before its commit quorum forms.

### Scenario B — view-change under delay

- `n = 4`; workload `[b"X"]` on node 0.
- Network: a single phase `[0, ∞)`, **constant delay `D = 1.0`**, drop 0.
- `vc_delay = 1.9`, satisfying `D < vc_delay < 2·D` (T29 design spec
  §10.2). View 0's timer (`vc_delay·2^0 = 1.9`) fires before the view-0
  commit quorum forms; view 1's doubled timer (`2·vc_delay = 3.8`)
  comfortably outlasts the view-1 commit. The clean single-recovery band
  is `vc_delay ∈ [1.8, 1.95]`; `1.9` sits mid-band.
- `t_max = 50.0` — a safety bound only; the healthy run quiesces at
  `t = 9.7`.

## Re-run

```
PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_consensus -v
PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v
```

The first command runs the 11-test T29 integration suite (Scenario A at
`n = 4` and `n = 7`, Scenario B); the second runs the 71-test `src/pbft/`
unit suite. Results are observed through the in-test `EventLogger` — no
CSV is persisted (CSV export is T40 work).

## Result

The T29 integration suite runs 11 tests to green; the `src/pbft/` unit
suite 71. Upstream suites are unaffected — event_log 30, network 62,
scheduler 46, nodes 46, config 39 (unchanged from the T28 baseline).

| Metric | A, `n=4` | A, `n=7` | B, `n=4` |
| :-- | --: | --: | --: |
| `stopped_by` | quiescence | quiescence | quiescence |
| `pbft_pre_prepared` | 4 | 7 | 8 |
| `pbft_prepared` | 4 | 7 | 8 |
| `pbft_committed` | 4 | 7 | 4 |
| `decided` | 4 | 7 | 4 |
| `pbft_view_change` | 0 | 0 | 4 |
| `pbft_new_view` | 0 | 0 | 4 |
| `pbft_rejected` | 0 | 0 | 0 |
| `PRE-PREPARE` deliveries | 3 | 6 | 3 |
| `PREPARE` deliveries | 12 | 42 | 24 |
| `COMMIT` deliveries | 12 | 42 | 24 |
| `VIEW-CHANGE` deliveries | 0 | 0 | 12 |
| `NEW-VIEW` deliveries | 0 | 0 | 3 |
| `events_processed` | 29 | 92 | 72 |
| `events_tombstoned` | 4 | 7 | 8 |

- **Scenario A.** Every node reaches `pre_prepared → prepared → committed`
  for `(view 0, seq 0)` and emits `decided` — `n` of each event. Zero
  rejections, zero view-changes. The decided value is `blake2b(b"X")` for
  every node. Two seed-identical runs produce byte-identical event-record
  streams.
- **Scenario B.** Every node's view-0 view-change timer fires (`t = 2.9`
  for the primary, `t = 3.9` for the others) before the view-0 commit
  quorum forms at `t = 4.0` — so all four nodes nonetheless commit
  `(view 0, seq 0)` and emit `decided` (a *spurious* view-change), then
  initiate a `VIEW-CHANGE` toward view 1. Node 1, the view-1 primary,
  collects `2f+1 = 3` `VIEW-CHANGE`s and broadcasts a `NEW-VIEW` reissuing
  `(view 1, seq 0)`; all four nodes enter view 1 (`pbft_new_view = 4`) and
  re-run the three-phase commit there. The view-1 instances reach
  `COMMITTED` but do not re-emit `pbft_committed` / `decided`: Decision G
  records `decided` once per `seq`. The decided value is `blake2b(b"X")` —
  view-change does not break safety. The run quiesces at `t = 9.7`;
  determinism holds byte-identically. The escalation timer is not
  exercised (the `NEW-VIEW` always arrives in time) — by design (T29 spec
  §10.3).

## Observation

The full three-phase commit composes across the W3 stack: a `PBFTNode`
primary drains its workload, and every replica votes `PREPARE` then
`COMMIT` on the uniform `2f+1` quorum (Decision B — each replica, the
primary included, self-records its own vote because `Network.broadcast`
excludes the sender), reaching `decided`. View-change recovers a stalled
instance: when an instance's per-view timer fires before its commit
quorum, the replica drives the `VIEW-CHANGE` → `NEW-VIEW` → reissue path,
and the per-view exponential backoff (`vc_delay·2^view`, Decision F)
guarantees a later view's timer is long enough to let the commit finish —
so recovery terminates. Scenario B is the "spurious view change under
delay variance" phenomenon [[algorithms/pbft]] describes: the honest
primary's request commits in view 0 anyway, just after the timer fired.

`events_tombstoned` stays far below `events_processed` in every scenario
(4/29, 7/92, 8/72): each node's view-change timer, armed on `PRE_PREPARED`
and cancelled on `COMMITTED`, leaves one lazy heap tombstone (the
[[concepts/simulation-design]] D4 cancellation model). At this scale the
tombstone fraction is small, so no heap compaction is warranted — the
threshold flagged in the standing `TASKS.md` Backlog note ("Scheduler heap
growth under high timer churn", compact when `tombstone_count >
heap/2`) is not approached. Scenario A's virtual clock advances to
`t ≈ 1001` because each cancelled view-change timer's tombstone sits on
the heap at its original fire time (`vc_delay·2^0 ≈ 1000`) and is popped
then skipped; this is cosmetic — the run reaches quiescence with the
protocol work complete near `t ≈ 1`.

## Back-links

- [[algorithms/pbft]] — the protocol implemented: three-phase commit, the
  `2f+1` quorum-intersection safety argument, view-change as liveness
  recovery, spurious view-change under delay variance.
- [[concepts/message-types]] — the `PREPARE` / `COMMIT` / `VIEW-CHANGE` /
  `NEW-VIEW` rows; see its `## Revisions` for the 4-tuple evidence change.
- [[concepts/system-design-protocols]] — the §2 PBFT main-loop sketch;
  see its `## Revisions` for the T29 divergences.
- [[concepts/node-model]] — the shared-layer `Node` the `PBFTNode`
  subclasses; the `broadcast` / `set_timer` / `cancel_timer` / `emit`
  API and the `decided` event contract.
- [[concepts/simulation-design]] — the discrete-event scheduler, the
  six-phase bootstrap, and the D4 lazy-tombstone timer-cancellation model.
- [[experiments/2026-05-21_pbft-proposal-baseline]] — the T28 pre-prepare
  baseline this run extends.
