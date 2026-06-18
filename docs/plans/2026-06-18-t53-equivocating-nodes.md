# T53 — Equivocating Nodes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Drive non-trivial logic with superpowers:test-driven-development. Dispatch a verification subagent at every commit boundary (per-commit verification protocol). The human commits; do not run `git commit` yourself — stage and propose the commit, the human runs it.

**Goal:** Add a Family-C `equivocate-vote` adversary across PBFT, Casper FFG, and Snowman, sweep the Byzantine fraction through and past `f=1/3`, and emit the raw safety + liveness signals that T54 will analyse.

**Architecture:** B-hybrid — Byzantine *behavior* lives in three thin adversarial node subclasses in `src/adversary/equivocate.py` (importing the honest node classes; the honest FSMs under `src/{pbft,pos,snowman}/` are never edited). Everything else — selection, profile, runners, sweep orchestrator, the cross-node safety reducer, CSV — is shared in `src/adversary/`, mirroring the T52 offline sweep. Because the behavior is in the node class, the runner's `make(node_id, …)` factory dispatches subclass-by-id; **no post-`build_run` wrap is needed**.

**Tech Stack:** Python 3 stdlib only; `unittest` per the per-suite Makefile (`make test-adversary`, `PYTHONPATH=src:tests/adversary`); the existing `common.run_grid_tiered` resumable/parallel sweep driver; the T40 reducers + `output.csv`/`output.schema`; `delay.clip` for the window clip.

**Design doc:** `docs/plans/2026-06-18-t53-equivocating-nodes-design.md` (approved 2026-06-18).

---

## Shared building blocks (reference)

- **Deterministic recipient split** (no adversary RNG): `peers = sorted(i for i in range(node.n) if i != node.id)`, `mid = len(peers)//2`, `lo = peers[:mid]`, `hi = peers[mid:]`.
- **Synthetic conflicting requests/blocks** are a pure function of the instance key, so every colluding Byzantine node derives the *same* pair independently (full collusion, no shared mutable state): PBFT `(view, seq)`, FFG/Snowman `(slot, parent)`.
- **f=0 ⇒ empty Byzantine set ⇒ pure honest run** (no subclass instantiated) ⇒ byte-identical to the honest static-baseline.
- Subclasses override only payload-emitting methods, never RNG-draw paths (Snowman sampling stays honest), so `f>0` cells are per-cell byte-identical on re-run.

---

## Task 1: Byzantine selection (`byzantine_node_ids`)

**Files:**
- Modify: `src/adversary/select.py`
- Test: `tests/adversary/test_select.py`

**Step 1 — failing test.** Append to `tests/adversary/test_select.py`:

```python
from select import byzantine_node_ids  # noqa: E402  (PYTHONPATH=src)

class TestByzantineNodeIds(unittest.TestCase):
    def test_lowest_ids_include_primary(self):
        # ⌊0.4·10⌋ = 4 lowest ids; node 0 (PBFT view-0 primary) is included.
        self.assertEqual(byzantine_node_ids(10, 0.4), (0, 1, 2, 3))

    def test_zero_is_empty(self):
        self.assertEqual(byzantine_node_ids(10, 0.0), ())

    def test_floor(self):
        self.assertEqual(byzantine_node_ids(25, 0.33), (0, 1, 2, 3, 4, 5, 6, 7))

    def test_rejects_out_of_range_f(self):
        with self.assertRaises(ValueError):
            byzantine_node_ids(10, 1.5)
```

**Step 2 — run, expect fail.** `make test-adversary` → ImportError / fail.

**Step 3 — implement.** Add to `src/adversary/select.py`:

```python
def byzantine_node_ids(n: int, f: float) -> tuple[int, ...]:
    """Return the ⌊f·n⌋ LOWEST node ids, ascending. Empty when f == 0.

    The inverse of slow_node_ids (which spares node 0): equivocation needs the
    PBFT view-0 primary (node 0) and proposer slots INSIDE the Byzantine set, so
    the adversary is the low-id prefix. (T53; adversary-model.md §5.)
    """
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"f must be in [0, 1], got {f}")
    k = math.floor(f * n)
    return tuple(range(0, k)) if k > 0 else ()
```

**Step 4 — run, expect pass.** `make test-adversary`.

**Step 5 — commit.** `feat(adversary): byzantine_node_ids low-id selection (T53)`

---

## Task 2: `EquivocateProfile`

**Files:**
- Modify: `src/adversary/profiles.py`, `src/adversary/__init__.py`
- Test: `tests/adversary/test_profiles.py`

**Step 1 — failing test.** Add a `TestEquivocateProfile` asserting the frozen dataclass carries `nodes`, `intensity`, `partition_strategy="half-half"`, `kind="equivocate-vote"`, and is hashable/frozen (assigning raises).

**Step 2 — run, expect fail.**

**Step 3 — implement.** Append to `profiles.py`:

```python
@dataclass(frozen=True)
class EquivocateProfile:
    """The ``equivocate-vote`` adversary profile for one run (T53).

    A Byzantine validator that signs two incompatible messages where the
    protocol expects one, forking the payload across a deterministic half-half
    split of its recipients. No magnitude axis (binary, like offline). The
    behaviour lives in the adversarial node subclasses (equivocate.py); this
    object is stored for observability/provenance (adversary-model.md §5).
    """
    nodes: tuple[int, ...]
    intensity: float
    partition_strategy: str = "half-half"
    kind: str = "equivocate-vote"
```

Add `EquivocateProfile` to `__init__.py` `__all__` and import.

**Step 4 — run, expect pass.**

**Step 5 — commit.** `feat(adversary): EquivocateProfile (T53)`

---

## Task 3: shared partition + conflicting-payload helpers

**Files:**
- Create: `src/adversary/equivocate.py` (helpers only this task)
- Test: `tests/adversary/test_equivocate.py` (create)

**Step 1 — failing test.** Create `tests/adversary/test_equivocate.py` with a `TestPartition`:

```python
from equivocate import split_recipients, conflicting_bytes  # PYTHONPATH=src

class _FakeNode:
    def __init__(self, n, node_id): self.n, self.id = n, node_id

class TestPartition(unittest.TestCase):
    def test_half_half_excludes_self_deterministic(self):
        lo, hi = split_recipients(_FakeNode(10, 0))
        self.assertEqual(lo, (1, 2, 3, 4))
        self.assertEqual(hi, (5, 6, 7, 8, 9))
        # pure function of (n, id): identical on re-call
        self.assertEqual((lo, hi), split_recipients(_FakeNode(10, 0)))

    def test_conflicting_bytes_distinct_and_keyed(self):
        a, b = conflicting_bytes("pbft", 0, 3)
        self.assertNotEqual(a, b)
        self.assertEqual((a, b), conflicting_bytes("pbft", 0, 3))  # deterministic
        self.assertNotEqual(a, conflicting_bytes("pbft", 0, 4)[0])  # keyed
```

**Step 2 — run, expect fail.**

**Step 3 — implement.** Create `src/adversary/equivocate.py` with the module docstring + helpers:

```python
"""The equivocate-vote adversary: three node subclasses + shared helpers (T53).

Behaviour lives here as thin subclasses of the honest node classes; the honest
FSMs under src/{pbft,pos,snowman}/ are never edited (B-hybrid, design §2). Each
subclass overrides only its payload-emitting methods to fork a conflicting
payload across a deterministic half-half split of its recipients — NO adversary
RNG, so per-cell replay is byte-identical (design §7).

Design contract: docs/plans/2026-06-18-t53-equivocating-nodes-design.md
"""
from __future__ import annotations

def split_recipients(node) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Split peers-minus-self into (lo, hi) halves; pure fn of (node.n, node.id)."""
    peers = tuple(i for i in range(node.n) if i != node.id)
    mid = len(peers) // 2
    return peers[:mid], peers[mid:]

def conflicting_bytes(tag: str, k1: int, k2: int) -> tuple[bytes, bytes]:
    """Two distinct request/tx blobs, a pure fn of the instance key, so every
    colluding Byzantine node derives the SAME pair independently."""
    return (f"EQV-A:{tag}:{k1}:{k2}".encode(),
            f"EQV-B:{tag}:{k1}:{k2}".encode())
```

**Step 4 — run, expect pass.**

**Step 5 — commit.** `feat(adversary): equivocate partition + conflicting-payload helpers (T53)`

---

## Task 4: `EquivocatingPBFTNode`

**Files:**
- Modify: `src/adversary/equivocate.py`
- Test: `tests/adversary/test_equivocate.py`

**Mechanism (design §3.1).** Override three methods; the rest of `PBFTNode` runs unchanged.
- `_propose`: as primary, send `PRE-PREPARE(reqA)` to `lo`, `PRE-PREPARE(reqB)` to `hi` (`reqA, reqB = conflicting_bytes("pbft", view, seq)`, each with its matching `digest`); self-accept `reqA`; advance `next_seq`; re-arm the propose timer.
- `_broadcast_prepare(inst, t)`: send `PREPARE(digest(reqA))` to `lo`, `PREPARE(digest(reqB))` to `hi`; self-record its own (`inst.prepares[self.id] = inst.digest`).
- `_broadcast_commit(inst, t)`: same fork for `COMMIT`.

Because the conflicting requests are keyed only on `(view, seq)`, every Byzantine node — primary or backup — derives both digests independently, so the votes manufacture two `2f+1` quorums on disjoint honest halves once `f` is large enough (the cliff appears between `f=0.33` and `f=0.40` at `n=10`; below it honest nodes split, no quorum, the view-change timer fires).

**Step 1 — failing tests** (`TestEquivocatingPBFT`):
- `test_primary_forks_pre_prepare`: build one `EquivocatingPBFTNode(id=0, n=4, workload=[b"x"])`, capture `send` calls (monkeypatch `node.send`), fire the propose timer; assert two distinct `PRE-PREPARE` payloads went to disjoint recipient sets, each with `digest(payload.request_payload) == payload.request_digest`.
- `test_backup_forks_votes`: drive a node to `_broadcast_prepare`; assert `PREPARE(digestA)`→lo, `PREPARE(digestB)`→hi.

**Step 2 — run, expect fail.**

**Step 3 — implement.** Add to `equivocate.py` (import the honest class + payloads/digest at top):

```python
from pbft import PBFTNode
from pbft.digest import digest as _pbft_digest
from pbft.messages import PrePreparePayload, PreparePayload, CommitPayload

class EquivocatingPBFTNode(PBFTNode):
    """Byzantine PBFT replica: conflicting PRE-PREPARE (as primary) + forked
    PREPARE/COMMIT votes (design §3.1). Honest PBFTNode FSM otherwise."""

    def _propose(self, t):
        if self.view_changing or not self.workload or not self._is_primary(self.view):
            return
        self.workload.pop(0)
        seq = self.next_seq
        self.next_seq += 1
        reqA, reqB = conflicting_bytes("pbft", self.view, seq)
        lo, hi = split_recipients(self)
        for dst in lo:
            self.send(dst, "PRE-PREPARE",
                      PrePreparePayload(self.view, seq, _pbft_digest(reqA), reqA), t)
        for dst in hi:
            self.send(dst, "PRE-PREPARE",
                      PrePreparePayload(self.view, seq, _pbft_digest(reqB), reqB), t)
        self._accept_pre_prepare(self.view, seq, _pbft_digest(reqA), reqA,
                                 src=self.id, t=t)
        self.set_timer("propose", self.propose_delay, None, t)

    def _broadcast_prepare(self, inst, t):
        reqA, reqB = conflicting_bytes("pbft", inst.view, inst.seq)
        lo, hi = split_recipients(self)
        for dst in lo:
            self.send(dst, "PREPARE",
                      PreparePayload(inst.view, inst.seq, _pbft_digest(reqA)), t)
        for dst in hi:
            self.send(dst, "PREPARE",
                      PreparePayload(inst.view, inst.seq, _pbft_digest(reqB)), t)
        inst.prepares[self.id] = inst.digest

    def _broadcast_commit(self, inst, t):
        reqA, reqB = conflicting_bytes("pbft", inst.view, inst.seq)
        lo, hi = split_recipients(self)
        for dst in lo:
            self.send(dst, "COMMIT",
                      CommitPayload(inst.view, inst.seq, _pbft_digest(reqA)), t)
        for dst in hi:
            self.send(dst, "COMMIT",
                      CommitPayload(inst.view, inst.seq, _pbft_digest(reqB)), t)
        inst.commits[self.id] = inst.digest
```

**Step 4 — run, expect pass.**

**Step 5 — commit.** `feat(adversary): EquivocatingPBFTNode (T53)`

---

## Task 5: `EquivocatingCasperNode`

**Files:** Modify `src/adversary/equivocate.py`; test `tests/adversary/test_equivocate.py`.

**Mechanism (design §3.2 — corrected for FFG fidelity).** Double-vote only; **both votes broadcast to ALL** (no partition, no forked proposal).
- `_attest(epoch, slot, t)`: run the honest attestation first (call `super()._attest(epoch, slot, t)` — it broadcasts the real `ATTESTATION` and self-records). Then build a **conflicting** `FFGVote` with the **same** `source_epoch`/`target_epoch` but a different `target_hash` (a fabricated 32-byte hash, e.g. `block_hash(slot=slot, parent_hash=GENESIS_HASH, proposer_idx=self.id, transactions=(b"EQV-ALT", ...))` or any value ≠ the real `target_cp.block_hash`), wrap it in an `AttestationPayload(slot, epoch, ffg=alt, attester_idx=self.id)`, and `self.broadcast("ATTESTATION", alt_payload, t)`. Both reach every honest node, so each honest `_file_ffg_vote` sees the attester's first (honest) vote as `NEW` then the second as `CONFLICT` → `casper_slashing` + `slashable_stake_fraction`.
- **No `_propose` override / no forked `BLOCK-PROPOSAL`.** *Fidelity finding:* `EpochState.links` (`src/pos/epoch.py`) aggregates by `source_epoch` only and ignores `target_hash`, so a forked checkpoint would "finalise" two checkpoints under an honest supermajority — a model artifact, not a real break. The faithful FFG signal is accountable safety (`slashable_stake_fraction`), not a fork. (The cross-node fork cliff is demonstrated by PBFT only.)
- Edge case: `super()._attest` may early-return (`checkpoint_unavailable` / `source_checkpoint_unavailable`) under delay — in that case emit no conflicting vote either (guard: only double-vote if the honest attestation was actually sent; simplest is to replicate the honest guards or detect via a captured-send flag). On the static-baseline (10 ms) timeline the guards never trip, so a straightforward `super()` call + conflicting broadcast is fine; just ensure the conflicting `target_epoch == epoch` so the recipient's `_handle_attestation` epoch-match guard passes.

**Step 1 — failing tests** (`TestEquivocatingFFG`):
- `test_double_vote_same_epoch_diff_hash`: drive `_attest`; capture broadcasts; assert two `ATTESTATION`s with equal `ffg.target_epoch` and **different** `ffg.target_hash`, both with `attester_idx == self.id`.
- `test_downstream_node_slashes`: feed both attestations (as `Message`s) into a fresh honest `CasperNode` (`_handle_attestation`); assert it emits a `casper_slashing` event and `slashable_stake_fraction() > 0`.

**Step 2 — run, expect fail.**

**Step 3 — implement.** Add `EquivocatingCasperNode(CasperNode)` importing `AttestationPayload, FFGVote` from `pos.messages`, `block_hash, GENESIS_HASH` from `pos.chain`. Override only `_attest` per the mechanism above. Do **not** override `_propose`. Do not edit `src/pos/`.

**Step 4 — run, expect pass.**

**Step 5 — commit.** `feat(adversary): EquivocatingCasperNode double-vote (T53)`

---

## Task 6: `EquivocatingSnowmanNode`

**Files:** Modify `src/adversary/equivocate.py`; test `tests/adversary/test_equivocate.py`.

**Mechanism (design §3.3).**
- `_propose(slot, t)`: as proposer, build two blocks A, B for the same `(slot, parent_id)` (distinct tx blobs from `conflicting_bytes("snow", slot, <parent int>)`); send `BLOCK-ANNOUNCEMENT(A)`→lo, `(B)`→hi; self-record A. This creates a genuine non-singleton conflict set — the only thing there is to lie about.
- `_handle_query(msg, t)`: lying responder — if the conflict set for the queried block has ≥2 members, respond with a **non-preference** member (lowest-id member ≠ `cs.preference`); else fall back to honest behaviour. No RNG.

**Step 1 — failing tests** (`TestEquivocatingSnowman`): assert `_propose` emits two distinct `BLOCK-ANNOUNCEMENT`s to disjoint subsets; assert `_handle_query` against a 2-member conflict set returns the non-preference block.

**Step 2 — run, expect fail.**

**Step 3 — implement.** Add `EquivocatingSnowmanNode(SnowmanNode)` importing `BlockAnnouncementPayload, QueryResponsePayload` from `snowman.messages`, `Block, hash_block` from `snowman.block`. Keep `_start_poll_round` (the RNG sampler) untouched.

**Step 4 — run, expect pass.**

**Step 5 — commit.** `feat(adversary): EquivocatingSnowmanNode proposer-fork + lying responder (T53)`

---

## Task 7: cross-node safety reducer (`safety.py`)

**Files:**
- Create: `src/adversary/safety.py`
- Test: `tests/adversary/test_safety.py` (create)

**Step 1 — failing test.** Given a list of `decided` `EventRecord`s (carrying `node_id` + `fields["instance_id"]` + `fields["value"]`) and a `byzantine_ids` set, `safety_signals(records, byzantine_ids)` returns a dict with:
- `safety_violation` (bool): two **honest** nodes decided different `value` for the same `instance_id`.
- `conflicting_instances` (int): count of such instances.
- `max_slashable_stake_fraction` (float): max `slashable_stake_fraction` over any `casper_slashing` event (0.0 if none).

Test cases: (a) all honest agree → `safety_violation=False`; (b) two honest decide different values for one instance → `True`, count 1; (c) only a Byzantine node disagrees → `False` (Byzantine excluded); (d) a `casper_slashing` event with `slashable_stake_fraction=0.33` → `max_slashable_stake_fraction==0.33`.

**Step 2 — run, expect fail.**

**Step 3 — implement** `src/adversary/safety.py`:

```python
"""Cross-node safety signals for the equivocate-vote sweep (T53).

A post-run reducer over the aggregated event stream. Safety is a property of
the HONEST nodes only (a Byzantine node deciding anything proves nothing), so
Byzantine node_ids are excluded before comparing decisions. Feeds T54's formal
four-invariant analysis; T53 only records the raw signals. (Design §6.)
"""
from __future__ import annotations

from event_log import EventRecord
from pos.node import CASPER_SLASHING  # the slashing event type

def safety_signals(records: list[EventRecord],
                   byzantine_ids: frozenset[int]) -> dict[str, object]:
    by_instance: dict[object, set] = {}
    max_slash = 0.0
    for r in records:
        if r.event_type == "decided" and r.node_id not in byzantine_ids:
            by_instance.setdefault(r.fields.get("instance_id"), set()).add(
                r.fields.get("value"))
        elif r.event_type == CASPER_SLASHING:
            frac = r.fields.get("slashable_stake_fraction", 0.0) or 0.0
            max_slash = max(max_slash, float(frac))
    conflicting = sum(1 for vals in by_instance.values() if len(vals) > 1)
    return {
        "safety_violation": conflicting > 0,
        "conflicting_instances": conflicting,
        "max_slashable_stake_fraction": max_slash,
    }
```

(Confirm `EventRecord` exposes `node_id`, `event_type`, `fields` — check `src/event_log/`; adjust attribute names if needed.)

**Step 4 — run, expect pass.**

**Step 5 — commit.** `feat(adversary): cross-node safety reducer (T53)`

---

## Task 8: equivocate runners + config

**Files:**
- Create: `src/adversary/equivocate_config.py`
- Modify: `src/adversary/runners.py`
- Test: `tests/adversary/test_runners.py`, `tests/adversary/test_equivocate_config.py` (create)

**Step 1 — failing tests.**
- `test_equivocate_config`: `F_VALUES` per design §5 (PBFT/FFG `(0,.10,.20,.33,.40,.50)`, Snowman `(0,.10,.20,.33)`), `N_VALUES==(10,25)`, `SEEDS==tuple(range(20))`.
- `test_runners`: `EQUIVOCATE_RUNNERS["pbft"](4, 0.0, 0)` returns a `RunTriple` byte-identical (records + result) to the honest static-baseline (f=0 ⇒ no Byzantine subclass); `EQUIVOCATE_RUNNERS["pbft"](10, 0.4, 0)` instantiates `EquivocatingPBFTNode` for ids 0–3.

**Step 2 — run, expect fail.**

**Step 3 — implement.**
- `equivocate_config.py`: mirror `offline_config.py` — reuse the shared knobs from `.config`, set `F_VALUES`/`N_VALUES`/`SEEDS`, and leave `WINDOW_S`/`BUFFER_S`/`T_MAX`/`PBFT_VC_DELAY_S`/`ONE_ROUND_S`/`SNOWMAN_QUERY_TIMEOUT_S` as **provisional** values (copy T52's) marked `# PROBE-SET in Task 10`.
- `runners.py`: add `from . import equivocate_config as ecfg`, import the three subclasses + `byzantine_node_ids`, and add `run_<proto>_equiv(n, f, seed)` mirroring the offline runners but with the **make-fn dispatching subclass-by-id**:

```python
def run_pbft_equiv(n, f, seed):
    propose = ecfg.PBFT_PROPOSE_DELAY_S
    batches = [b"".join(b) for b in _batches(seed, propose, ecfg)]
    byz = set(byzantine_node_ids(n, f))

    def make(node_id, global_seed):
        cls = EquivocatingPBFTNode if node_id in byz else PBFTNode
        workload = batches if node_id == 0 else None
        return cls(node_id=node_id, weight=1.0, endpoint=None,
                   global_seed=global_seed, n=n, workload=workload,
                   propose_delay=propose, initial_view=0,
                   vc_delay=ecfg.PBFT_VC_DELAY_S)

    meta = _meta("pbft", f"pbft-n{n}", n, seed, propose, None, ecfg)
    handle = build_run(_config(n, ecfg), seed, make)
    result, logger = run_to_completion(handle, t_max=ecfg.T_MAX)
    return logger.records, result, meta
```

Mirror for `run_ffg_equiv` (Byzantine ids → `EquivocatingCasperNode`) and `run_snowman_equiv` (Byzantine ids → `EquivocatingSnowmanNode`, honest pass `query_timeout=ecfg.SNOWMAN_QUERY_TIMEOUT_S` to all so stalls can close). Add `EQUIVOCATE_RUNNERS = {...}`.

**Step 4 — run, expect pass** (`make test-adversary`).

**Step 5 — commit.** `feat(adversary): equivocate runners + config (T53)`

---

## Task 9: sweep orchestrator (`equivocate_sweep.py`)

**Files:**
- Create: `src/adversary/equivocate_sweep.py`
- Test: `tests/adversary/test_equivocate_sweep.py` (create)

**Step 1 — failing test.** `test_smoke_one_seed`: `run_sweep(seeds=(0,))` returns rows whose count == `len(_build_cells((0,)))`; every row carries the `equivocate-vote` annotation columns + `safety_violation`/`conflicting_instances`/`max_slashable_stake_fraction`; `f=0` rows have `adversary_strategy=="none"` and `safety_violation==False`.

**Step 2 — run, expect fail.**

**Step 3 — implement.** Copy `offline_sweep.py` and change:
- output path `results/adversary/equivocating_nodes.csv`; checkpoint dir `.sweep_equivocate`.
- read `ecfg` (equivocate_config); cell is the 4-tuple `(proto, n, f, seed)`; `_build_cells` uses `ecfg.F_VALUES`.
- runner = `EQUIVOCATE_RUNNERS`.
- `_HEADLINE_COLUMNS = ("safety_violation", "conflicting_instances", "max_slashable_stake_fraction")`.
- in `_build_row`, after the generic + reducer + `_window_denominator_fix` + common-adv columns, compute `byz = frozenset(byzantine_node_ids(n, f))` and `row.update(safety_signals(records, byz))`. **Note:** pass the *unclipped* records to `safety_signals` (a safety violation anywhere in the run counts), or clipped — decide in Task 10; default to unclipped for safety, clipped for throughput.
- replace the `_throughput_ratios` post-pass with **no post-pass** (the safety signals are per-cell; keep a `throughput_ratio` post-pass too if useful for T54 — optional, mirror offline).
- `write_csv`: format the three headline columns (`safety_violation` as `"1"/"0"`, `conflicting_instances` int, `max_slashable_stake_fraction` `:.6f`).
- reuse `sweep_common` for the common adv columns + `is_heavy_snowman`.

**Step 4 — run, expect pass.** Also run `PYTHONPATH=src python3 -m adversary.equivocate_sweep --smoke` and eyeball a few rows.

**Step 5 — commit.** `feat(adversary): equivocate sweep orchestrator (T53)`

---

## Task 10: calibration probe + finalize config

**Files:** Modify `src/adversary/equivocate_config.py`; the probe lives in `equivocate_sweep.py` (`--probe`, copied from offline).

**Step 1.** Run `PYTHONPATH=src python3 -m adversary.equivocate_sweep --probe` (largest f per protocol, n∈{10,25}, seed 0). Capture per-(protocol, n): first-decision latency, clip fraction, in-window finalizations, PBFT view-change count, and whether `safety_violation` fires at the above-threshold cells.

**Step 2.** Set `WINDOW_S` ≥ the slowest finalizing first-decision; `BUFFER_S` ≥ worst single-instance finalization; `PBFT_VC_DELAY_S` small enough to fire below/at the cliff; `ONE_ROUND_S`; `SNOWMAN_QUERY_TIMEOUT_S`. Record the probe table + the reasoning in module comments (mirror `offline_config.py`'s probe block).

**Step 3.** Re-run `--probe` to confirm the finalized constants capture every finalizing cell.

**Step 4 — commit.** `chore(adversary): probe-calibrate equivocate window/buffer (T53)`

---

## Task 11: run the full sweep → dataset

**Files:** `results/adversary/equivocating_nodes.csv` (640 rows).

**Step 1.** `PYTHONPATH=src python3 -m adversary.equivocate_sweep --jobs 8 --heavy-jobs 1`. (Per the sandbox-multiprocessing memory, if `--jobs>1` hangs, fall back to `--jobs 1`, or hand the production sweep to the user's terminal.)

**Step 2 — verify dataset.** Confirm 640 rows, single `commit_hash`, `f=0` rows all `safety_violation=0`. Per-protocol expectation: **PBFT** `safety_violation=1` at/above the fork cliff (≥`f=0.40` at n=10) and `0` below; **FFG** `safety_violation=0` throughout (faithful — no forked proposal) but `max_slashable_stake_fraction ≈ f` at `f>0`, crossing 1/3 at `f≥0.33` (the accountable-safety cliff); **Snowman** `safety_violation=0` throughout (resists).

**Step 3 — re-run determinism guard.** Re-run one control + one attack cell; assert byte-identical to the committed rows (modulo `commit_hash`). Re-run the honest baseline byte-identical guard to prove the honest FSMs are untouched.

**Step 4 — commit.** `data(adversary): equivocating-nodes sweep dataset, 640 rows (T53)`

---

## Task 12: cliff-witness figure (minimal)

**Files:** Create `src/output/equivocate_plots.py` (optional, mirror `offline_plots.py`); `results/adversary/plots/safety_vs_f_n{10,25}.pdf`.

Render only the minimum to *witness* the cliff for the experiment page: `safety_violation` rate (and FFG `max_slashable_stake_fraction`) vs `f`, per `n`, all three protocols. The polished four-invariant figures + ranking are **T54** — do not build them here. (If a figure isn't needed to make the page legible, skip this task and note the deferral.)

**Commit.** `feat(output): equivocate cliff-witness plot (T53)`

---

## Task 13: wiki + docs

**Files:**
- Create: `wiki/experiments/2026-06-18_equivocating-nodes.md`
- Modify: `wiki/concepts/adversary-model.md` (`## Revisions` entry for §5), `wiki/index.md`, `wiki/log.md`

**Experiment page** (mirror the T52 page structure): subsystem/mechanism (B-hybrid subclasses, the unifying proposer-fork+voter-fork insight), config + grid, calibration table, determinism note, **descriptive findings** (per-protocol: PBFT cliff between f=0.33 and f=0.40 with view-change escalation below; FFG slashable-stake ≈ f + conflicting finalization above 1/3; Snowman safety-violation ≈ 0, resists), the figure (if built), the **Auggie verification** subsection (every query string + phase, per the Engineer role), seeds/commit/re-run commands, cost.

**adversary-model.md `## Revisions`**: the §5 `equivocate-vote` row gains a runtime realization (third `Node.adversary` fill, subclass-based not seam-wrap); record whether the §5 Snowman "no fork-induction surface" claim and the FFG accountable-safety bound held empirically.

**index.md / log.md**: add the experiment page under `## Experiments`; append the `[YYYY-MM-DD] experiment | task 53` log entry.

**Commit.** `wiki: T53 equivocating-nodes experiment page + adversary-model revision`

---

## Task 14: verification + flip to In Review

**Step 1.** `make test` — every suite green (record counts).
**Step 2.** Invoke `superpowers:verification-before-completion`.
**Step 3.** Post-edit auggie re-query (`mcp__auggie__codebase-retrieval`) describing the new `equivocate.py`/`safety.py`/runners and confirming the honest FSMs + `inject.py` are unchanged; log the query strings into the experiment page's Auggie verification subsection.
**Step 4.** Check the `## Backlog` for any T53 follow-up clause addressed/deferred; note in the handoff.
**Step 5.** Flip `T53` to `[?]` In Review in `TASKS.md` and recompute the Dashboard counts. **Do not** mark Completed (human only). Stage everything and propose the commit `task 53: simulate equivocating nodes (Family C equivocate-vote)`; the human commits and merges.

**Handoff summary to the human:** files touched, wiki pages added/updated, the per-protocol cliff findings, determinism evidence, and that T54 is unblocked to consume `results/adversary/equivocating_nodes.csv`.

---

## Notes / risks

- **PBFT cliff arithmetic** (n=10): Byzantine help pushes each honest half to `2f+1` only once `byz ≥ 4` (`f=0.40`), so the safety break first appears at `f=0.40`, not `f=0.33` — the probe must confirm this. If it doesn't appear, check the half-half split sizes and that Byzantine backups fork *both* PREPARE and COMMIT.
- **FFG has no representable cross-node fork** in this simulator: `EpochState.links` ignores `target_hash` (`src/pos/epoch.py`), so the faithful FFG signal is `max_slashable_stake_fraction` (double-vote detection, fires reliably when both votes are broadcast to all), **not** a forked finalization. FFG `safety_violation` is expected to stay 0; that is correct, not a bug. Document this fidelity boundary on the experiment page and as an `adversary-model.md` §5 Revision.
- **Sandbox multiprocessing** (memory `project_sweep_multiprocessing_sandbox`): `--jobs>1` may deadlock in-sandbox; default the in-sandbox run to `--jobs 1` or hand the full sweep to the user's terminal.
- **`head` is shadowed** in this shell (memory): use `sed -n`/`tail`/`awk` to inspect CSV rows, not `head`.
- **EventRecord attribute names**: verify `node_id`/`event_type`/`fields` against `src/event_log/` before relying on them in `safety.py`.
