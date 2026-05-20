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
