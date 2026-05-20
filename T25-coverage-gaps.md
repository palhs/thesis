# T25 coverage gaps — working document

Working scratch document compiled during the 2026-05-20 T25 self-assessment
walkthrough. Captures behavioral gaps in the test suite — what the tests
do *not* prove — grouped per module and tagged by the owning task, so
human can decide which to compensate inside T25 versus leave to the
owning task.

Not a wiki artifact. Delete (or archive elsewhere) once T25 merges.

**Status (2026-05-20 end of walkthrough):** All five modules complete. Modules 1–3 closed selective gaps as the walkthrough progressed (see per-module tables). Modules 4 (event_log) and 5 (integration) closed every catalogued gap candidate at the user's direction — 7 new tests in `tests/event_log/`, 13 new tests across 8 new files in `tests/integration/`. Full suite: 178 → 206 green (scheduler 46, nodes 42, network 61, event_log 30, integration 27).

**Legend on the Owner column:** every gap is tagged by the task whose
scope it sits inside (T21 = scheduler, T22 = nodes, T23 = network,
T24 = event_log, T25 = integration). The integration suite itself
(T25) only owns gaps about cross-module interaction; module-internal
gaps stay with their module's task.

**Status:** `OPEN` = still uncovered; `CLOSED` = test added inside T25;
`DEFERRED` = recorded in TASKS.md Backlog for a future task.

---

## Module 1 — scheduler  (`src/scheduler/`, `tests/scheduler/`)

Coverage of `src/scheduler/` by the scheduler suite alone: 99.0 %
(`scheduler.py:179` is an intentionally-unreachable defensive `raise`
in `_dispatch`'s unknown-event-class `else`; not a real gap).

Scheduler suite test count: 40 → **46** after T25 review (+6 tests).

### Gap candidates

| ID   | Gap candidate                                                                                                                                                                                                                                                             | Owner   | Severity | Status   |
| :--- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------ | :------- | :------- |
| S-1  | `stop_when` predicate is documented to be checked *after each dispatch*, but no test confirms it is **not** invoked after a tombstoned event or when the heap is empty.                                                                                                      | T21     | Low      | OPEN     |
| S-2  | The `event_sink` is not called for tombstoned events. No test mixed a tombstoned and a live event in one run to assert the sink sees only the live one.                                                                                                                       | T21     | Low      | **CLOSED** — `test_event_sink_skips_tombstoned_events` |
| S-3  | `bind(node)` collision: re-binding a node, or binding two `Node` instances with the same `node_id`, silently overwrites `self.nodes[node.id]`. Direct analogue of the `Network.register` Backlog item.                                                                       | T21+T23 | Medium   | DEFERRED — bundled with existing `Network.register` Backlog entry, now amended to cover both subsystems. Fix-together hardening task. |
| S-4  | At a single `t`, `PhaseAdvance` (sentinel `node_id = -1`) is supposed to sort before every real-node event — the half-open `[t_start, t_end)` boundary the Network relies on. No test exercised a same-`t` mix.                                                                | T21     | Low      | **CLOSED** — `test_phaseadvance_dispatched_before_real_events_at_same_t` (ST-4) |
| S-5  | High-churn tombstone garbage growth. Already in TASKS.md Backlog ("Scheduler heap growth under high timer churn").                                                                                                                                                            | T21/T28+| Low      | REGRESSION SENTINEL added (ST-2); underlying Backlog item still open for the eventual compaction work in T28+. |
| S-6  | `scheduler.py:179` — defensive unreachable `raise`. Not a real gap; documented in the T26 coverage-tooling Backlog entry.                                                                                                                                                     | T21     | n/a      | n/a      |

### Stress-test coverage

Eight canonical scheduler stress dimensions surveyed during the T25
walkthrough. Three high/medium-value dimensions plus one for completeness
were closed inside T25.

| ID   | Stress dimension                                                                          | Status                                                       |
| :--- | :---------------------------------------------------------------------------------------- | :----------------------------------------------------------- |
| ST-1 | Huge calendar — 10k+ events queued                                                         | Not added — low thesis-scope value (stdlib heap is mature)  |
| ST-2 | Tombstone density / high churn — many set/cancel cycles                                    | **CLOSED** — `test_tombstone_density_under_high_churn` (20 nodes × 100 cycles → 2,000 tombstones + 20 live fires; regression sentinel for S-5) |
| ST-3 | Same-`t` many events — 50+ events at one timestamp                                         | **CLOSED** — `test_same_t_many_events_dispatched_in_canonical_node_seq_order` (20 nodes × 5 events = 100 events at one `t`, scrambled submission) |
| ST-4 | Mixed event classes at same `t` — PhaseAdvance + Delivery + TimerFire                      | **CLOSED** — `test_phaseadvance_dispatched_before_real_events_at_same_t` (also closes S-4) |
| ST-5 | Long virtual-time runs / float precision at large `t`                                      | Not added — thesis simulates seconds, not centuries          |
| ST-6 | Many bound nodes — 100+ in the registry                                                    | Not added — dispatch is O(1) dict, low value                |
| ST-7 | Reentrancy chains — handler schedules a delay=0 successor                                  | **CLOSED** — `test_bounded_reentrancy_chain_at_delay_zero_terminates` + bonus `test_runaway_reentrancy_chain_bounded_by_stop_when` (predicate as safety valve) |
| ST-8 | Predicate under high event rate                                                            | Not added — covered behaviorally, low regression risk        |

---

## Module 2 — nodes  (`src/nodes/`, `tests/nodes/`)

Coverage of `src/nodes/` by the nodes suite alone: 100 % line (modulo the
`trace._find_executable_linenos` line-0 artifact also seen on the
scheduler). No defensive-unreachable `raise` in `src/nodes/`.

Nodes suite test count: 41 → **42** after T25 review (+1 test).

The shared-layer Node is thin by design: identity, lifecycle FSM, per-Node
RNG, inbound lifecycle guards, and outbound API placeholders. Protocol
behaviour arrives in T28 (PBFT), T32 (Casper FFG), T38 (Snowman /
Narwhal+Tusk). Three of the six gap candidates below are best resolved at
the protocol seam where the contract first bites, not pre-emptively in T22.

### Gap candidates

| ID  | Gap candidate                                                                                                                                                                                                                              | Owner   | Severity | Status                                                                 |
| :-- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------ | :------- | :--------------------------------------------------------------------- |
| N-1 | `halt()` from `CREATED` — never-started Node receiving the harness blanket `RUN_END` halt — is an undocumented but reachable transition (skips `RUNNING`). No test pins it.                                                                | T22     | Low      | **CLOSED** — `test_halt_from_created_skips_running_and_drops_inbound` |
| N-2 | Outbound binding partition: `send`/`broadcast` ← `Network.bind()`; `set_timer`/`cancel_timer`/`emit` ← `Scheduler.bind()` (node-model §5.5). Only `emit` rebind is unit-tested.                                                              | T22     | Low      | Not added — placeholder pattern; production binders enforce it, covered indirectly by e2e. |
| N-3 | Non-finite `weight` (`NaN`, `±inf`) is not rejected — `weight < 0` returns `False` for `NaN`. No protocol uses weight yet; matters for Casper FFG (T32) where weight is staked balance.                                                      | T22+T32 | Low      | DEFERRED — added to TASKS.md Backlog as a Casper FFG (T32) precondition. |
| N-4 | `Node.__init__` accepts `node_id = -1`, which collides with the scheduler `PhaseAdvance` sentinel (also `node_id = -1`) in the heap's `(t, node_id, seq)` tie-break.                                                                          | T22+T21 | Low      | DEFERRED — folded into the existing S-3 / `Network.register` Backlog item (same fail-fast-at-bind-or-register theme). |
| N-5 | Node-layer e2e is the 2-node `PingPongNode` only. No 4/7/10-node test at the node layer.                                                                                                                                                    | T22     | n/a      | By design — T25 integration owns multi-node scenarios; PingPong is unit-scope build verification. |
| N-6 | Re-entrant `emit` during `halt()` — `halt` calls `self.emit(HALTED, ...)`; no test pins that emit is exactly once per halt or that a misbehaving sink can't loop.                                                                            | T22     | Low      | Not added — `Scheduler.bind` is the contract owner; out of T22 unit scope. |

### Stress-test coverage

Eight candidate dimensions surveyed. The shared-layer Node's behavioral
surface is small, so most "stress" of interest is protocol-FSM stress that
arrives with T28+/T32+, not T22.

| ID   | Stress dimension                                                                                       | Status |
| :--- | :----------------------------------------------------------------------------------------------------- | :----- |
| NT-1 | Lifecycle cycling — repeated `CREATED → RUNNING → HALTED` cycles                                        | Not applicable — lifecycle is monotonic (covered by `test_start_after_halt_raises`). |
| NT-2 | Halt mid-inbound-burst — many messages queued, halt arrives midstream                                   | Not added — drops are status-only and payload-independent; per-event drop is already tested, only the count changes. |
| NT-3 | Many bound nodes (50+) in one run                                                                       | Covered upstream by T25 integration (4/7/10 nodes); going higher only stresses Python dict/heap scaling. |
| NT-4 | Per-Node RNG churn — 10k samples for distribution shape                                                  | Not added — `random.Random` is stdlib; the pinned-literal seed test already pins byte-identical RNG output, which is what we contract against. |
| NT-5 | Inbound payload variety while HALTED                                                                    | Not added — HALTED drop is unconditional regardless of payload. |
| NT-6 | Cross-Node RNG isolation                                                                                | Already covered — `random.Random` instances are independent; the `different-id` and `different-global-seed` divergence tests pin separation. |
| NT-7 | Self-halt during `_on_message` (handler calls `self.halt`)                                              | Already covered — `PingPongNode._on_message` does exactly this when `hops >= budget`; exercised by the e2e tests. |
| NT-8 | `start()` followed by immediate `halt()` at the same `t` (non-participant-adversary pattern)            | Not added — covered indirectly by halt-from-RUNNING + dropped-on-HALTED tests. May want an explicit test when T18 adversary wiring lands at T28+. |

---

## Module 3 — network  (`src/network/`, `tests/network/`)

Coverage of `src/network/` by the network suite alone: 99.5 % line —
`phases.py` and `__init__.py` were already at 100 %; `network.py:58`
(the body of the `node.broadcast = lambda ...` wrapper installed by
`bind()`) was the sole uncovered line, closed inside T25 by W-1 below.
The lambda *assignment* statement runs on every `bind()` call, but no
network-suite test had ever invoked `node.broadcast(...)` through a
bound node — only `submit_broadcast` directly. The integration suite's
`BroadcastNode` did exercise it; the network unit suite did not, so a
regression in the wrapper would only fail integration, not unit.

Network suite test count: 57 → **61** after T25 review (+4 tests).
Integration suite gained one new test class (`tests/integration/test_drop_rate.py`,
3 tests) for NW-4. Behavioral surface and stress dimensions surveyed
together — most "stress" of interest in the latency-only honest layer
is statistical calibration (delay shape, drop rate), not load.

### Gap candidates

| ID  | Gap candidate                                                                                                                                                                                                                             | Owner | Severity | Status                                                                 |
| :-- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---- | :------- | :--------------------------------------------------------------------- |
| W-1 | `Network.bind` installs `node.broadcast = lambda type, payload, t: self.submit_broadcast(node.id, ...)` but the lambda body was never invoked by the network suite (only `submit_broadcast` was called directly). Sole uncovered line in `src/network/`. | T23   | Low      | **CLOSED** — `test_bind_broadcast_lambda_invoked_through_node` |
| W-2 | Drop + partition composition in one phase. The §6.2 single-axis tests pin the sampling-order contract for each axis independently but not the joint case (partition-bound message under `p_drop > 0` should still consume exactly one RNG draw, zero delay samples). | T23   | Low      | **CLOSED by NW-6** — `test_drop_and_partition_compose_per_sampling_order` |
| W-3 | `Network.start()` is not idempotent — calling twice doubles `PhaseAdvance` events on the heap. Symmetric to the existing `Network.register` / `Scheduler.bind` collision pattern.                                                          | T23   | Low      | DEFERRED — folded into the existing register/bind Backlog bundle (now register/bind/start — three fail-fast-at-the-seam items, one task). |
| W-4 | `validate_timeline` has no explicit `p_drop < 0` rejection test — the `not (0.0 <= p_drop < 1.0)` predicate catches it, but no test pins it.                                                                                                | T23   | Low      | Not added — same predicate handles both bounds; marginal value. |
| W-5 | Partition with ≥ 3 groups is permitted by the contract (`Partition.groups` is a `tuple[tuple[NodeId, ...], ...]`; validator requires `>= 2`) but only 2-group partitions are tested. `_group_of` is general.                              | T23   | Low      | Not added — generalisation case; low regression risk. |
| W-6 | `Network.register` silently overwrites on duplicate NodeId. **Already in Backlog** as the S-3 / N-4 register/bind collision bundle; W-3 above extends the same bundle to include `start()`.                                                | T23   | Low      | DEFERRED — in Backlog (bundle now amended to register/bind/start). |
| W-7 | `_LATENCY_FLOOR = 1e-9` (the universal positive floor binding on the measure-zero exponential edge case) is never specifically pinned; the existing `> 0` tests check the looser bound.                                                    | T23   | Low      | Not added — testable only by monkey-patching `random.expovariate`; low value. |
| W-8 | Broadcast iterates `sorted(self.registry)` — §6.3 forbidden surface for deterministic RNG consumption. `test_broadcast_reaches_registry_minus_sender` checks the delivery *set*, not the dst → delay-sample mapping. A regression that dropped `sorted()` would still pass the existing set-comparison but would shuffle the dst→delay assignment across registration orders, breaking byte-identical replay. | T23   | Low–Med  | **CLOSED by NW-8** — `test_broadcast_rng_consumption_independent_of_registration_order` |

### Stress-test coverage

Eight canonical network stress dimensions surveyed. Three closed inside
T25 — the §6.2 sampling-order composition pin (NW-6), the §6.3
sorted-broadcast determinism seam (NW-8), and the integration drop-rate
calibration analogue of the existing delay-distribution shape test
(NW-4). One contract-immutability pin (NW-5) closed in the same pass.

| ID   | Stress dimension                                                                                                  | Status                                                                  |
| :--- | :---------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------- |
| NW-1 | Large-registry broadcast (50+ nodes) — fan-out + `sorted()` scaling                                               | Not added — thesis tops at n=10; O(n log n) sort + O(n) deliveries are Python builtins. |
| NW-2 | Many-phase timeline (10+ phases) in one run                                                                       | Not added — only stresses the already-stressed scheduler heap (ST-3); `validate_timeline` is O(n). |
| NW-3 | Heavy-tail / exponential delay distribution-shape check                                                            | Not added — T46/T47 experiment fidelity rather than T23 contract; uniform-shape covered by `tests/integration/test_delay_distribution.py`. |
| NW-4 | Drop-rate calibration — observed delivery rate matches `1 - p_drop` over many seeded runs                          | **CLOSED** — `tests/integration/test_drop_rate.py` (60 seeded runs × 7-node broadcast × 42 trials/run = 2 520 Bernoulli draws; observed rate within ±0.03 of configured `p_drop=0.3`). Bernoulli analogue of `test_delay_distribution.py`; the existing unit suite only pinned the saturation case (`p_drop ≈ 1.0` → 0 deliveries). |
| NW-5 | Phase parameters baked at submit time — a Delivery scheduled in `phase[i]` is unaffected by a subsequent `advance_phase(i+1)`. The converse of `test_active_phase_governs_delay`. | **CLOSED** — `test_phase_parameters_baked_at_submit_time` (heap entry's fire time stays at `t_sent + phase[0].delay` after `advance_phase(1)`; phase 1's delay is never retroactively applied). |
| NW-6 | Drop + partition composition in same phase — joint case for the §6.2 sampling-order contract (also closes W-2)     | **CLOSED** — `test_drop_and_partition_compose_per_sampling_order` (partition-bound message under `p_drop=0.5` consumes exactly one RNG draw — the drop coin — regardless of how it lands; zero delay samples; zero scheduled deliveries). |
| NW-7 | Partition with 3+ groups — generalisation beyond the 2-group case                                                  | Not added — `_group_of` / `blocks` logic is fully general; low regression risk. |
| NW-8 | Broadcast iteration order — `sorted(NodeId)` RNG-consumption determinism seam (also closes W-8)                    | **CLOSED** — `test_broadcast_rng_consumption_independent_of_registration_order` (registering `[0,1,2,3]` vs `[3,2,1,0]` produces the identical dst → delivered-time mapping under a stochastic uniform delay; a regression dropping `sorted()` would shuffle the mapping and fail this pin). |

---

## Module 4 — event_log  (`src/event_log/`, `tests/event_log/`)

Coverage of `src/event_log/` by the event_log suite: 100 % line by
visual inspection — every branch of `EventLogger.sink` (the four
payload shapes plus the fail-fast `else`), every `to_csv` path
(header-only, populated, sorted-keys repr, missing-parent-dir
creation), and every public name re-exported from the package root is
reached by the unit suite. No `coverage` tool is wired in this session
(T26 scaffolding owns that); the claim is by reading, not by
`coverage report`.

Event-log suite test count: 23 → **30** after T25 review (+7 tests
closing all six gap candidates plus the LT-2 / LT-3 stress dimensions
that compose with them).

The event_log subsystem is structurally the **flight recorder** of the
simulator: a passive, write-only observer that watches the
`Scheduler.event_sink` seam and normalises a heterogeneous payload
stream (emit tuples + typed transport events) into uniform
`EventRecord`s, then exports them on demand to CSV. It holds no
scheduler reference, no file handle, and never schedules anything —
the design contract in [[concepts/event-log-schema]] pins this. Its
behavioural surface is small (one `sink` callback with four payload
branches plus a fail-fast default, one `to_csv` exporter, one frozen
record type, one constant vocabulary), and the existing 23-test suite
is dense on that surface. The valuable T25-review gaps are therefore
contract-edge cases inside the small unit surface and one
cross-component pin: the existing T25 integration suite mounts its own
custom sink (`tests/integration/_helpers.py:86`–`94`) rather than the
real `EventLogger`, so the seam is unit-tested at 2 nodes (e2e) and
never end-to-end at 4/7/10-node scale.

### Gap candidates

| ID  | Gap candidate                                                                                                                                                                                                                                                                                              | Owner | Severity | Priority | Analogy (flight recorder) | Status |
| :-- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---- | :------- | :------- | :------------------------ | :----- |
| L-1 | `EventRecord` is a frozen dataclass — `r.t = 9.0` raises `FrozenInstanceError` (pinned by `test_record_is_frozen`) — but `r.fields` is a `dict`, which is *not* frozen. A downstream consumer that does `r.fields["k"] = "mutated"` silently corrupts a buffered record. The emit-side defensive copy (`test_emit_fields_dict_is_copied_not_aliased`) protects the inbound direction only; the symmetric outbound concern is unpinned. | T24   | Low      | Med      | The recorder's outer case is welded shut, but the tape spool inside can still be scribbled on by anyone holding the reel. | **CLOSED** — `test_fields_dict_is_mutable_in_place_known_contract_limitation` (negative pin documenting the contract limitation; a future `MappingProxyType` wrap would flip the assertion). |
| L-2 | `ast.literal_eval` round-trip is pinned (`test_fields_cell_has_sorted_keys`) only for `{"a": 1, "b": 2}` — plain int/str values. The design contract claims the CSV cell round-trips the tuple `instance_id` of PBFT / Narwhal `decided` events ([[concepts/event-log-schema]] §"CSV format"), but no test feeds a `fields` dict containing a tuple value through `to_csv` and then back through `ast.literal_eval`. A regression that switched `repr` → `json.dumps` would pass every existing test (JSON serialises `{"a": 1, "b": 2}` to `'{"a": 1, "b": 2}'` which still parses) but silently break the `instance_id` round-trip (JSON has no tuple type). | T24   | Low–Med  | Med      | We promised the tape format is readable back as the same shape it was written — but only checked that for plain numbers and strings, not for the tuple instance ids the real protocols will emit. | **CLOSED** — `test_csv_cell_round_trips_tuple_via_ast_literal_eval` (feeds a tuple-valued `instance_id` through `to_csv` + `ast.literal_eval`, asserts type discipline preserves `tuple`, not `list`). |
| L-3 | The T25 integration suite (`tests/integration/_helpers.py:86`) installs a custom inline sink — `def sink(t, nid, seq, ev): ...` — instead of mounting `EventLogger`. So the logger's `sink` is exercised end-to-end only by the 2-node `PingPongNode` e2e in `tests/event_log/test_e2e.py`. There is no proof that a real 4/7/10-node integration run feeds the `EventLogger` faithfully — e.g. that the `(t, node_id, seq)` triples the logger records match the dispatch order the integration suite already pins via its custom sink. | T24+T25 | Low–Med  | **High** | The dress rehearsal mounts a stenographer in the wings; the actual flight recorder has never flown a full-cast scene. (Pair: Module 5 **I-3**.) | **CLOSED by I-3** — `tests/integration/test_event_logger_integration.py` (3 tests: real EventLogger captures n*(n-1) deliveries at 4/7/10 nodes, recorded `(t, node_id, seq)` keys strictly increasing, byte-identical CSV across seed-identical 7-node runs). |
| L-4 | The e2e tests assert `{"decided", "halted", "delivery"}` ⊆ `seen` (`test_both_event_sink_shapes_are_recorded`), but `PingPongNode` arms no timers and the single-phase `(Phase(0, inf, …))` setup means `phase_advance` only fires once at `t=0` and is not asserted, and `timer_fire` never fires at all. So 3 of the 5 event-type branches are e2e-validated; `timer_fire` and `phase_advance` are unit-only (`test_timer_fire_records_timer_id_only`, `test_phase_advance_records_phase_id`). | T24   | Low      | Low      | The only flight the recorder has flown emits 3 of the 5 event types it claims to handle — the other 2 are bench-tested only. | **CLOSED** — `test_recorded_stream_contains_all_five_event_types` + the `TimerPingNode` fixture (two-phase Network + timer-arming node ⇒ recorded stream contains delivery + timer_fire + phase_advance + decided + halted in one real run). |
| L-5 | `to_csv` after `to_csv` to the same path silently overwrites (stdlib `open(path, "w")` semantics). No test pins this. A future caller relying on append-on-second-call would be surprised. Symmetric to a `sink()` call *after* a `to_csv`: the logger holds no file handle and the buffer is untouched by export, so further `sink()`s extend it — also unpinned. | T24   | Low      | Low      | We never test dumping the tape twice to the same drawer, or whether the recorder keeps rolling after the dump. | **CLOSED** — `test_second_to_csv_to_same_path_overwrites` (replaces the file rather than appending) + `test_sink_after_to_csv_extends_buffer` (further sinks extend the buffer; export holds no file handle). |
| L-6 | Emit-tuple structural detection requires `len(payload) == 3`. `test_non_emit_tuple_raises_type_error` covers the wrong-tag case (`("notemit", "x", {})`), but a 2-tuple `("emit", "x")` or a 4-tuple `("emit", "x", {}, "extra")` is not explicitly tested. Both fall through to the same `raise TypeError`; only the principle is tested, not the arity edges. | T24   | Low      | Low      | The recorder rejects "definitely-not-an-emit" but we never tried "almost-an-emit" (right tag, wrong arity). | **CLOSED** — `test_two_tuple_emit_raises_type_error` + `test_four_tuple_emit_raises_type_error` (both arity edges of the `len(payload) == 3` guard pinned to `TypeError`). |

### Stress-test coverage

Eight canonical stress dimensions surveyed for the event_log. The
subsystem has no load-bearing internal state machine (`sink` is one
`list.append`; `to_csv` is one synchronous write), so most "stress" of
interest is *coverage-shape* rather than scale: do all five event-type
branches appear in a real recorded stream, and does the byte-identical
replay contract hold past 2 nodes.

| ID   | Stress dimension                                                                                       | Status |
| :--- | :----------------------------------------------------------------------------------------------------- | :----- |
| LT-1 | Huge buffer — 100k+ records in memory                                                                  | Not added — thesis scale is ~10 nodes × ~10 s sim time, ~10² records per run. The CSV writer is stdlib; `list.append` is amortised O(1). |
| LT-2 | All five event types in one recorded stream — `halted` + `decided` + `delivery` + `timer_fire` + `phase_advance` (e2e gap L-4) | **CLOSED by L-4** — `test_recorded_stream_contains_all_five_event_types` (TimerPingNode + two-phase Network e2e). |
| LT-3 | Multi-node byte-identical CSV replay — 4/7/10-node seed-identical runs export byte-identical CSV       | **CLOSED by I-3** — `tests/integration/test_event_logger_integration.py::test_byte_identical_csv_across_seed_identical_runs_at_7_nodes` (seed-42 vs seed-42 7-node uniform-delay runs → byte-identical CSV). |
| LT-4 | `to_csv` then more `sink()` then a second `to_csv` — resumable buffer (overlaps L-5)                   | Not added — folded into L-5 above; behavioral fact, not a stress dimension. |
| LT-5 | Production-payload `fields` round-trip — tuple `instance_id`, `None`, nested dict, large int (overlaps L-2) | Not added — folded into L-2 above; the gap is contract-shape, not scale. |
| LT-6 | Sink throughput under high event rate                                                                  | Not applicable — sink is a synchronous `list.append`; no buffering, no I/O, no contention. |
| LT-7 | Concurrent sink access                                                                                 | Not applicable — the simulator is single-threaded by design ([[concepts/simulation-design]] §4). |
| LT-8 | Empty-buffer `to_csv` idempotence — repeated header-only writes                                        | Already covered — `test_empty_buffer_writes_header_only` pins the empty case; repeated calls are mechanically the same write. |

---

## Module 5 — integration  (`tests/integration/`)

### Role in the analogy

Modules 1–4 are the per-subsystem walkthroughs. To carry the simulator
analogy forward one step:

- **Module 1 — scheduler** is the *metronome*: every event ticks past it
  in `(t, node_id, seq)` order, and the entire simulation's notion of
  "what happens next" is whatever the heap pops.
- **Module 2 — nodes** are the *actors*: identity, lifecycle, per-Node
  RNG, the inbound/outbound API placeholders. The shared layer is the
  empty stage costume the four protocol FSMs (T28 / T32 / T38 / T38)
  will be poured into.
- **Module 3 — network** is the *postal channel*: it takes one `send`
  or `broadcast`, samples a delay (and a drop coin, and a partition
  membership), and schedules a future `Delivery`. It is the only place
  randomness affects the message stream.
- **Module 4 — event_log** is the *flight recorder*: a passive,
  write-only observer mounted on `Scheduler.event_sink`, recording
  every dispatch and every `Node.emit` into a uniform CSV-exportable
  stream that downstream T40 metrics consume.

**Module 5 — integration is the *dress rehearsal*.** Each per-subsystem
suite drives a 2-node ping-pong — a scene check between two actors on
a bare stage. Integration is the first time the metronome, the cast,
the postal channel, and the flight recorder all play together under
load, with the validator set scaled to the sizes the thesis actually
cares about: **n = 4** (the minimum BFT committee, `3f+1` with `f=1`),
**n = 7**, and **n = 10**. The job of this module is not to re-test
any single subsystem's internals — those are owned upstream — but to
prove that the seams *compose*: that the six-phase bootstrap
([[concepts/simulation-design]] §7.2) wires the four moving parts in
the documented order, that scaling from 2 to 10 actors preserves the
`(t, node_id, seq)` total order, and that the seed knob and the
network's stochastic parameters (delay distribution, drop rate)
produce the statistical shapes their unit contracts promise.

The legend at the top of this working doc pins the consequence: the
integration suite **owns only cross-module gaps**; anything
module-internal stays with its owning task. Module 5's gap surface is
therefore narrow by construction — composition gaps only.

### Test inventory + behavioral mapping

The integration suite was 0 tests before T25 and **27 tests** after —
the entire suite is T25 output. The first 14 landed during the initial
T25 implementation (4 files); the remaining 13 were added during the
T25 review walkthrough to close gaps I-1..I-8 plus L-3 (8 new files).
Per the legend, Module 5's gap surface is closed entirely from inside
T25; no deferrals to Backlog.

| File | Tests | Sweep | What it pins |
| :--- | :---: | :---- | :----------- |
| `_helpers.py` | — | — | `BroadcastNode` (one-round, n*(n-1) deliveries), `TimerNode` (three timers in scrambled submission order), `build_and_run` (six-phase bootstrap + capture sink). |
| `test_message_exchange.py` | 4 | 4 / 7 / 10 | Functional reachability under constant delay (every peer, exact n*(n-1) count, every delivery `TOKEN`, exact delay 10.0); full-`RunResult` determinism under uniform delay (closes T23-review L1); different-seed divergence. |
| `test_delay_distribution.py` | 4 | n = 7 only | Statistical calibration of the configured `uniform(low, high)` over a fixed-seed pool of 2 520 samples (60 seeds × 42 deliveries): pool size, every-sample-in-bounds, mean within ±20 of 300.0, sd within ±20 of ~115.47 (closes T23-review M1). |
| `test_drop_rate.py` | 3 | n = 7 only | Bernoulli analogue of the delay-shape pin: 60 × 42 = 2 520 trials at `p_drop = 0.3` yield an observed drop rate within ±0.03 of 0.3 (closes NW-4). |
| `test_ordering.py` | 3 | 4 / 7 / 10 | Scrambled submission order — `TimerNode` submits LATE before EARLY1 / EARLY2 and nodes are started in reverse id order — still dispatches in canonical `(t, node_id, seq)` order; dispatch keys strictly increasing; handler order matches dispatch order exactly (closes T21-review scrambled-order Backlog note). |

The 14 tests collapse to **four behavioural axes**:

1. **Reachability** — every peer reached, exact delivery count
   (test_message_exchange).
2. **Statistical shape** — observed delay distribution and drop rate
   match the configured ones (test_delay_distribution + test_drop_rate).
3. **Determinism** — seed-identical runs → byte-identical full
   `RunResult` *and* delivery stream; different seeds diverge
   (test_message_exchange).
4. **Total order** — scrambled submission and reverse-start still
   yield canonical `(t, node_id, seq)` dispatch (test_ordering).

### Coverage view

Line coverage is not the right lens for the integration suite — every
line under `src/` is the responsibility of its owning module's suite.
The right lens is **behavioural composition coverage**: which
cross-module seams does the suite cross, and which does it leave
unexercised?

Exercised:

- The full six-phase bootstrap (register → `bind_network` → split bind
  → arm phase rollover → kickoff → `run`).
- Both `Node` outbound APIs that exist today: `broadcast` (via
  `BroadcastNode`) and `set_timer` (via `TimerNode`). `send` is exercised
  only by the unit-level `PingPongNode`s.
- The Network's delay-distribution sampling (`constant` and `uniform`)
  and drop sampling (`p_drop = 0.3` mid-range, `p_drop = 0` implicitly).
- The Scheduler's `(t, node_id, seq)` tie-break across heterogeneous
  event classes (`Delivery` + `TimerFire` + `PhaseAdvance`) at n ≥ 4.
- The `event_sink` callback as a capture-then-assert observer.

Not exercised (the gap surface below):

- **Phase boundary mid-run.** Every test uses a single phase
  `(Phase(0, inf, ...))`. `advance_phase` is unit-tested in the
  Network suite but never crossed under multi-node broadcast.
- **Partition.** `Partition.groups` is unit-tested; no integration
  test sees a partitioned 4/7/10-node run.
- **Real `EventLogger`.** The capture sink in `_helpers.py:86`–`94` is
  a custom inline `def sink(...)`, not `EventLogger.sink`. The Module 4
  gap **L-3** lives here.
- **`DelayDist("exponential", ...)`.** Unit-tested; never integration-
  tested, even though it is the realistic-Internet-RTT distribution
  the thesis actually uses ([[concepts/network-model]]).
- **Halt chains under load.** No `BroadcastNode` halts explicitly;
  every run drains to quiescence. The `HALTED` / `DECIDED` emit path
  at scale is unexercised.
- **`stop_when` at integration scale.** Every test ends in quiescence,
  never in predicate stop.

### Gap candidates

| ID  | Gap candidate                                                                                                                                                                                                                                                                                            | Owner   | Severity | Priority | Analogy (dress rehearsal) | Status |
| :-- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------ | :------- | :------- | :------------------------ | :----- |
| I-1 | Multi-phase timeline crossed mid-run. `advance_phase` is unit-pinned (NW-5 confirms phase parameters bake at submit time), but no integration test sees what happens when a 4/7/10-node broadcast straddles a phase boundary — e.g., phase 0 `uniform(5, 50)` for the first half, phase 1 `uniform(50, 200)` for the rest. Composition seam between scheduler dispatch order, `PhaseAdvance` events, and the Network's per-phase sampling. | T25     | Medium   | **High** | The rehearsal only ever runs in a single weather condition — never crosses from clear-channel to lossy mid-scene. | **CLOSED** — `tests/integration/test_phase_boundary.py::test_phase0_broadcast_delays_unchanged_by_mid_run_rollover` (phase 0 constant 10ms ends at t=5; phase 1 constant 100ms; n=7 broadcast at t=0 → all 42 deliveries arrive at t=10 with phase-0-baked 10ms delay, after PhaseAdvance(1) fires at t=5). |
| I-2 | Partition phase at multi-node scale. `Partition.groups` is unit-tested at n = 2/3 in the network suite; no integration test pins a 2-group partition over n = 7 (e.g., `{0,1,2}` ⟂ `{3,4,5,6}`) producing the expected partial reachability — each node receives only from its group, total deliveries drop from `n(n-1)` to `\sum_g k_g(k_g-1)`. Thesis-critical: partitioned consensus is the central adversarial scenario for T28+. | T25     | Medium   | **High** | The rehearsal never plays the scene where the postal channel splits into two unreachable rooms — the central scene the thesis is being written to evaluate. | **CLOSED** — `tests/integration/test_partition.py::test_two_group_partition_yields_intra_group_deliveries_only` ({0,1,2} ⟂ {3,4,5,6} over n=7 → 18 = 3·2 + 4·3 intra-group deliveries; zero cross-group deliveries; each node's inbound set is exactly its in-group peers). |
| I-3 | Real `EventLogger` mounted on a 4/7/10-node integration run (closes Module 4 **L-3** + **LT-2** + **LT-3** in one pin). The suite currently uses a custom capture sink; replacing it (or adding it alongside) would cross-validate that the logger faithfully records the same `(t, node_id, seq)` stream the existing dispatch-order tests already pin, at integration scale, with byte-identical CSV across seed-identical runs. | T24+T25 | Low–Med  | **High** | Hire the actual flight recorder for the dress rehearsal instead of writing notes by hand from the wings. (Pair: Module 4 **L-3**.) | **CLOSED** — `tests/integration/test_event_logger_integration.py` (3 tests: real EventLogger captures all n*(n-1) deliveries at n=4/7/10; recorded (t,node_id,seq) keys strictly increasing; byte-identical CSV across two seed-42 7-node runs). Closes L-3 + LT-3 in one pin. |
| I-4 | `DelayDist("exponential", ...)` at integration scale. The exponential is the thesis's realistic-RTT distribution ([[concepts/network-model]]), unit-tested for shape and the `_LATENCY_FLOOR` edge, but never end-to-end exercised. A statistical-calibration analogue of `test_delay_distribution.py` (mean ≈ 1/λ, no upper bound) would close the gap. | T25     | Low      | Med      | The rehearsal uses constant and uniform postal speeds — never the realistic-Internet "memoryless tail" the thesis actually argues from. | **CLOSED** — `tests/integration/test_exponential_delay.py` (4 tests: pool size, every-sample-positive, observed mean within ±15 of configured mean=100, observed sd within ±15 of mean=100 — the signature exponential property sd=mean over 60 seeds × 42 samples = 2520 deliveries). |
| I-5 | Halt chains under load. No `BroadcastNode` halts explicitly; every test drains to quiescence. A scenario where node `k` halts mid-run while the rest finish would exercise the `HALTED`-while-inbound-pending drop path ([[concepts/node-model]] §3) at n ≥ 4 — currently pinned only by the 2-node `PingPongNode` unit e2e and by `test_halt_from_created_skips_running_and_drops_inbound` (N-1, closed inside T25 in Module 2). | T25     | Low      | Low      | No scene where one actor walks off mid-rehearsal while the rest are still on stage. | **CLOSED** — `tests/integration/test_halt_chains.py::test_halted_node_drops_remaining_same_t_inbounds` (`HaltOnFirstInboundNode` at id 0 over n=7 broadcast → node 0 records exactly 1 inbound, halts; remaining 5 same-t inbounds dispatched but dropped by HALTED guard before `_on_message`). |
| I-6 | `stop_when` predicate at integration scale. Every existing test ends in `stopped_by == "quiescence"`. No integration test pins `stopped_by == "predicate"` over a 4/7/10-node run — e.g., "stop after 10 deliveries". `RunResult.stopped_by` is unit-tested but the integration suite never produces the non-quiescence value. | T25     | Low      | Low      | The rehearsal always ends when everyone is done; never when the director calls "cut" mid-scene. | **CLOSED** — `tests/integration/test_stop_when.py::test_predicate_terminates_run_before_quiescence` (n=4 broadcast with `stop_when=lambda: delivery_count >= 5` → `stopped_by == "predicate"`, events_processed < n*(n-1)=12). |
| I-7 | Heterogeneous node mix in one run. `BroadcastNode` and `TimerNode` are exercised in separate tests; no test runs the two side by side, which would put `Delivery` and `TimerFire` events at the same `t` in the same run and re-stress the scheduler's mixed-class tie-break (ST-4) at integration scale. Bonus pin for the cross-module `(t, node_id, seq)` invariant. | T25     | Low      | Low      | No scene with a talking actor and a timer-only actor on stage together — the metronome's mixed-class beat never gets a multi-actor test. | **CLOSED** — `tests/integration/test_node_mix.py::test_mixed_broadcast_and_timer_nodes_dispatch_in_canonical_order` (4 BroadcastNodes + 4 TimerNodes in one run; dispatch stream contains both Delivery and TimerFire classes; (t, node_id, seq) keys strictly increasing across mixed events). |
| I-8 | Per-Node RNG vs `net_rng` separation at integration scale. Unit tests pin that two nodes with the same `global_seed` but different `node_id` produce different RNG streams; no integration test pins that two seed-identical runs that differ only in `global_seed` for one node (with others fixed) leave the *network*-sampled delivery stream unchanged — i.e., that the per-Node RNG and the net RNG do not bleed into each other under multi-node load. | T25     | Low      | Low      | We never check that the dice each actor rolls in their hand don't bleed into the dice the postal channel rolls for delays. | **CLOSED** — `tests/integration/test_rng_separation.py::test_changing_per_node_seed_leaves_delivery_stream_unchanged` (same Network global_seed=42; nodes built once with global_seed=42, again with global_seed=99; uniform delay stream byte-identical, confirming per-Node `random.Random` instances are independent of net_rng under multi-node load). |

### Stress-test coverage

Eight canonical integration-stress dimensions surveyed. Most of the
"stress" here is *combinatorial parameter coverage* (mixed phases,
partitions, exponential delay) rather than scale-up; the thesis tops
out at n = 10, and the existing scenarios already cover that ceiling
across the four behavioural axes above.

| ID   | Stress dimension                                                                                       | Status |
| :--- | :----------------------------------------------------------------------------------------------------- | :----- |
| IT-1 | Larger n (20 / 50 / 100 nodes)                                                                         | Not added — beyond thesis-scope validator set sizes. n*(n-1) at n = 100 = 9 900 deliveries; only stresses the scheduler heap (already covered by ST-3) and Python broadcast fan-out. |
| IT-2 | Many-phase timeline (5+ phases) crossed by a multi-node broadcast (overlaps I-1)                       | **CLOSED by I-1** — `test_phase0_broadcast_delays_unchanged_by_mid_run_rollover` pins the 2-phase boundary case; the 5+ phase generalisation is mechanical (each interior boundary schedules its own PhaseAdvance, and the bake-at-submit contract is per-message). |
| IT-3 | Partition with k ≥ 3 groups at n = 10 (generalises I-2 + closes the W-5 partition-groups concern)      | Not added — staged behind I-2; the 2-group case is the thesis-critical one. |
| IT-4 | Mixed `DelayDist` family across phases — phase 0 `uniform`, phase 1 `exponential`                       | Not added — composes I-1 + I-4; one bundled test could close both. |
| IT-5 | High drop rate (`p_drop = 0.9`) at n ≥ 4 — does quiescence still hold? does the delivery count tail match Bernoulli(0.1)? | Not added — `test_drop_rate.py` pins the mid-range case; saturation is unit-pinned (`test_full_drop_phase_suppresses_delivery`). Low marginal value at integration scale. |
| IT-6 | Adversarial node count (Byzantine, crash, late-join)                                                   | Not applicable yet — T18 adversary scaffold is design-only; real adversary nodes arrive with T28+. Deferred by construction. |
| IT-7 | Long sim time (`t` up to 10⁶ or 10⁹)                                                                   | Not added — thesis simulates seconds, not centuries; covered by the Module 1 stress survey (ST-5, dismissed there). |
| IT-8 | Recursive / multi-round broadcast — protocol that re-broadcasts on receipt                             | Not added — `BroadcastNode` is one-round by design. Real multi-round behaviour is T28+ protocol territory, not T25 scaffolding. |
