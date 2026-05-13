# Scheduler — Event Dispatch (Run Loop)

> One iteration of `Scheduler.run()`. Shows pop, virtual-time
> advancement, deadline check, tombstone check, observability sink,
> dispatch by event type, and stop-predicate check. The three exit
> paths (`quiescence`, `deadline`, `predicate`) are drawn explicitly.
>
> Part of the T17 contract diagram set. Reading order: comes after
> [[diagrams/scheduler/event-enqueue]]; assumes the heap has been
> populated.

## Diagram

```swimlanes
title: Scheduler — one iteration of run()

order: Caller, Scheduler, Heap, Registry, EventSink, Node
autonumber

if: heap is empty
  Scheduler => Caller: return RunResult(stopped_by='quiescence', now, events_processed)
end

Scheduler -> Heap: heappop
Heap --> Scheduler: `(t, node_id, seq, event)`
Scheduler -> Scheduler: self._now = t

if: t_max set AND now >= t_max
  Scheduler => Caller: return RunResult(stopped_by='deadline', now, events_processed)
end

if: event is TimerFire AND `registry[(node_id, event.timer_id)] != event.seq`
  note Scheduler, Registry: **stale TimerFire** — silently skip; control jumps to next iteration
else
  Scheduler -> EventSink: (if event_sink set) `event_sink(t, node_id, seq, event)`
  Scheduler -> Node: dispatch by event class — **Delivery** → `on_message`, **TimerFire** → `on_timer`, **PhaseAdvance** → `network.advance_phase`
end

if: stop_when set AND `stop_when() == true`
  Scheduler => Caller: return RunResult(stopped_by='predicate', now, events_processed)
end

-: control returns to top of loop
```

## What this pins

**The loop body is sequential, not deeply nested.** Four conditional
gates fire in order: quiescence check, deadline check, tombstone
check, predicate check. There is no other branching. Anyone reading
the run loop should be able to walk these four conditionals from top
to bottom and see every exit path.

**Three exit paths, each labeled.** `RunResult.stopped_by` is one of
`'quiescence' | 'deadline' | 'predicate'`. T40 uses this label when
projecting one row of `results.csv` so failed (deadline-stopped) runs
are distinguishable from completed (predicate-stopped) and natural-end
(quiescence-stopped) runs.

**The tombstone check is between pop and dispatch.** A stale
`TimerFire` is silently dropped — `Node.on_timer` is *not* invoked.
The event sink is also skipped for stale events; the silent skip is
total. This matches the lazy cancellation pattern in
[[diagrams/scheduler/timer-lifecycle]].

**The event sink fires before dispatch, not after.** Order is: pop →
tombstone check → sink → dispatch → predicate check. A handler that
raises during dispatch will have already been recorded by the sink.
T24 may choose to also record exceptions; that is T24's instrumentation
choice, not the scheduler's.

**`self._now = t` is the only write of `now`.** Every other component
reads `now` via the `t` parameter that flows through handler
signatures. No public `now()` accessor exists on the scheduler beyond
a read-only property; the underlying field is private.

**An exception in a handler propagates.** If `Node.on_message`,
`Node.on_timer`, or `Network.advance_phase` raises, the exception
propagates out of `run()`. The scheduler does not catch. T27's
determinism regression test relies on this: a non-deterministic bug
surfaces as a divergence between two seed-identical runs, and the loud
exception is the regression signal.

**`stop_when()` is zero-argument.** The harness builds it as a closure
that captures whatever state it cares about (typically a counter of
`decided` events maintained outside the scheduler). The scheduler does
not pass a `SchedulerView` object; the predicate inspects external
state, not scheduler internals.

## Cross-links

- Scheduler API surface: [[concepts/simulation-design]] (forthcoming).
- Tie-break key: [[concepts/node-model]] §8.3.
- Tombstone mechanism in detail: [[diagrams/scheduler/timer-lifecycle]].
- Failure modes catalogue: [[diagrams/scheduler/constraints]].
- Enqueue-side counterpart: [[diagrams/scheduler/event-enqueue]].

## Source

Authored as part of T17 ([[concepts/simulation-design]]).

## Revisions

None.
