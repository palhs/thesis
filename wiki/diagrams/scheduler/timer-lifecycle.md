# Scheduler — Timer Lifecycle

> One Node's timer through set / optional cancel / optional overwrite /
> eventual fire (or silent skip). Shows how the lazy-tombstone pattern
> handles all four cases with one piece of registry state and no heap
> surgery.
>
> Part of the T17 contract diagram set. Companion to
> [[diagrams/scheduler/event-dispatch]] which shows the pop-side
> tombstone check.

## Diagram

```swimlanes
title: Scheduler — timer lifecycle (lazy tombstone)

order: Node, Scheduler, SeqPer, Registry, Heap
autonumber

note Node, Heap: **scenario** — Node sets timer_id=1; one of {cancel, overwrite, fire} happens later

Node -> Scheduler: set_timer(timer_id=1, delay=20, payload, t=10)
Scheduler -> SeqPer: seq_per[Node] -> 1
Scheduler -> Registry: registry[(Node, 1)] = 1
Scheduler -> Heap: heappush `(30, Node, 1, TimerFire id=1)`

=: time passes; scheduler pops other events

if: **case A** — cancel before fire
  Node -> Scheduler: cancel_timer(timer_id=1)
  Scheduler -> Registry: del registry[(Node, 1)]
  note Scheduler, Heap: heap still holds `(30, Node, 1, TimerFire)` — it is a tomb
end

if: **case B** — re-register (overwrite) before fire
  Node -> Scheduler: set_timer(timer_id=1, delay=15, payload', t=12)
  Scheduler -> SeqPer: seq_per[Node] -> 2
  Scheduler -> Registry: registry[(Node, 1)] = 2 (overwrites the `1`)
  Scheduler -> Heap: heappush `(27, Node, 2, TimerFire id=1)`
  note Scheduler, Heap: heap now holds **both** the new entry and the old tomb
end

=: case B — at t=27 the newer entry pops first

Scheduler -> Heap: heappop -> `(27, Node, 2, TimerFire id=1)`
Scheduler -> Registry: `registry[(Node, 1)] == 2`? yes — alive
Scheduler => Node: on_timer(1, payload', 27)

=: later at t=30 the older entry pops

Scheduler -> Heap: heappop -> `(30, Node, 1, TimerFire id=1)`
Scheduler -> Registry: `registry[(Node, 1)] == 1`? no (current is 2 or absent) — **stale**
note Scheduler: silently skip; Node.on_timer is **not** invoked
```

## What this pins

**Three operations, one piece of state.** `set_timer`, `cancel_timer`,
and re-registration all manipulate `registry[(node_id, timer_id)]`.
The heap is append-only from cancellation's perspective.

**`registry` is the source of truth for "is this timer alive?"** The
heap is the source of truth for "when does it fire?" The two together
implement the lifecycle without heap surgery.

**Re-registration is overwrite, not replace.** Setting `timer_id=1` a
second time bumps the seq in the registry and pushes a new heap entry.
The first heap entry is now stale by definition (its `seq` no longer
matches the registry). When it eventually pops, the tombstone check
drops it silently.

**`cancel_timer` is O(1).** A single dict pop. The heap is untouched.
The cost is a small amount of garbage — stale entries that sit in the
heap until they pop — which at thesis scale (≤ 25 validators × ≤ 100
rounds × handful of timer types) is negligible.

**`cancel_timer` on an unknown id is a no-op.** Per
[[concepts/node-model]] §7, `cancel_timer` does not raise if the timer
was never set or was already cancelled. The
`registry.pop(..., None)` form realises this.

**No other event class touches the registry.** `Delivery` and
`PhaseAdvance` events cannot be cancelled. They always run (assuming
the run loop reaches them without hitting a deadline or predicate
stop).

**The two-entries-in-the-heap scenario is correct, not a bug.** Case B
deliberately leaves both `(27, Node, 2, ...)` and `(30, Node, 1, ...)`
in the heap. The earlier one fires; the later one tombstones at pop
time. This is the standard pattern in production schedulers (Linux's
hrtimer, libuv's timer queue, the JVM's `ScheduledThreadPoolExecutor`
when configured for cancel-via-replace).

## Cross-links

- Pop-side tombstone check: [[diagrams/scheduler/event-dispatch]]
  ("if event is TimerFire AND registry mismatch").
- `cancel_timer` contract: [[concepts/node-model]] §7.
- Re-registration semantics: [[concepts/node-model]] §7
  ("re-registering an existing `timer_id` overwrites the prior
  registration").
- Enqueue path that writes the registry:
  [[diagrams/scheduler/event-enqueue]].

## Source

Authored as part of T17 ([[concepts/simulation-design]]).

## Revisions

None.
