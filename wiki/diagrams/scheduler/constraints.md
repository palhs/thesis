# Scheduler — Constraints (Adversary, Determinism, Fail-Fast)

> What the scheduler does *not* do: adversaries do not attach here;
> RNGs do not live here; metrics are not computed here; the wallclock
> is not read here. Plus the four fail-fast validation gates that
> raise `ValueError` or propagate exceptions instead of producing
> wrong-but-quiet output.
>
> Part of the T17 contract diagram set. This is the "negative space"
> diagram — it pins what is in other components' jurisdiction so the
> scheduler's surface remains small.

## Diagram

```swimlanes
title: Scheduler — constraints, boundary, fail-fast

order: Harness, Node, Adversary, Network, Scheduler, EventSink, T40Consumer
autonumber

=: **adversary boundary** — gating happens at Node, not Scheduler

if: Node.adversary is None (honest)
  Node -> Network: send(dst, msg, t)
else: Node.adversary is set (Byzantine)
  Node -> Adversary: gate(send, dst, msg, t)
  Adversary -> Adversary: modify | drop | fork
  Adversary -> Network: send(dst, msg', t) (or skip entirely)
end

Network -> Scheduler: schedule(Delivery msg', t')

note Adversary, Scheduler: **Scheduler sees only post-adversary calls.** It has no adversary slot, no interception hook, no `SchedulerAdversaryProfile` type.

=: **RNG ownership** — scheduler holds no RNG

note Network: `net_rng` — owned by Network; drives delay and drop sampling
note Node: `self.rng` — owned by Node; drives FSM-internal randomness (Snowman sampling, timer jitter)
note Scheduler: pure dispatch; **no `random.*` calls anywhere in its body**

=: **metric computation** — done downstream, not in scheduler

Scheduler -> EventSink: every popped event flows through `event_sink`
EventSink -> T40Consumer: structured event stream
T40Consumer -> T40Consumer: derive latency, throughput, msg counts, finality, fork rate

note Scheduler: scheduler never computes throughput, latency, success rate; it produces a deterministic event stream and stops there

=: **wallclock** — forbidden in every component

note Node: receives `t` as parameter on every handler; never reads wallclock
note Network: samples delay against virtual time; never reads wallclock
note Scheduler: advances `self._now` only on pop; never reads wallclock

=: **fail-fast validation gates**

if: `schedule(event, t)` with `t < self.now`
  Scheduler => Harness: raise ValueError — no time travel
end

if: `set_timer(..., delay)` with `delay < 0`
  Scheduler => Harness: raise ValueError — no negative delay
end

if: handler (on_message / on_timer / advance_phase) raises
  Scheduler => Harness: exception propagates out of run() — not caught
end

if: event_sink callback raises
  Scheduler => Harness: exception propagates out of run() — T24 wraps its own try/except if it wants graceful logging
end

note Harness, Scheduler: **`delay == 0` is allowed** — fires on the next iteration via the tie-break `seq` ordering
```

## What this pins

**Adversaries attach at `Node.adversary`, not at the scheduler.** The
four T18 generic adversaries (delayer, equivocator, non-participant,
leader-disruptor) all gate or modify the Node's outbound API. By the
time a call reaches `Network.submit_*` or `Scheduler.schedule`,
adversary semantics have already been applied. The scheduler is
unaware. Network is also unaware; see [[concepts/network-model]] §6.

The honest reason for this design: in real distributed systems, the
scheduler is not a network element you can attack. Real-world
equivalents are kernel schedulers and event loops, which adversaries
do not have direct access to. A scheduler-layer adversary would model
a threat that does not correspond to anything in production.

**Three RNG streams, none in the scheduler.** `Network.net_rng` seeds
delay and drop sampling. Each `Node.self.rng` seeds FSM-internal
randomness. The scheduler holds no RNG and makes no `random.*` calls.
Determinism is therefore a property of (a) seed inputs to Network and
Nodes and (b) the scheduler's deterministic dispatch — pure function
of (heap state, registry state).

**Metrics are derived downstream from the event stream.** T40 (unified
output) consumes the stream produced by `event_sink` plus Node-emitted
`decided` / `halted` events to build CSV columns. The scheduler does
not aggregate, count, average, or compute statistics. The scheduler's
contribution is to *produce* the stream deterministically; the
contribution of T40 is to *derive metrics* from it.

**No component reads wallclock.** The simulator is virtual-time
throughout. `Node` handlers receive `t` as a parameter; `Network`
samples delays against virtual time; the scheduler advances
`self._now` only on event pop. A `time.time()` call anywhere in the
simulator is a determinism bug.

**Four fail-fast validation gates.** Each raises immediately rather
than swallowing:

| Condition | Behaviour |
| :-- | :-- |
| `schedule(event, t, node_id)` with `t < self.now` | `ValueError` raised by `schedule()`. |
| `set_timer(..., delay)` with `delay < 0` | `ValueError` raised by `set_timer()`. |
| Exception inside a handler (`on_message`, `on_timer`, `advance_phase`) | Propagates out of `run()`. Scheduler does not catch. |
| Exception inside `event_sink` callback | Propagates out of `run()`. T24 wraps its own `try/except` if it wants graceful logging. |

**`delay == 0` is allowed.** A zero-delay `TimerFire` is scheduled at
`self.now` and pops on the next iteration. The tie-break key
`(t, node_id, seq)` sorts it after the current handler's continuation
because `seq` increments on every `schedule()` call. This is the
natural "yield to the scheduler" idiom for protocols that want to
schedule self-callbacks without advancing virtual time.

**Why fail-fast over fail-silent.** For a thesis whose central
artifact is "this experiment can be re-run and you get the same
numbers," wrong-but-quiet is the worst outcome — far worse than
crashing with a clear traceback that says "delay = −1 at line 47."
Bugs surface immediately, not three weeks into a result analysis.

## Cross-links

- Adversary attachment surface: [[concepts/node-model]] §9.
- Network honest-infrastructure boundary: [[concepts/network-model]] §6.
- Determinism contract (Node side): [[concepts/node-model]] §8.
- Determinism contract (Network side):
  [[concepts/network-model-phases]] §6.
- Reproducibility hook: [[concepts/reproducibility]] (T27,
  forthcoming).
- Output schema: [[concepts/output-format]] (T40, forthcoming).
- Tie-break key that allows `delay == 0`: [[concepts/node-model]] §8.3.

## Source

Authored as part of T17 ([[concepts/simulation-design]]).

## Revisions

None.
