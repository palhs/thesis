"""Family B — Network-delay experiment harness (T46).

A thin orchestration/config layer OVER the existing honest protocol
baselines (src/pbft, src/pos, src/snowman) — the delay analogue of the
T41 scaling sweep at src/output/. It injects a non-trivial network-delay
timeline (uniform[100,500] ms or exponential mean-300 ms; see
[[concepts/experiment-matrix-runs]] §2), rescales the Casper FFG
slot_duration to stay coherent with E[delay] (the §5 FFG coherence rule),
runs each honest protocol over a window-plus-buffer horizon, and clips the
finalization tail back to the measurement window W per the Week-9 locked
buffer/clip methodology.

It does NOT modify any shared infrastructure (src/scheduler, src/nodes,
src/network, src/event_log) nor the protocol packages: every knob it needs
(network Phase, slot_duration, propose_delay, t_max) is already an existing
constructor / Config argument. T46 covers EXACTLY two timelines
(delay-uniform, delay-exponential); the remaining four Family B timelines
(heavy-tail, loss, partial-sync-gst) are T47's.

Design contract: wiki/experiments/2026-06-10_delay-moderate.md
"""
