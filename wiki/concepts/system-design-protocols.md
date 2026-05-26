# System Design — Protocol Main Loops

Companion to [[concepts/system-design]]. That page draws the
architecture (§2) and one run end-to-end (§3); this page gives the four
protocols' **main loops** as event-handler pseudocode — PBFT, Casper
FFG, Snowman, Narwhal+Tusk — and carries the open-to-revision register
spanning both pages. Split per `docs/wiki-spec.md` § Page size; same
precedent as [[concepts/simulation-design]] /
[[concepts/simulation-design-runtime]].

Consumed by the per-protocol implementations: T28 / T29 (PBFT), T32–T34
(Casper FFG), T38 (Snowman / Narwhal+Tusk).

## 1. Event-handler framing

The simulator is event-driven: the **Scheduler owns the only run
loop**, and a `Node` is a set of handlers — `start`, `on_message`,
`on_timer` ([[concepts/node-model]] §6) — over a per-protocol FSM.
There is no textbook "main loop" per protocol; what each section below
gives under that heading is the protocol's **handler-dispatch logic** —
the work done per delivered message or fired timer.

Each block is an **illustrative, non-binding reference sketch**, per
the W3 design-contract style ([[concepts/node-model]] §10,
[[concepts/message-types]] §8). T28 / T32 / T38 may diverge; divergences
land as `## Revisions` entries per `docs/wiki-spec.md` § Revisions rule.
Secondary paths are elided with comments to keep the control spine
readable. `f` is the fault threshold; `2f+1` the quorum. Each section
pairs with a Mermaid `sequenceDiagram` under `diagrams/protocols/`.

## 2. PBFT

Per-`(view, seq)` three-phase commit ([[algorithms/pbft#three-phase-commit]]);
view change recovers liveness when an instance stalls
([[algorithms/pbft#view-change]]). Diagram: [[diagrams/protocols/pbft]].

```python
# Reference sketch — illustrative, non-binding (see §6).
class PBFTNode(Node):
    # cross-instance: self.view, self.view_changing, self.inst[(view, seq)]

    def start(self, t):
        if self.is_primary(self.view):
            self.set_timer("propose", PROPOSE_DELAY, None, t)

    def on_timer(self, timer_id, payload, t):
        if timer_id == "propose":                       # primary only
            req = self.batch_mempool()
            self.broadcast("PRE-PREPARE",
                           PrePrepare(self.view, self.next_seq(),
                                      digest(req), req), t)
        elif timer_id[0] == "view_change":              # instance stalled
            self.broadcast("VIEW-CHANGE", self.vc_evidence(), t)

    def on_message(self, msg, t):
        i = self.inst[(msg.payload.view, msg.payload.seq)]
        if msg.type == "PRE-PREPARE" and i.state == IDLE:
            i.state = PRE_PREPARED
            self.set_timer(("view_change", i.key), VC_DELAY, i.key, t)
            self.broadcast("PREPARE", Prepare(i.view, i.seq, i.digest), t)
        elif msg.type == "PREPARE" and i.add_prepare(msg) >= 2*f + 1 \
                and i.state == PRE_PREPARED:
            i.state = PREPARED
            self.broadcast("COMMIT", Commit(i.view, i.seq, i.digest), t)
        elif msg.type == "COMMIT" and i.add_commit(msg) >= 2*f + 1 \
                and i.state == PREPARED:
            i.state = COMMITTED
            self.cancel_timer(("view_change", i.key))
            self.emit("decided", {"value": i.digest, "instance_id": i.key}, t)
        # VIEW-CHANGE / NEW-VIEW: collect 2f+1, new primary reissues — elided
```

## 3. Casper FFG

Per-epoch two-round justify→finalise over a proposed chain
([[algorithms/pos#two-round-finalisation]]). Thresholds are
stake-weighted. Diagram: [[diagrams/protocols/casper-ffg]].

```python
# Reference sketch — illustrative, non-binding (see §6).
class CasperNode(Node):
    # cross-instance: self.epoch_state{epoch}, justified/finalised chain

    def start(self, t):
        self.set_timer("slot", SLOT_DURATION, 0, t)

    def on_timer(self, timer_id, slot, t):
        if timer_id == "slot":
            if self.is_slot_proposer(slot):             # seed-derived (node-model §5)
                self.broadcast("BLOCK-PROPOSAL", self.build_block(slot), t)
            self.broadcast("ATTESTATION", self.attest(slot), t)
            self.set_timer("slot", SLOT_DURATION, slot + 1, t)

    def on_message(self, msg, t):
        if msg.type == "BLOCK-PROPOSAL":
            self.lmd_ghost.add(msg.payload)             # head view; no FFG transition
        elif msg.type == "ATTESTATION":
            link = msg.payload.ffg                      # <source, target>
            es = self.epoch_state[link.target_epoch]
            es.stake += self.weight_of(msg.src)
            if es.state == UNJUSTIFIED and es.stake >= twothirds_stake():
                es.state = JUSTIFIED
            if es.state == JUSTIFIED and self.next_link_justified(es):
                es.state = FINALISED
                self.emit("decided", {"value": es.root,
                                      "instance_id": link.target_epoch}, t)
        elif msg.type == "SLASHING-EVIDENCE":
            self.verify_and_slash(msg.payload, t)       # → halted{slashed}
```

## 4. Snowman

Per-block subsampled poll: sample `K` peers each round, raise a
confidence counter, accept at `counter ≥ β`
([[algorithms/avalanche#snowman--linearised-production]]).
Diagram: [[diagrams/protocols/snowman]].

```python
# Reference sketch — illustrative, non-binding (see §6).
class SnowmanNode(Node):
    # cross-instance: self.block[block_id] = (preference, counter, state)

    def start(self, t):
        pass                                            # idle until a block arrives

    def on_timer(self, timer_id, block_id, t):
        if timer_id == ("poll", block_id):
            self.req_id += 1
            for peer in self.rng.sample(self.peers, K):  # K-peer subsample
                self.send(peer, "QUERY", Query(self.req_id, block_id), t)

    def on_message(self, msg, t):
        if msg.type == "BLOCK-ANNOUNCEMENT":
            self.block[msg.payload.block_id] = (msg.payload.block_id, 0, POLLING)
            self.set_timer(("poll", msg.payload.block_id), POLL_DELAY, ..., t)
        elif msg.type == "QUERY":
            self.send(msg.src, "QUERY-RESPONSE",
                      QueryResponse(msg.payload.request_id, self.preferred()), t)
        elif msg.type == "QUERY-RESPONSE":
            b = self.collect(msg)                       # one block per poll round
            if b.responses == K:                        # round complete
                if b.agree_count >= ALPHA_C:
                    b.counter = b.counter + 1 if b.kept_pref else 1
                else:
                    b.counter = 0
                if b.counter >= BETA:
                    b.state = ACCEPTED
                    self.emit("decided", {"value": b.hash, "instance_id": b.id}, t)
                else:
                    self.set_timer(("poll", b.id), POLL_DELAY, b.id, t)
```

## 5. Narwhal+Tusk

Per-round DAG mempool (header → vote → certificate) plus Tusk anchor
commit, which derives a total order with zero extra messages
([[algorithms/dag-based#narwhal--the-dag-mempool]],
[[algorithms/dag-based#tusk-and-bullshark--zero-message-ordering]]).
Diagram: [[diagrams/protocols/narwhal-tusk]].

```python
# Reference sketch — illustrative, non-binding (see §6).
class NarwhalNode(Node):
    # cross-instance: self.dag (certs by (round, validator)), anchor schedule

    def start(self, t):
        self.set_timer("round", ROUND_DELAY, 1, t)

    def on_timer(self, timer_id, rnd, t):
        if timer_id == "round":
            parents = self.dag.certs_at(rnd - 1)[:2*f + 1]
            self.broadcast("HEADER",
                           Header(rnd, self.id, parents, self.batch_mempool()), t)
            self.set_timer("round", ROUND_DELAY, rnd + 1, t)

    def on_message(self, msg, t):
        if msg.type == "HEADER":
            if self.parents_available(msg.payload):
                self.send(msg.src, "HEADER-VOTE", Vote(msg.payload), t)
        elif msg.type == "HEADER-VOTE":
            i = self.dag.own_header(msg.payload.round)
            if i.add_vote(msg) >= 2*f + 1 and i.state == PROPOSING:
                i.state = CERTIFIED
                self.broadcast("CERTIFICATE", i.certificate(), t)
        elif msg.type == "CERTIFICATE":
            self.dag.add_cert(msg.payload)
            self.try_anchor_commit(msg.payload.round, t)  # local predicate

    def try_anchor_commit(self, rnd, t):
        a = self.dag.anchor_for(rnd)
        if a and self.dag.refs_to(a, rnd + 1) >= 2*f + 1 and a.state == NOMINATED:
            a.state = COMMITTED                          # zero wire messages
            self.emit("decided", {"value": a.cert_id, "instance_id": a.key}, t)
```

## 6. Open to revision

Synthesis-level fit issues already visible across both pages; each
lands as a `## Revisions` entry per `docs/wiki-spec.md` § Revisions rule
rather than a silent overwrite.

- **All four pseudocode sketches** (§§2–5). Non-binding. T28 (PBFT),
  T32 (Casper FFG), T38 (Snowman / Narwhal+Tusk) may diverge as
  implementation reveals fit issues; the diagrams and these pages
  update to follow.
- **PBFT view-change / NEW-VIEW body** (§2). Elided to a comment. T29
  implements the full recovery path; if the elision hides a structural
  choice, §2 grows it back.
- **Snowman `α_p` / `α_c` split** (§4). The sketch uses one `ALPHA_C`;
  production Snowman splits the preference-flip threshold from the
  counter-increment threshold ([[concepts/node-model]] §10). T38 may
  need the richer two-threshold form.
- **`Harness` / `Builder` boundary** ([[concepts/system-design]] §2,
  §3). The macro diagram [[diagrams/runtime/macro]] shows `Builder` as
  a distinct lifeline; T19 / T27 may fold it into the `Harness`. The
  component table treats them as one owner already.
- **`load_workload` seam** ([[concepts/system-design]] §3 phase 2).
  Mempool seeding is named there but owned by no W3 contract yet; T27
  (reproducibility / config) is expected to pin it.

## 7. Sources

Synthesis page; no primary-literature citations. Mechanism semantics
and the bibliography live on the algorithm pages.

**Inbound (existing wiki pages):**

- [[concepts/system-design]] — the architecture and run-loop half of
  this synthesis.
- [[concepts/node-model]] (T14) — handler surface (§6), outbound API
  (§7), FSM table (§4), revision register (§10).
- [[concepts/message-types]] (T16) — the wire vocabulary §§2–5 send
  and receive.
- [[algorithms/pbft]], [[algorithms/pos]], [[algorithms/avalanche]],
  [[algorithms/dag-based]] — per-protocol mechanism for §§2–5.

**Visual contract:** [[diagrams/protocols/pbft]],
[[diagrams/protocols/casper-ffg]], [[diagrams/protocols/snowman]],
[[diagrams/protocols/narwhal-tusk]] under [[diagrams/index]].

**Forward references (not yet authored):** T28 / T29 / T32 / T34 / T38
implement the §§2–5 loops; [[concepts/output-format]] (T40) fixes the
`decided`-event projection.

## Revisions

- **2026-05-21 (T29).** The §2 PBFT sketch diverges from the T29
  implementation (`src/pbft/node.py`) in three ways a reader reproducing
  the protocol from the sketch alone would get wrong:
  - *Self-recorded votes.* The sketch counts `i.add_prepare(msg)` /
    `i.add_commit(msg)` over delivered messages only. `Network.broadcast`
    excludes the sender, so a node never receives its own vote — counting
    deliveries alone tops out at `2f`, never `2f+1`. The implementation
    has every replica (the primary included) **explicitly self-record**
    its own `PREPARE` / `COMMIT` — and its own `PRE-PREPARE` — into the
    instance's quorum dict (T29 design spec Decision B).
  - *Per-view timer backoff.* The sketch arms the view-change timer with
    a flat `VC_DELAY`. The implementation uses `vc_delay·2^view` (Decision
    F): a flat delay cannot make view-change recovery terminate
    deterministically — a delay regime that view-changes once view-changes
    forever.
  - *Lazy instance creation.* The sketch does `i = self.inst[(view, seq)]`
    directly. A `PREPARE` or `COMMIT` can arrive before the local
    `PRE-PREPARE` (the network gives no ordering guarantee), so the
    implementation creates the instance with `setdefault` and files the
    vote regardless of state, counting it once the digest is known
    (Decision C).
  The §6 register already flagged the sketch as non-binding; this entry
  records the specific divergences. The control spine — three-phase
  commit, `2f+1` transitions, `decided` on `COMMITTED` — is unchanged.
- **2026-05-23 (T32).** The §3 Casper sketch diverges from the T32
  implementation (`src/pos/node.py`) in two ways a reader reproducing the
  protocol from the sketch alone would get wrong:
  - *Attestation cadence.* The sketch attests **every slot**, building the
    FFG checkpoint vote and a per-slot head vote together. The
    implementation attests **once per epoch** at `attest_offset` slots in
    (the constructor default is the mid-epoch slot — design spec Decision
    J). The per-slot head vote belongs to LMD-GHOST fork choice, which is
    out of scope (next item); without LMD-GHOST the per-slot cadence
    contributes no extra information to the FFG gadget and inflates the
    message count by a factor of `slots_per_epoch`.
  - *Fork-choice object.* The sketch references a `self.lmd_ghost`
    object to choose the head vote and resolve `chain.head` under
    competing forks. The implementation has **no fork-choice object**:
    `Chain.head` is just the block at the greatest known slot (honest-path
    linear chain — Decision B). Delay-induced reorgs are out of scope
    until T46–T50.
  The §6 register already flagged the sketch as non-binding; this entry
  records the specific divergences. The control spine — slot loop with
  proposer rotation, per-epoch FFG aggregation, two-round justify→finalise
  on a `≥ 2/3` stake supermajority, `decided` on finalisation — is
  unchanged.
