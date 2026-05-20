"""Six-phase bootstrap from a Config + global_seed (T27 spec § 5).

build_run() composes Scheduler + Network + Nodes in the canonical order
pinned by simulation-design.md (the wiki six-phase bootstrap) and by spec
§ 5. Returns a RunHandle. The caller calls handle.scheduler.run() and
optionally wires handle.scheduler.event_sink before that.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Callable

from network import Network
from nodes import Node
from scheduler import Scheduler

from .schema import Config, RunHandle

NodeId = int
NodeFactory = Callable[[NodeId, int], Node]
#               (node_id, global_seed) -> Node


def build_run(config: Config,
              global_seed: int,
              node_factory: NodeFactory) -> RunHandle:
    """Construct one run from `config` and `global_seed`.

    Construction order (matches simulation-design.md six-phase bootstrap):
      1. Scheduler()
      2. Network(scheduler, config.network, global_seed)
      3. For each NodeId in range(config.n):
           node = node_factory(nid, global_seed)
           assert node.id == nid
           network.register(node); scheduler.bind(node); network.bind(node)
      4. scheduler.bind_network(network)
      5. network.start()
      6. For each NodeId in sorted order: node.start(t=0.0)

    Returns a RunHandle whose `nodes` field is an immutable mapping view.
    """
    scheduler = Scheduler()
    network = Network(scheduler, config.network, global_seed)

    nodes: dict[NodeId, Node] = {}
    for nid in range(config.n):
        node = node_factory(nid, global_seed)
        assert node.id == nid, (
            f"node_factory returned node.id={node.id} for requested nid={nid}"
        )
        network.register(node)
        scheduler.bind(node)
        network.bind(node)
        nodes[nid] = node

    scheduler.bind_network(network)
    network.start()

    for nid in sorted(nodes):
        nodes[nid].start(t=0.0)

    return RunHandle(scheduler=scheduler, network=network,
                     nodes=MappingProxyType(nodes))
