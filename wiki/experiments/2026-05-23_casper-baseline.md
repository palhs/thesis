# Casper FFG baseline — T32

End-to-end run of the **simplified Casper FFG honest-path core** across
the W3 stack: the discrete-event scheduler ([[concepts/simulation-design]],
T21), the shared-layer `Node` ([[concepts/node-model]], T22), the honest
`Network` (T23), the event-log subsystem (T24), and the config/factory
layer (T27), driven by a `CasperNode` validator (`src/pos/`). Not a
protocol experiment — a build-verification baseline. It confirms the
two-round justify→finalise gadget composes across the stack: every epoch
reaches `casper_finalised`, `decided` fires in epoch order, and two
seed-identical runs produce byte-identical event streams.

The implementation is Approach 1 ([[algorithms/pos]]): inline round-robin
proposer (`slot mod n`) and inline two-thirds-stake finality. Slashing
detection and LMD-GHOST fork choice are out of scope (deferred to T18/T53
and T46–T50 respectively); stake-weighted proposer selection (T33) and the
extracted finality module (T34) extend the same code.

## Configuration

- Code under test: `src/pos/` on branch `task/T32-pos-consensus`. T32
  modified no upstream `src/` — only `src/pos/` and its tests, plus the
  additive `Makefile` `SUITES` row and the new integration test. Commit
  hash `TODO(human)` — assigned when the branch is committed (T32 lands as
  one human commit per `docs/workflow.md`).
- `global_seed = 42`; `slot_duration = 1.0`; `slots_per_epoch = 2`;
  `attest_offset = 1` (the constructor default — the mid-epoch slot, so
  the checkpoint block has time to propagate before validators attest).
- Network: a single phase `[0, ∞)`, constant delay `1e-9`, drop rate 0,
  no partitions. The delay is `1e-9` rather than literal zero because the
  network model enforces `t_delivered > t_sent`; `1e-9` is the minimum.
- `t_max = 20.0`. Casper FFG has no quiescence — the slot timer re-arms
  every slot indefinitely — so the run is bounded by `t_max` only. With
  `slot_duration = 1.0` and `slots_per_epoch = 2`, epoch `e` finalises
  once epoch `e+1` is justified, which requires reaching at least slot
  `3·slots_per_epoch + attest_offset = 7`; `t_max = 20.0` covers ≈ 10
  slots and finalises epochs 1 through 8.

### Scenarios

- **n=4, uniform stake.** `stake_table = {i: 3.0 for i in range(4)}`;
  `total_stake = 12`; supermajority `≥ 2/3` ⇒ `≥ 8`. Three peer
  attestations plus the node's own self-vote clear the threshold.
- **n=7, uniform stake.** `stake_table = {i: 3.0 for i in range(7)}`;
  `total_stake = 21`; supermajority `≥ 14`.
- **n=4, non-uniform stake.** `stake_table = {0: 5.0, 1: 4.0, 2: 2.0,
  3: 1.0}`; `total_stake = 12`; supermajority `≥ 8`. Justification is on
  stake, not head-count: any pair of `{0, 1}` already clears the
  threshold; node 3 alone is far below it.

## Re-run

```
PYTHONPATH=src:tests/integration python3 -m unittest test_casper_baseline -v
PYTHONPATH=src:tests/pos python3 -m unittest discover -s tests/pos -v
```

The first command runs the 7-test T32 integration suite (n=4, n=7, and the
non-uniform-stake scenario); the second runs the 49-test `src/pos/` unit
suite. Results are observed through the in-test `EventLogger` — no CSV is
persisted (CSV export is T40 work).

## Result

The T32 integration suite runs 7 tests to green; the `src/pos/` unit
suite 49. Upstream suites are unaffected — scheduler 46, nodes 46, network
62, event_log 30, config 39, pbft 130, integration 60 (unchanged from the
T31 baseline). The full `make test` run is green (462 tests).

| Event | n=4 uniform | n=7 uniform | n=4 non-uniform |
| :-- | --: | --: | --: |
| `stopped_by` | deadline | deadline | deadline |
| `casper_block_accepted` | 77 | 133 | 77 |
| `casper_attested` | 36 | 63 | 36 |
| `casper_justified` | 36 | 63 | 36 |
| `casper_finalised` | 32 | 56 | 32 |
| `decided` | 32 | 56 | 32 |
| `casper_rejected` | 0 | 0 | 0 |

- **n=4 uniform.** The run advances to `t = 20.0` (deadline stop;
  Casper has no quiescence). Across 10 slot fires every node accepts the
  proposer's block (`77 = 8 epochs × 8 checkpoint-and-non-checkpoint
  acceptances ≈ slots × n`), attests once per epoch from each node
  (`36 = 9 epochs × 4`), and the FFG gadget produces a justification per
  attesting node per epoch (`36`) plus a finalisation per epoch per node
  (`32 = 8 finalised epochs × 4`). The `decided` count matches
  `casper_finalised` per Decision G (one `decided` per `(node, epoch)` —
  Casper finalises *epochs*, so each node emits one `decided` per
  finalised epoch). Zero rejections — every proposed block validates and
  every attestation lands within the validator set.
- **n=7 uniform.** Scaled up: more blocks accepted per slot (each peer
  receives a delivery), more attestations per epoch (`63 = 9 × 7`),
  more `decided` events (`56 = 8 × 7`). The protocol scales without any
  rejection or stall.
- **n=4 non-uniform.** Event counts are identical to the n=4 uniform
  case — under the honest-path baseline, every validator attests once per
  epoch regardless of stake, every link sums to `total_stake`, and the
  supermajority test passes the same way. The non-uniform run is the
  build-verification that `total_stake` (Decision D, the constructor sum)
  is wired correctly and that `EpochState.link_stake` weights each vote
  by `stake_table[attester_idx]` rather than head-count.
- **Determinism.** Two seed-identical runs at n=4 (and at n=7) produce
  byte-identical event-record streams (455 records at n=4, identical
  across re-runs). T32 draws no randomness — the proposer schedule is
  `slot mod n` and the FFG aggregation is order-stable — so determinism
  is structural, not statistical.

## Observation

The two-round justify→finalise gadget composes across the W3 stack: a
`CasperNode` proposer builds a block extending `chain.head` on its slot
fire, every node accepts the block, every node files its own FFG vote at
its epoch's attestation slot (Decision C — `Network.broadcast` excludes
the sender, so the proposer and the attester each self-record before
broadcasting), and the FFG transitions justify the target on a
supermajority link from an already-justified source and finalise the
source when the target is its direct child. Genesis (epoch 0) is
justified+finalised at construction (Decision F) and bootstraps the
justify chain: epoch 1 forms a `<0,1>` link, justifying epoch 1; epoch 2
forms a `<1,2>` link, justifying epoch 2 and finalising epoch 1; and so
on.

Casper has no quiescence — unlike PBFT, which drains its workload and
stops — so every run is `t_max`-bounded. `config.factory.build_run` does
not pipe `Config.t_max` into `scheduler.run()`; the integration test
passes it explicitly through `handle.scheduler.run(t_max=t_max)`. A
future task that wires `Config.t_max` end-to-end would let
`build_run`-driven runs stop at the configured deadline without the
caller threading the argument.

The non-uniform-stake scenario does not stress the supermajority
arithmetic at this scale: every validator attests every epoch, so every
link sums to `total_stake` and the threshold is met identically to the
uniform case. The stake-weighting check that pins this is the unit test
`test_non_uniform_stake_justifies_on_stake` (a single attestation from
the stake-9 node justifies; head-count alone would not). The end-to-end
*adversarial* setting where a subset of stake is withheld is T18/T53
work.

## Back-links

- [[algorithms/pos]] — the protocol implemented: epochs of slot-proposed
  blocks, FFG `<source, target>` votes, the two-round justify→finalise
  gadget, the `2/3` supermajority on stake.
- [[concepts/system-design-protocols]] — the §3 Casper main-loop sketch;
  see its `## Revisions` for the T32 divergences (one attestation per
  epoch instead of per slot; no fork-choice object).
- [[concepts/message-types]] — the `BLOCK-PROPOSAL` / `ATTESTATION` rows;
  see its `## Revisions` for the omitted `head_vote_hash` and signature
  fields.
- [[concepts/node-model]] — the shared-layer `Node` the `CasperNode`
  subclasses; the `broadcast` / `set_timer` / `emit` API and the
  `decided` event contract; §4 FSM mapping table for Casper.
- [[concepts/simulation-design]] — the discrete-event scheduler and the
  six-phase bootstrap; the `t_max` deadline-stop branch the Casper run
  exercises.
