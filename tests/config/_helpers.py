"""Test helpers for the T27 config suite."""
from __future__ import annotations

import textwrap

# Canonical minimal valid YAML — used by every loader / factory / e2e test.
# 4 nodes, single-phase constant-delay network, t_max=1000, n_runs=1, all
# three opaque sections empty.
MINIMAL_YAML = textwrap.dedent("""\
    n: 4
    t_max: 1000.0
    seeds:
      n_runs: 1
    network:
      phases:
        - t_start: 0
          t_end: .inf
          delay:
            kind: constant
            params: { delay: 50.0 }
          p_drop: 0.0
          partitions: []
    adversary: {}
    protocol_knobs: {}
    workload: {}
""")


def write_yaml(tmp_path, body: str = MINIMAL_YAML):
    """Materialise `body` as a temp YAML file and return its path."""
    p = tmp_path / "cfg.yaml"
    p.write_text(body)
    return p


from nodes import HaltReason, Message, Node


class MinimalNode(Node):
    """Concrete Node used by T27 factory + e2e tests. Tiny by design — its
    sole job is to produce observable events so the determinism contract
    can be exercised without binding to T28+ protocol semantics.

    Behaviour: on _on_start, broadcast a single "PING" carrying a random
    draw from self.rng. On _on_message, halt(RUN_END). _on_timer is
    defensive — never fired by this scenario.
    """

    def __init__(self, node_id, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)

    def _on_start(self, t):
        self.broadcast("PING", {"r": self.rng.random()}, t)

    def _on_message(self, msg, t):
        self.halt(HaltReason.RUN_END, t)

    def _on_timer(self, timer_id, payload, t):
        raise AssertionError("MinimalNode never sets a timer")
