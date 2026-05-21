# T29 — PBFT Voting, Commit, and View-Change Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the T28 pre-prepare-only `src/pbft/` package into the full
classical PBFT validator — `PREPARE`/`COMMIT` voting, commit/finalization,
and `VIEW-CHANGE`→`NEW-VIEW` recovery.

**Architecture:** Per-`(view, seq)` `Instance` FSM with `2f+1` quorum
collection (uniform model — every replica including the primary votes and
self-records). A per-instance view-change timer with per-view exponential
backoff arms on `PRE_PREPARED`, cancels on `COMMITTED`; on fire it drives
the `VIEW-CHANGE`→`NEW-VIEW`→reissue recovery path. Design spec:
`docs/superpowers/specs/2026-05-21-t29-pbft-voting-design.md` — read it
before starting; this plan references its sections for implementation code.

**Tech Stack:** Python 3, stdlib `unittest`, discrete-event simulator
(`src/scheduler`, `src/nodes`, `src/network`, `src/event_log`, `src/config`).

**Test commands:**
- Unit (one test): `PYTHONPATH=src:tests/pbft python3 -m unittest <module>.<Class>.<test> -v`
- Unit (pbft suite): `PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v`
- Integration: `PYTHONPATH=src:tests/integration python3 -m unittest <module> -v`
- Full repo: run each suite dir (`tests/pbft`, `tests/integration`, `tests/scheduler`, `tests/nodes`, `tests/network`, `tests/event_log`, `tests/config`).

**Commits:** Per `docs/workflow.md`, the entire T29 work lands as **one
human-authored commit** (`task 29: <description>`) at the In-Review flip —
plus the `task 29: start` status-flip commit already pending. This plan
therefore has **no per-task `git commit` steps**; the agent does not run
`git commit` (the human commits). Task 15 is the single commit/handoff
checkpoint.

**Regression watch:** Two T28 tests encode behaviour T29 deliberately
changes — they are updated in-plan (Task 7 and Task 12), not left to break:
- `tests/pbft/test_node_validation.py::TestOnMessageDispatch::test_known_but_unwired_types_silently_no_op`
  — T28's silent no-op for `PREPARE`/`COMMIT`/`VIEW-CHANGE`/`NEW-VIEW` is
  gone (those types are now wired).
- `tests/integration/test_pbft_proposal.py::TestScenarioA_n4::test_no_voting_messages_emitted`
  — the pre-prepare phase now emits `PREPARE`/`COMMIT`.

---

## Task 1: `messages.py` — self-contained `VIEW-CHANGE` evidence

Spec §4, Decision E. `ViewChangePayload.prepared` carries the request
payload so the new primary can reissue without having prepared the
instance itself.

**Files:**
- Modify: `src/pbft/messages.py` (the `ViewChangePayload` dataclass)
- Test: `tests/pbft/test_messages.py`

**Step 1: Write the failing test**

Add to `tests/pbft/test_messages.py`:

```python
def test_view_change_payload_prepared_holds_four_tuples(self):
    from pbft.messages import ViewChangePayload
    vc = ViewChangePayload(
        new_view=1, last_stable_seq=-1,
        prepared=[(0, 0, b"d" * 32, b"REQ")])
    self.assertEqual(vc.prepared[0], (0, 0, b"d" * 32, b"REQ"))
    self.assertEqual(vc.new_view, 1)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_messages -v`
Expected: the new test FAILs (or the existing 3-tuple comment is stale) —
confirm the assertion exercises a 4-tuple.

**Step 3: Implement**

In `src/pbft/messages.py`, change `ViewChangePayload.prepared` type to
`list[tuple[int, int, bytes, bytes]]` and update the field comment to
`(view, seq, request_digest, request_payload)`. No other class changes.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_messages -v`
Expected: PASS, all `test_messages` tests green.

---

## Task 2: `instance.py` — `request_payload` field + matching helpers

Spec §5. `Instance` stores the payload (for evidence) and counts
digest-matching votes.

**Files:**
- Modify: `src/pbft/instance.py`
- Test: `tests/pbft/test_instance.py`

**Step 1: Write the failing tests**

Add to `tests/pbft/test_instance.py`:

```python
def test_request_payload_defaults_none(self):
    from pbft.instance import Instance
    self.assertIsNone(Instance(view=0, seq=0).request_payload)

def test_matching_prepares_counts_only_digest_matches(self):
    from pbft.instance import Instance
    inst = Instance(view=0, seq=0)
    inst.digest = b"A" * 32
    inst.prepares = {0: b"A" * 32, 1: b"A" * 32, 2: b"B" * 32}
    self.assertEqual(inst.matching_prepares(), 2)

def test_matching_is_zero_while_digest_none(self):
    from pbft.instance import Instance
    inst = Instance(view=0, seq=0)
    inst.prepares = {0: b"A" * 32}
    self.assertEqual(inst.matching_prepares(), 0)
    self.assertEqual(inst.matching_commits(), 0)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_instance -v`
Expected: FAIL — `request_payload` / `matching_prepares` not defined.

**Step 3: Implement**

In `src/pbft/instance.py` add the `request_payload: Optional[bytes] = None`
field and the `matching_prepares()` / `matching_commits()` methods exactly
as in spec §5.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_instance -v`
Expected: PASS.

---

## Task 3: `viewchange.py` — `collect_evidence`

Spec §8. Pure function: all instances at state ≥ `PREPARED` as
`(view, seq, digest, payload)` 4-tuples, sorted.

**Files:**
- Create: `src/pbft/viewchange.py`
- Test: `tests/pbft/test_viewchange.py` (new)

**Step 1: Write the failing test**

Create `tests/pbft/test_viewchange.py`:

```python
import unittest
from pbft.instance import Instance, InstanceState
from pbft.viewchange import collect_evidence


def _inst(view, seq, state, digest=b"d" * 32, payload=b"REQ"):
    i = Instance(view=view, seq=seq)
    i.state = state
    i.digest = digest
    i.request_payload = payload
    return i


class TestCollectEvidence(unittest.TestCase):
    def test_includes_prepared_and_committed_only(self):
        inst = {
            (0, 0): _inst(0, 0, InstanceState.IDLE),
            (0, 1): _inst(0, 1, InstanceState.PRE_PREPARED),
            (0, 2): _inst(0, 2, InstanceState.PREPARED),
            (0, 3): _inst(0, 3, InstanceState.COMMITTED),
        }
        ev = collect_evidence(inst)
        self.assertEqual([(v, s) for v, s, _, _ in ev], [(0, 2), (0, 3)])

    def test_tuple_shape_and_sort(self):
        inst = {
            (1, 0): _inst(1, 0, InstanceState.PREPARED, b"x" * 32, b"X"),
            (0, 0): _inst(0, 0, InstanceState.PREPARED, b"y" * 32, b"Y"),
        }
        ev = collect_evidence(inst)
        self.assertEqual(ev[0], (0, 0, b"y" * 32, b"Y"))
        self.assertEqual(ev[1], (1, 0, b"x" * 32, b"X"))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_viewchange -v`
Expected: FAIL — `pbft.viewchange` does not exist.

**Step 3: Implement**

Create `src/pbft/viewchange.py` with a module docstring referencing
T29 spec §8, and implement `collect_evidence(inst)` per spec §8: iterate
`inst.values()`, keep `state in (PREPARED, COMMITTED)`, emit
`(view, seq, digest, request_payload)`, return sorted by `(view, seq)`.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_viewchange -v`
Expected: PASS.

---

## Task 4: `viewchange.py` — `compute_reissue`

Spec §8. Union evidence across proofs; per `seq` pick the highest-view
tuple; stamp `new_view`.

**Files:**
- Modify: `src/pbft/viewchange.py`
- Test: `tests/pbft/test_viewchange.py`

**Step 1: Write the failing test**

Add to `tests/pbft/test_viewchange.py`:

```python
from pbft.messages import ViewChangePayload, PrePreparePayload
from pbft.viewchange import compute_reissue


class TestComputeReissue(unittest.TestCase):
    def test_unions_and_stamps_new_view(self):
        p1 = ViewChangePayload(2, -1, [(0, 0, b"a" * 32, b"A")])
        p2 = ViewChangePayload(2, -1, [(0, 1, b"b" * 32, b"B")])
        out = compute_reissue([p1, p2], new_view=2)
        self.assertEqual([pp.seq for pp in out], [0, 1])
        self.assertTrue(all(isinstance(pp, PrePreparePayload) for pp in out))
        self.assertTrue(all(pp.view == 2 for pp in out))

    def test_picks_highest_view_per_seq(self):
        p1 = ViewChangePayload(2, -1, [(0, 0, b"old" * 11 + b"o", b"OLD")])
        p2 = ViewChangePayload(2, -1, [(1, 0, b"new" * 11 + b"n", b"NEW")])
        out = compute_reissue([p1, p2], new_view=2)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].request_payload, b"NEW")
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_viewchange -v`
Expected: FAIL — `compute_reissue` not defined.

**Step 3: Implement**

Add `compute_reissue(proofs, new_view)` to `src/pbft/viewchange.py` per
spec §8: collect every `(view, seq, digest, payload)` across
`proofs[*].prepared`; for each distinct `seq` keep the tuple with the
largest `view`; return `PrePreparePayload(view=new_view, seq=seq,
request_digest=digest, request_payload=payload)` sorted by `seq`.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_viewchange -v`
Expected: PASS.

---

## Task 5: `node.py` — constructor extension + event constants

Spec §6.1, §7.9. Add `vc_delay`, view-change cross-instance state, the
new event constants, and `__init__.py` exports.

**Files:**
- Modify: `src/pbft/node.py` (constructor, module-level constants)
- Modify: `src/pbft/__init__.py`
- Test: `tests/pbft/test_node_voting.py` (new)

**Step 1: Write the failing test**

Create `tests/pbft/test_node_voting.py` with a `_node` helper accepting
`vc_delay` and an initial constructor test:

```python
import unittest
from typing import Any
from nodes import Message
from nodes.lifecycle import Lifecycle
from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import PreparePayload, CommitPayload, PrePreparePayload
from pbft import node as pbft_node
from pbft.node import PBFTNode


def _node(node_id, n, *, view=0, vc_delay=10.0):
    return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                    global_seed=42, n=n, workload=None,
                    propose_delay=1.0, initial_view=view, vc_delay=vc_delay)


def _capturers(node):
    emitted, broadcasts, timers, cancels = [], [], [], []
    node.emit = lambda et, f, t: emitted.append((et, f, t))
    node.broadcast = lambda ty, p, t: broadcasts.append((ty, p, t))
    node.send = lambda d, ty, p, t: None
    node.set_timer = lambda tid, dl, p, t: timers.append((tid, dl, p, t))
    node.cancel_timer = lambda tid: cancels.append(tid)
    return emitted, broadcasts, timers, cancels


def _kickoff(node):
    node.status = Lifecycle.RUNNING


class TestConstructor(unittest.TestCase):
    def test_vc_delay_stored_and_validated(self):
        self.assertEqual(_node(0, 4, vc_delay=2.5).vc_delay, 2.5)
        with self.assertRaises(ValueError):
            _node(0, 4, vc_delay=0.0)

    def test_view_change_state_initialised(self):
        n = _node(1, 4)
        self.assertEqual(n._view_changes, {})
        self.assertEqual(n._decided_seqs, set())

    def test_event_constants_exist(self):
        for name in ("PBFT_PREPARED", "PBFT_COMMITTED",
                     "PBFT_VIEW_CHANGE", "PBFT_NEW_VIEW"):
            self.assertTrue(hasattr(pbft_node, name))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_voting -v`
Expected: FAIL — `vc_delay` keyword unknown / constants missing.

**Step 3: Implement**

In `src/pbft/node.py`: add the `PBFT_PREPARED`, `PBFT_COMMITTED`,
`PBFT_VIEW_CHANGE`, `PBFT_NEW_VIEW` module constants (spec §7.9); extend
`__init__` with the keyword-only `vc_delay` param + positivity check and
the view-change cross-instance state, all per spec §6.1. In
`src/pbft/__init__.py` export the four new constants and (forward) the
`viewchange` helpers `collect_evidence` / `compute_reissue`.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_voting -v`
Expected: PASS. Also run the full `tests/pbft` suite to confirm T28 tests
still pass (constructor change is additive — `vc_delay` has a default).

---

## Task 6: `node.py` — view-change timer wrappers

Spec §7.1 (`_arm_view_change_timer`, `_cancel_view_change_timer`). Pure
`set_timer`/`cancel_timer` wrappers with the per-view backoff delay.

**Files:**
- Modify: `src/pbft/node.py`
- Test: `tests/pbft/test_node_viewchange.py` (new)

**Step 1: Write the failing test**

Create `tests/pbft/test_node_viewchange.py` reusing the `_node` /
`_capturers` / `_kickoff` idiom (import them or redefine locally), then:

```python
class TestViewChangeTimer(unittest.TestCase):
    def test_arm_uses_per_view_exponential_backoff(self):
        n = _node(0, 4, vc_delay=2.0)
        _, _, timers, _ = _capturers(n)
        n._arm_view_change_timer(view=0, seq=0, t=1.0)
        n._arm_view_change_timer(view=1, seq=0, t=1.0)
        self.assertEqual(timers[0], (("view_change", 0, 0), 2.0, (0, 0), 1.0))
        self.assertEqual(timers[1], (("view_change", 1, 0), 4.0, (1, 0), 1.0))

    def test_cancel_targets_the_instance_timer(self):
        n = _node(0, 4)
        _, _, _, cancels = _capturers(n)
        n._cancel_view_change_timer(0, 2)
        self.assertEqual(cancels, [("view_change", 0, 2)])
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_viewchange -v`
Expected: FAIL — methods not defined.

**Step 3: Implement**

Add `_arm_view_change_timer` and `_cancel_view_change_timer` to `PBFTNode`
exactly as spec §7.1.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_viewchange -v`
Expected: PASS.

---

## Task 7: `node.py` — PREPARE phase

Spec §6.2 (dispatch), §6.3 (extended `_accept_pre_prepare`), §6.4. On
`PRE_PREPARED` a node broadcasts `PREPARE`, self-records, arms the
view-change timer; `2f+1` matching `PREPARE`s → `PREPARED`.

**Files:**
- Modify: `src/pbft/node.py`
- Modify: `tests/pbft/test_node_validation.py` (regression — see Step 5)
- Test: `tests/pbft/test_node_voting.py`

**Step 1: Write the failing tests**

Add to `tests/pbft/test_node_voting.py`:

```python
def _pre_prepare(src, view, seq, batch):
    pp = PrePreparePayload(view=view, seq=seq,
                           request_digest=digest(batch), request_payload=batch)
    return Message(src=src, dst=1, type="PRE-PREPARE", payload=pp, t_sent=0.0)

def _prepare(src, view, seq, batch):
    pp = PreparePayload(view=view, seq=seq, request_digest=digest(batch))
    return Message(src=src, dst=1, type="PREPARE", payload=pp, t_sent=0.0)


class TestPreparePhase(unittest.TestCase):
    def test_pre_prepared_broadcasts_prepare_and_self_records(self):
        n = _node(1, 4)                       # primary view0 = node0
        emitted, broadcasts, timers, _ = _capturers(n)
        _kickoff(n)
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=5.0)
        kinds = [b[0] for b in broadcasts]
        self.assertIn("PREPARE", kinds)
        self.assertEqual(n.inst[(0, 0)].prepares[1], digest(b"A"))
        self.assertTrue(any(tid[0] == "view_change" for tid, *_ in timers))

    def test_quorum_of_prepares_transitions_to_prepared(self):
        n = _node(1, 4)                       # f=1, 2f+1=3
        emitted, broadcasts, *_ = _capturers(n)
        _kickoff(n)
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=5.0)   # self-prepare = 1
        n.on_message(_prepare(2, 0, 0, b"A"), t=5.1)       # = 2
        self.assertIs(n.inst[(0, 0)].state, InstanceState.PRE_PREPARED)
        n.on_message(_prepare(3, 0, 0, b"A"), t=5.2)       # = 3 -> PREPARED
        self.assertIs(n.inst[(0, 0)].state, InstanceState.PREPARED)
        self.assertIn("COMMIT", [b[0] for b in broadcasts])
        self.assertIn(pbft_node.PBFT_PREPARED, [e[0] for e in emitted])

    def test_prepare_before_pre_prepare_is_buffered(self):
        n = _node(1, 4)
        _capturers(n); _kickoff(n)
        n.on_message(_prepare(2, 0, 0, b"A"), t=5.0)        # arrives early
        n.on_message(_prepare(3, 0, 0, b"A"), t=5.1)
        self.assertIs(n.inst[(0, 0)].state, InstanceState.IDLE)
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=5.2)    # now digest known
        self.assertIs(n.inst[(0, 0)].state, InstanceState.PREPARED)

    def test_digest_mismatched_prepare_does_not_count(self):
        n = _node(1, 4)
        _capturers(n); _kickoff(n)
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=5.0)
        n.on_message(_prepare(2, 0, 0, b"B"), t=5.1)        # wrong digest
        n.on_message(_prepare(3, 0, 0, b"B"), t=5.2)
        self.assertIs(n.inst[(0, 0)].state, InstanceState.PRE_PREPARED)

    def test_malformed_prepare_payload_rejected(self):
        n = _node(1, 4)
        emitted, *_ = _capturers(n); _kickoff(n)
        n.on_message(Message(src=2, dst=1, type="PREPARE",
                             payload=None, t_sent=0.0), t=5.0)
        self.assertEqual([e for e in emitted if e[0] == pbft_node.PBFT_REJECTED]
                         [0][1]["reason"], "malformed_payload")
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_voting.TestPreparePhase -v`
Expected: FAIL — PREPARE unhandled / `_accept_pre_prepare` arity.

**Step 3: Implement**

In `src/pbft/node.py`: extend `_on_message` dispatch (spec §6.2, with the
payload-shape guard); extend `_accept_pre_prepare` to the new signature
`(view, seq, d, payload, src, t)` and body (spec §6.3) — update its two
existing callers (`_handle_pre_prepare`, `_propose`) to pass the payload;
add `_broadcast_prepare`, `_handle_prepare`, `_check_prepare_quorum`,
`_accept_prepare` (spec §6.4). `_accept_prepare` calls a
`_broadcast_commit` / `_check_commit_quorum` that do not exist yet — add
**minimal stubs** for them now (`_broadcast_commit`: broadcast + self-record;
`_check_commit_quorum`: `pass`) so the prepare-phase tests run; Task 8
completes them.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_voting -v`
Expected: PASS.

**Step 5: Fix the T28 regression**

`tests/pbft/test_node_validation.py::TestOnMessageDispatch::test_known_but_unwired_types_silently_no_op`
asserts `PREPARE`/`COMMIT`/`VIEW-CHANGE`/`NEW-VIEW` with `payload=None`
emit nothing — no longer true. Rewrite that test method to assert each
now emits a `pbft_rejected` with `reason="malformed_payload"` (they carry
`payload=None`). Keep `test_unknown_type_rejects` unchanged. Run:
`PYTHONPATH=src:tests/pbft python3 -m unittest test_node_validation -v`
Expected: PASS.

---

## Task 8: `node.py` — COMMIT phase + finalization

Spec §6.5, Decision G. `2f+1` matching `COMMIT`s → `COMMITTED`, cancel the
view-change timer, emit `pbft_committed` + `decided` once per `seq`.

**Files:**
- Modify: `src/pbft/node.py`
- Test: `tests/pbft/test_node_voting.py`

**Step 1: Write the failing tests**

Add to `tests/pbft/test_node_voting.py`:

```python
def _commit(src, view, seq, batch):
    cp = CommitPayload(view=view, seq=seq, request_digest=digest(batch))
    return Message(src=src, dst=1, type="COMMIT", payload=cp, t_sent=0.0)


class TestCommitPhase(unittest.TestCase):
    def _drive_to_prepared(self, n):
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=1.0)
        n.on_message(_prepare(2, 0, 0, b"A"), t=1.1)
        n.on_message(_prepare(3, 0, 0, b"A"), t=1.2)        # -> PREPARED, self-commit

    def test_quorum_of_commits_finalizes(self):
        n = _node(1, 4)
        emitted, _, _, cancels = _capturers(n); _kickoff(n)
        self._drive_to_prepared(n)                          # self-commit = 1
        n.on_message(_commit(2, 0, 0, b"A"), t=1.3)         # = 2
        n.on_message(_commit(3, 0, 0, b"A"), t=1.4)         # = 3 -> COMMITTED
        self.assertIs(n.inst[(0, 0)].state, InstanceState.COMMITTED)
        kinds = [e[0] for e in emitted]
        self.assertIn(pbft_node.PBFT_COMMITTED, kinds)
        self.assertIn("decided", kinds)
        self.assertIn(("view_change", 0, 0), cancels)

    def test_decided_value_is_request_digest(self):
        n = _node(1, 4)
        emitted, *_ = _capturers(n); _kickoff(n)
        self._drive_to_prepared(n)
        n.on_message(_commit(2, 0, 0, b"A"), t=1.3)
        n.on_message(_commit(3, 0, 0, b"A"), t=1.4)
        dec = [e for e in emitted if e[0] == "decided"][0]
        self.assertEqual(dec[1]["value"], digest(b"A").hex())
        self.assertEqual(dec[1]["instance_id"], (0, 0))

    def test_decided_emitted_once_per_seq(self):
        # An extra COMMIT after COMMITTED must not re-emit decided.
        n = _node(1, 4)
        emitted, *_ = _capturers(n); _kickoff(n)
        self._drive_to_prepared(n)
        n.on_message(_commit(2, 0, 0, b"A"), t=1.3)
        n.on_message(_commit(3, 0, 0, b"A"), t=1.4)
        n.on_message(_commit(0, 0, 0, b"A"), t=1.5)
        self.assertEqual(sum(1 for e in emitted if e[0] == "decided"), 1)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_voting.TestCommitPhase -v`
Expected: FAIL — commit never reaches `COMMITTED` (stub).

**Step 3: Implement**

Replace the Task-7 stubs: implement `_broadcast_commit`, `_handle_commit`,
`_check_commit_quorum`, `_accept_commit` per spec §6.5 (uses
`_decided_seqs`, `_emit_decided`, `_cancel_view_change_timer`).

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_voting -v`
Expected: PASS — full `test_node_voting` green.

---

## Task 9: `node.py` — view-change initiation

Spec §7.1 (`_on_view_change_timeout`), §7.2 (`_initiate_view_change`),
§7.4 (`_handle_view_change` + `f+1` catch-up). Timer dispatch for
`("view_change", v, s)`.

**Files:**
- Modify: `src/pbft/node.py`
- Test: `tests/pbft/test_node_viewchange.py`

**Step 1: Write the failing tests**

Add to `tests/pbft/test_node_viewchange.py` (import `PrePreparePayload`,
`ViewChangePayload`, `digest`, and the `pbft_node` module):

```python
class TestViewChangeInitiation(unittest.TestCase):
    def _pre_prepared(self, n, seq=0):
        pp = PrePreparePayload(0, seq, digest(b"A"), b"A")
        n.on_message(Message(src=0, dst=n.id, type="PRE-PREPARE",
                             payload=pp, t_sent=0.0), t=1.0)

    def test_timer_fire_on_stalled_instance_initiates(self):
        n = _node(1, 4, vc_delay=2.0)
        emitted, broadcasts, *_ = _capturers(n); _kickoff(n)
        self._pre_prepared(n)                               # PRE_PREPARED, stalled
        n.on_timer(("view_change", 0, 0), (0, 0), t=9.0)
        self.assertTrue(n.view_changing)
        self.assertIn("VIEW-CHANGE", [b[0] for b in broadcasts])
        self.assertIn(pbft_node.PBFT_VIEW_CHANGE, [e[0] for e in emitted])

    def test_timer_fire_on_committed_instance_is_noop(self):
        n = _node(1, 4)
        _capturers(n); _kickoff(n)
        self._pre_prepared(n)
        n.inst[(0, 0)].state = InstanceState.COMMITTED
        n.on_timer(("view_change", 0, 0), (0, 0), t=9.0)
        self.assertFalse(n.view_changing)

    def test_initiate_is_idempotent(self):
        n = _node(1, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        self._pre_prepared(n)
        n.on_timer(("view_change", 0, 0), (0, 0), t=9.0)
        n.on_timer(("view_change", 0, 0), (0, 0), t=9.1)
        self.assertEqual(sum(1 for b in broadcasts if b[0] == "VIEW-CHANGE"), 1)

    def test_f_plus_one_view_changes_trigger_catch_up(self):
        # n=4, f=1: f+1=2 VIEW-CHANGEs for view 1 make a lagging node join.
        n = _node(2, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        for src in (0, 1):
            vc = ViewChangePayload(new_view=1, last_stable_seq=-1, prepared=[])
            n.on_message(Message(src=src, dst=2, type="VIEW-CHANGE",
                                 payload=vc, t_sent=0.0), t=5.0)
        self.assertTrue(n.view_changing)
        self.assertIn("VIEW-CHANGE", [b[0] for b in broadcasts])
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_viewchange.TestViewChangeInitiation -v`
Expected: FAIL.

**Step 3: Implement**

In `src/pbft/node.py`: extend `_on_timer` dispatch for the
`("view_change", ...)` tuple (spec §6.2); add `_on_view_change_timeout`
(§7.1), `_initiate_view_change` (§7.2), `_handle_view_change` (§7.4), and
`_on_message` dispatch for `VIEW-CHANGE`. `_initiate_view_change` calls
`_arm_escalation_timer` and `_check_new_view_quorum` — add **minimal
stubs** (`pass`) for both; Tasks 10–11 complete them.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_viewchange -v`
Expected: PASS.

---

## Task 10: `node.py` — `NEW-VIEW` issuance and view entry

Spec §7.5 (`_check_new_view_quorum`, `_send_new_view`), §7.6
(`_handle_new_view`), §7.7 (`_enter_new_view`), §7.8 (propose guard).

**Files:**
- Modify: `src/pbft/node.py`
- Test: `tests/pbft/test_node_viewchange.py`

**Step 1: Write the failing tests**

Add to `tests/pbft/test_node_viewchange.py`:

```python
class TestNewView(unittest.TestCase):
    def _vc(self, new_view, prepared=()):
        return ViewChangePayload(new_view=new_view, last_stable_seq=-1,
                                 prepared=list(prepared))

    def test_new_primary_issues_new_view_on_quorum(self):
        # new_view=1 -> primary = node 1. Feed 2f+1=3 VIEW-CHANGEs.
        n = _node(1, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        for src in (0, 2, 3):
            n.on_message(Message(src=src, dst=1, type="VIEW-CHANGE",
                                 payload=self._vc(1), t_sent=0.0), t=5.0)
        self.assertIn("NEW-VIEW", [b[0] for b in broadcasts])
        self.assertEqual(n.view, 1)            # primary self-enters

    def test_new_view_recipient_advances_view(self):
        n = _node(2, 4)
        _capturers(n); _kickoff(n)
        nv = NewViewPayload(new_view=1,
                            vc_proofs=[self._vc(1), self._vc(1), self._vc(1)],
                            reissued=[])
        n.on_message(Message(src=1, dst=2, type="NEW-VIEW",
                             payload=nv, t_sent=0.0), t=6.0)
        self.assertEqual(n.view, 1)
        self.assertFalse(n.view_changing)

    def test_new_view_reissue_installs_and_resumes(self):
        n = _node(2, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        reissued = [PrePreparePayload(1, 0, digest(b"A"), b"A")]
        nv = NewViewPayload(1, [self._vc(1)] * 3, reissued)
        n.on_message(Message(src=1, dst=2, type="NEW-VIEW",
                             payload=nv, t_sent=0.0), t=6.0)
        self.assertIs(n.inst[(1, 0)].state, InstanceState.PRE_PREPARED)
        self.assertIn("PREPARE", [b[0] for b in broadcasts])

    def test_new_view_rejections(self):
        n = _node(2, 4)
        emitted, *_ = _capturers(n); _kickoff(n)
        bad = NewViewPayload(1, [self._vc(1)], [])           # < 2f+1 proofs
        n.on_message(Message(src=1, dst=2, type="NEW-VIEW",
                             payload=bad, t_sent=0.0), t=6.0)
        reasons = [e[1]["reason"] for e in emitted
                   if e[0] == pbft_node.PBFT_REJECTED]
        self.assertIn("insufficient_proofs", reasons)

    def test_propose_quiescent_while_view_changing(self):
        n = _node(0, 4)                        # node 0 is primary view 0
        n.workload = [b"A"]
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        n.view_changing = True
        n._propose(t=1.0)
        self.assertEqual(broadcasts, [])
```

(Import `NewViewPayload` at the top of the test module.)

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_viewchange.TestNewView -v`
Expected: FAIL.

**Step 3: Implement**

Replace the Task-9 `_check_new_view_quorum` stub with the real method
(spec §7.5); add `_send_new_view` (§7.5), `_handle_new_view` (§7.6),
`_enter_new_view` (§7.7), `_on_message` dispatch for `NEW-VIEW`; add the
`if self.view_changing: return` guard at the top of `_propose` (§7.8).

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_viewchange -v`
Expected: PASS.

---

## Task 11: `node.py` — escalation timer

Spec §7.3. If no `NEW-VIEW` arrives, escalate to the next view.

**Files:**
- Modify: `src/pbft/node.py`
- Test: `tests/pbft/test_node_viewchange.py`

**Step 1: Write the failing tests**

Add to `tests/pbft/test_node_viewchange.py`:

```python
class TestEscalation(unittest.TestCase):
    def test_initiating_view_change_arms_escalation_timer(self):
        n = _node(1, 4, vc_delay=2.0)
        _, _, timers, _ = _capturers(n); _kickoff(n)
        n._initiate_view_change(1, t=5.0)
        self.assertIn(("vc_escalate", 1),
                      [tid for tid, *_ in timers])

    def test_escalation_fires_when_no_new_view(self):
        n = _node(1, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        n._initiate_view_change(1, t=5.0)
        n.on_timer(("vc_escalate", 1), 1, t=99.0)            # NEW-VIEW never came
        self.assertGreaterEqual(n._target_view, 2)

    def test_escalation_noop_after_new_view_installed(self):
        n = _node(1, 4)
        _capturers(n); _kickoff(n)
        n._initiate_view_change(1, t=5.0)
        n._new_view_installed.add(1)
        before = n._target_view
        n.on_timer(("vc_escalate", 1), 1, t=99.0)
        self.assertEqual(n._target_view, before)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_viewchange.TestEscalation -v`
Expected: FAIL.

**Step 3: Implement**

Replace the Task-9 `_arm_escalation_timer` stub with the real method;
add `_on_escalation_timeout`; extend `_on_timer` dispatch for the
`("vc_escalate", ...)` tuple — all per spec §7.3. Cancel the escalation
timer inside `_enter_new_view` (already specified in §7.7 — confirm it is
present).

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v`
Expected: PASS — the entire `tests/pbft` suite green.

---

## Task 12: Integration — Scenario A (honest full commit)

Spec §10.2 Scenario A. Full three-phase commit across the W3 stack, no
view-change.

**Files:**
- Create: `tests/integration/test_pbft_consensus.py`
- Modify: `tests/integration/test_pbft_proposal.py` (regression — Step 5)

**Step 1: Write the failing test**

Create `tests/integration/test_pbft_consensus.py`. Model the harness on
`tests/integration/test_pbft_proposal.py` (`_config`, `_factory`, `_run`,
`_count_event`) but the factory must pass `vc_delay` (generous default so
no view-change). Scenario A — n=4 and n=7, single phase, minimal delay,
zero drop, workload `[b"X"]` on node 0:

```python
class TestScenarioA_n4(unittest.TestCase):
    def test_every_node_decides_seq0(self):
        logger, result = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(_count_event(logger.records, "pbft_committed"), 4)
        self.assertEqual(_count_event(logger.records, "decided"), 4)

    def test_no_rejections_or_view_changes(self):
        logger, _ = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, "pbft_rejected"), 0)
        self.assertEqual(_count_event(logger.records, "pbft_view_change"), 0)

    def test_decided_value_matches_request(self):
        logger, _ = _run(n=4, workload_for=self._workload_for)
        from pbft import digest
        for r in logger.records:
            if r.event_type == "decided":
                self.assertEqual(r.fields["value"], digest(b"X").hex())

    def test_determinism(self):
        a, _ = _run(n=4, workload_for=self._workload_for, global_seed=42)
        b, _ = _run(n=4, workload_for=self._workload_for, global_seed=42)
        self.assertEqual(list(a.records), list(b.records))
```

Add the analogous `TestScenarioA_n7` (assert counts of 7).

**Step 2: Run test to verify it fails / passes**

Run: `PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_consensus -v`
Expected: with Tasks 1–11 done, the protocol code exists — this test
should PASS once the harness is correct. If it FAILs, debug per
`superpowers:systematic-debugging` (do not weaken assertions).

**Step 3: (implementation already complete)**

No `src/` change — Scenario A exercises code from Tasks 1–11. If a genuine
bug surfaces, fix it in `src/pbft/` with a matching unit test added to
`tests/pbft/`.

**Step 4: Re-run to confirm green**

Run: `PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_consensus -v`
Expected: PASS.

**Step 5: Fix the T28 regression**

`tests/integration/test_pbft_proposal.py::TestScenarioA_n4::test_no_voting_messages_emitted`
asserts zero `PREPARE`/`COMMIT` deliveries — false once voting is wired.
Remove that one test method (its invariant was T28-skeleton-only;
`test_pbft_consensus.py` now covers the post-T29 behaviour). Leave the
rest of `test_pbft_proposal.py` intact (pre-prepare counts, digests,
determinism, quiescence still hold). Run:
`PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_proposal -v`
Expected: PASS.

---

## Task 13: Integration — Scenario B (view-change under delay)

Spec §10.2 Scenario B. A delay regime where view 0's timer fires before
its commit quorum but view 1's (doubled) does not — exercises the full
recovery path.

**Files:**
- Modify: `tests/integration/test_pbft_consensus.py`

**Step 1: Write the test (assertions fixed; constants tuned)**

Add `TestScenarioB_viewchange` — n=4, workload `[b"X"]` on node 0.
Choose a constant network delay `D` and `vc_delay` with
`D < vc_delay < 2·D` (spec §10.2). Start from `D = 1.0`, `vc_delay = 1.5`,
`propose_delay = 1.0`; the run needs `t_max` large enough to finish.
Assertions:

```python
def test_view_change_occurs_and_request_still_decided(self):
    logger, result = _run_b()
    self.assertGreaterEqual(_count_msg_type(logger.records, "VIEW-CHANGE"), 1)
    self.assertGreaterEqual(_count_msg_type(logger.records, "NEW-VIEW"), 1)
    self.assertGreaterEqual(_count_event(logger.records, "decided"), 1)
    from pbft import digest
    for r in logger.records:
        if r.event_type == "decided":
            self.assertEqual(r.fields["value"], digest(b"X").hex())

def test_all_nodes_reach_view_1(self):
    # assert via pbft_new_view events that every node entered view 1
    logger, _ = _run_b()
    entered = {r.fields["new_view"] for r in logger.records
               if r.event_type == "pbft_new_view"}
    self.assertIn(1, entered)

def test_determinism(self):
    a, _ = _run_b(); b, _ = _run_b()
    self.assertEqual(list(a.records), list(b.records))
```

**Step 2: Run test**

Run: `PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_consensus.TestScenarioB_viewchange -v`
Expected: initially may FAIL on the timing constants.

**Step 3: Tune the constants**

If view 0 never view-changes (timer too long) or never commits at all
(escalates forever), adjust `D` / `vc_delay` within `D < vc_delay < 2·D`
and re-run. Confirm exactly the recovery path runs: a `VIEW-CHANGE`, a
`NEW-VIEW`, and a final `decided`. Do **not** weaken the assertions to
pass — tune the scenario. If the network model applies phase/delay at a
boundary that defeats the regime, fall back to the spec §10.2 note and
record the working constants in the test docstring.

**Step 4: Re-run to confirm green**

Run: `PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_consensus -v`
Expected: PASS — Scenarios A and B both green.

---

## Task 14: Experiment page + wiki updates

Spec §11, §12.

**Files:**
- Create: `wiki/experiments/2026-05-21_pbft-consensus-baseline.md`
- Modify: `wiki/index.md`
- Modify: `wiki/log.md`
- Modify: `wiki/concepts/message-types.md` (add `## Revisions` entry)
- Modify: `wiki/concepts/system-design-protocols.md` (add `## Revisions` entry, if warranted)

**Step 1: Write the experiment page**

Create `wiki/experiments/2026-05-21_pbft-consensus-baseline.md` following
the T28 template (`2026-05-21_pbft-proposal-baseline.md`): config for both
scenarios (`n`, workload, `propose_delay`, `vc_delay`, network phases,
`global_seed`), re-run commands, per-scenario event counts (filled from
the actual test output), determinism confirmation, and a one-paragraph
observation per spec §11 — including the `events_tombstoned` vs
`events_processed` figure from a Scenario B `RunResult`.

**Step 2: Update `wiki/index.md`**

Add under `## Experiments`:
`- [[experiments/2026-05-21_pbft-consensus-baseline]] — T29 build-verification baseline: ...`
(one-line summary in the established style).

**Step 3: Append to `wiki/log.md`**

Append one entry per `docs/wiki-spec.md` § Log format:
`## [2026-05-21] code | task 29 — implement PBFT voting, commit, and view-change`,
role Engineer, touched file list, 1–3 sentence note.

**Step 4: Add the `## Revisions` entries**

- `wiki/concepts/message-types.md` — `## Revisions` entry: `VIEW-CHANGE`
  `prepared_evidence` is a 4-tuple `(view, seq, digest, request_payload)`
  (spec Decision E), and T29 applies no evidence-size cap (Decision D /
  §9). Dated 2026-05-21.
- `wiki/concepts/system-design-protocols.md` — review the §2 sketch
  against the implementation; add a `## Revisions` entry **only if** a
  reader following the sketch would write incorrect code (the uniform
  quorum model, the timer backoff, the explicit self-loop broadcasts).
  Otherwise leave it.

**Step 5: Verify wikilinks resolve**

Confirm the new index line and experiment-page back-links point at files
that exist on disk.

---

## Task 15: Verification, In-Review flip, and commit handoff

**Files:**
- Modify: `TASKS.md` (status flip + dashboard)

**Step 1: Run the full test suite**

REQUIRED SUB-SKILL: `superpowers:verification-before-completion`.

Run each suite and record the pass counts:
```
PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v
PYTHONPATH=src:tests/integration python3 -m unittest discover -s tests/integration -v
PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v
PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v
PYTHONPATH=src:tests/network python3 -m unittest discover -s tests/network -v
PYTHONPATH=src:tests/event_log python3 -m unittest discover -s tests/event_log -v
PYTHONPATH=src:tests/config python3 -m unittest discover -s tests/config -v
```
Expected: all green. Upstream suites (scheduler/nodes/network/event_log/
config) must be unchanged from the T28 baseline counts — T29 touched only
`src/pbft/`.

**Step 2: Confirm artifacts exist**

Verify on disk: `src/pbft/viewchange.py`, the three new test files, the
experiment page, the `wiki/index.md` + `wiki/log.md` updates.

**Step 3: Flip `TASKS.md` to In Review**

In `TASKS.md`: change T29 `[~]` → `[?]`; update the dashboard line
(`In Progress: 1 → 0`, `In Review: 0 → 1`).

**Step 4: Hand off to the human**

Do **not** run `git commit`. Summarize for the human: files touched, wiki
pages added/updated, the design decisions (full view-change, uniform
quorum, exponential backoff), the two T28 regression-test updates, and any
open questions. State the suggested commit message
(`task 29: implement PBFT voting, commit, and view-change recovery`) and
that the branch convention is `task/T29-pbft-voting`. The human reviews,
commits, and merges.

---

## Notes for the executing engineer

- Read the design spec `docs/superpowers/specs/2026-05-21-t29-pbft-voting-design.md`
  first — it carries the full implementation code for every method; this
  plan gives the test-first sequence and the exact test code.
- TDD throughout: write the test, watch it fail, implement the minimum,
  watch it pass. Never weaken an assertion to make a test green.
- If a bug surfaces during integration (Tasks 12–13), use
  `superpowers:systematic-debugging` and add a unit test that reproduces
  it before fixing.
- Tasks 7, 9 introduce **temporary stubs** for methods later tasks
  complete (`_broadcast_commit`/`_check_commit_quorum` in Task 7;
  `_arm_escalation_timer`/`_check_new_view_quorum` in Task 9). The stubs
  keep each task's tests runnable; do not forget to replace them.
- The whole T29 change is **one human commit**; the agent runs no
  `git commit`.
