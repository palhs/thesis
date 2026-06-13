"""T47 — PBFT under packet loss: commits within tolerance + recovers via
view-change (TASKS.md Backlog 2026-05-21, due "when T47 is picked up").

Drives the full W3 stack (PBFTNode + Network with a non-zero per-phase
`p_drop` + Scheduler) and asserts the two halves of PBFT's loss behavior the
T47 heavy sweep relies on:

  - within tolerance, the protocol still makes progress (instances commit);
  - loss that stalls an instance's quorum triggers the view-change recovery
    path (PBFT_VIEW_CHANGE emitted), whereas the loss-free control does not
    rotate leaders.

Self-contained (does not import the sweep harness): a constant-delay loss
phase + short horizon + a low `vc_delay` so view-change fires inside the run.
The sub-second `delay` and modest horizon keep the suite fast; the heavy-tail
calibration is exercised by the sweep, not here.

Re-run:
  PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_heavy_loss -v
"""
import math
import unittest

from common import run_to_completion
from config.factory import build_run
from config.schema import Config, SeedsConfig
from network import DelayDist, Phase
from workload import WorkloadConfig, generate_batches

from pbft import PBFTNode, PBFT_VIEW_CHANGE

_PROPOSE = 1.0
_T_MAX = 90.0
_VC_DELAY = 8.0            # well above one ~0.6 s commit, low enough to fire
_DELAY_S = 0.2


def _run_pbft(n: int, seed: int, p_drop: float):
    """Build and run one honest PBFT instance over a constant-delay phase
    with the given Bernoulli loss; return the event records."""
    batches = [b"".join(b) for b in generate_batches(
        WorkloadConfig("poisson", 100.0, 512, 0.0),
        seed, n_opportunities=math.ceil(_T_MAX / _PROPOSE) + 2,
        interval=_PROPOSE)]
    phase = Phase(0.0, math.inf,
                  DelayDist("constant", {"delay": _DELAY_S}), p_drop=p_drop)
    config = Config(n=n, t_max=_T_MAX, seeds=SeedsConfig(n_runs=1),
                    network=(phase,), adversary={}, protocol_knobs={},
                    workload={})

    def make(node_id: int, global_seed: int) -> PBFTNode:
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n,
                        workload=batches if node_id == 0 else None,
                        propose_delay=_PROPOSE, initial_view=0,
                        vc_delay=_VC_DELAY)

    handle = build_run(config, seed, make)
    _, logger = run_to_completion(handle, t_max=_T_MAX)
    return logger.records


def _count(records, event_type: str) -> int:
    return sum(1 for r in records if r.event_type == event_type)


class TestPBFTLossRecovery(unittest.TestCase):
    def test_control_commits_and_does_not_rotate(self):
        # Loss-free control: PBFT commits many instances and never view-changes.
        records = _run_pbft(4, 0, p_drop=0.0)
        self.assertGreater(_count(records, "decided"), 0)
        self.assertEqual(_count(records, PBFT_VIEW_CHANGE), 0)

    def test_low_loss_still_commits(self):
        # Within tolerance, the protocol keeps making progress under loss.
        decided = sum(_count(_run_pbft(4, s, p_drop=0.05), "decided")
                      for s in range(3))
        self.assertGreater(decided, 0)

    def test_loss_triggers_view_change_recovery(self):
        # Heavier loss stalls quorums; the per-instance view-change timer
        # fires, engaging the recovery path. Summed over a few seeds so the
        # fixed-seed outcome is robust, not flaky.
        view_changes = sum(_count(_run_pbft(4, s, p_drop=0.20),
                                  PBFT_VIEW_CHANGE) for s in range(3))
        self.assertGreater(view_changes, 0)


if __name__ == "__main__":
    unittest.main()
