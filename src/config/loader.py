"""YAML config loader (T27 spec § 4).

Five-step pipeline: parse → required-keys → type-coercion → leaf-construct →
cross-field. This module owns steps 4.1 + 4.2 + 4.3 + 4.4 today; Task 9
fills 4.5 (cross-field validation).

Every failure is funneled into ConfigError(path, key_path, message). No
other exception type escapes load_config — yaml.YAMLError and ValueError
from leaf __post_init__ validators are caught and re-raised.
"""
from __future__ import annotations

import math
import pathlib
from typing import Any

import yaml

from .schema import Config, SeedsConfig
from network.phases import DelayDist, Partition, Phase


class ConfigError(ValueError):
    """Loader / cross-field validation failure.

    `__str__` returns `f"{path}: {key_path}: {message}"` — a caller printing
    the exception gets a one-line locator. Subclass of ValueError so
    pytest.raises(ValueError) catches it.
    """
    def __init__(self, path: pathlib.Path | str, key_path: str, message: str):
        self.path = pathlib.Path(path)
        self.key_path = key_path
        self.message = message
        super().__init__(f"{self.path}: {self.key_path}: {self.message}")


_REQUIRED_TOP_LEVEL = frozenset((
    "n", "t_max", "seeds", "network",
    "adversary", "protocol_knobs", "workload",
))


def load_config(path: str | pathlib.Path) -> Config:
    """Load and fully validate a YAML config file. Returns a frozen Config.

    Raises ConfigError on any malformed input.
    """
    path = pathlib.Path(path)

    # --- 4.1 Parse -----------------------------------------------------
    try:
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(path, "<root>",
                          f"YAML parse failed: {e}") from None
    if not isinstance(raw, dict):
        raise ConfigError(path, "<root>",
                          f"top level must be a mapping, got "
                          f"{type(raw).__name__}")

    # --- 4.2 Required-key check ----------------------------------------
    keys = set(raw)
    missing = _REQUIRED_TOP_LEVEL - keys
    if missing:
        first = sorted(missing)[0]
        raise ConfigError(path, first, "missing required top-level key")
    unknown = keys - _REQUIRED_TOP_LEVEL
    if unknown:
        first = sorted(unknown)[0]
        raise ConfigError(path, first, "unknown top-level key")

    seeds_raw = raw["seeds"]
    if not isinstance(seeds_raw, dict):
        raise ConfigError(path, "seeds",
                          f"must be a mapping, got {type(seeds_raw).__name__}")
    if "n_runs" not in seeds_raw:
        raise ConfigError(path, "seeds.n_runs",
                          "missing required key")
    extra_seeds = set(seeds_raw) - {"n_runs"}
    if extra_seeds:
        first = sorted(extra_seeds)[0]
        raise ConfigError(path, f"seeds.{first}", "unknown key")

    network_raw = raw["network"]
    if not isinstance(network_raw, dict):
        raise ConfigError(path, "network",
                          f"must be a mapping, got "
                          f"{type(network_raw).__name__}")
    if "phases" not in network_raw:
        raise ConfigError(path, "network.phases",
                          "missing required key")
    extra_net = set(network_raw) - {"phases"}
    if extra_net:
        first = sorted(extra_net)[0]
        raise ConfigError(path, f"network.{first}", "unknown key")

    phases_raw = network_raw["phases"]
    if not isinstance(phases_raw, list):
        raise ConfigError(path, "network.phases",
                          f"must be a list, got {type(phases_raw).__name__}")
    for i, ph in enumerate(phases_raw):
        if not isinstance(ph, dict):
            raise ConfigError(path, f"network.phases[{i}]",
                              f"must be a mapping, got {type(ph).__name__}")
        for req in ("t_start", "t_end", "delay"):
            if req not in ph:
                raise ConfigError(path,
                                  f"network.phases[{i}].{req}",
                                  "missing required key")
        dly = ph["delay"]
        if not isinstance(dly, dict):
            raise ConfigError(path,
                              f"network.phases[{i}].delay",
                              f"must be a mapping, got "
                              f"{type(dly).__name__}")
        for req in ("kind", "params"):
            if req not in dly:
                raise ConfigError(path,
                                  f"network.phases[{i}].delay.{req}",
                                  "missing required key")

    for opaque in ("adversary", "protocol_knobs", "workload"):
        v = raw[opaque]
        if not isinstance(v, dict):
            raise ConfigError(path, opaque,
                              f"must be a mapping, got {type(v).__name__}")

    # --- 4.3 + 4.4 Type coercion + leaf construction --------------------
    try:
        n = int(raw["n"])
    except (TypeError, ValueError) as e:
        raise ConfigError(path, "n", f"must coerce to int: {e}") from None

    try:
        t_max = float(raw["t_max"])
    except (TypeError, ValueError) as e:
        raise ConfigError(path, "t_max",
                          f"must coerce to float: {e}") from None

    try:
        n_runs = int(seeds_raw["n_runs"])
    except (TypeError, ValueError) as e:
        raise ConfigError(path, "seeds.n_runs",
                          f"must coerce to int: {e}") from None
    seeds = SeedsConfig(n_runs=n_runs)

    phases: list[Phase] = []
    for i, ph_raw in enumerate(phases_raw):
        key_prefix = f"network.phases[{i}]"
        try:
            t_start = float(ph_raw["t_start"])
            t_end = float(ph_raw["t_end"])
        except (TypeError, ValueError) as e:
            raise ConfigError(path, f"{key_prefix}.t_start/t_end",
                              f"must coerce to float: {e}") from None

        dly_raw = ph_raw["delay"]
        if not isinstance(dly_raw["params"], dict):
            raise ConfigError(path, f"{key_prefix}.delay.params",
                              f"must be a mapping, got "
                              f"{type(dly_raw['params']).__name__}")
        try:
            delay = DelayDist(kind=str(dly_raw["kind"]),
                              params=dict(dly_raw["params"]))
        except ValueError as e:
            raise ConfigError(path, f"{key_prefix}.delay",
                              str(e)) from None

        if "p_drop" in ph_raw:
            try:
                p_drop = float(ph_raw["p_drop"])
            except (TypeError, ValueError) as e:
                raise ConfigError(path, f"{key_prefix}.p_drop",
                                  f"must coerce to float: {e}") from None
        else:
            p_drop = 0.0

        partitions_raw = ph_raw.get("partitions", [])
        if not isinstance(partitions_raw, list):
            raise ConfigError(path, f"{key_prefix}.partitions",
                              f"must be a list, got "
                              f"{type(partitions_raw).__name__}")
        parts: list[Partition] = []
        for j, part_raw in enumerate(partitions_raw):
            ppref = f"{key_prefix}.partitions[{j}]"
            if not isinstance(part_raw, dict):
                raise ConfigError(path, ppref,
                                  f"must be a mapping, got "
                                  f"{type(part_raw).__name__}")
            if "groups" not in part_raw:
                raise ConfigError(path, f"{ppref}.groups",
                                  "missing required key")
            groups_raw = part_raw["groups"]
            if not isinstance(groups_raw, list):
                raise ConfigError(path, f"{ppref}.groups",
                                  f"must be a list, got "
                                  f"{type(groups_raw).__name__}")
            try:
                groups = tuple(tuple(int(nid) for nid in g) for g in groups_raw)
            except (TypeError, ValueError) as e:
                raise ConfigError(path, f"{ppref}.groups",
                                  f"NodeIds must be ints: {e}") from None
            sym = bool(part_raw.get("symmetric", True))
            parts.append(Partition(groups=groups, symmetric=sym))

        try:
            phases.append(Phase(t_start=t_start, t_end=t_end,
                                delay=delay, p_drop=p_drop,
                                partitions=tuple(parts)))
        except ValueError as e:
            raise ConfigError(path, key_prefix, str(e)) from None

    config = Config(
        n=n,
        t_max=t_max,
        seeds=seeds,
        network=tuple(phases),
        adversary=dict(raw["adversary"]),
        protocol_knobs=dict(raw["protocol_knobs"]),
        workload=dict(raw["workload"]),
    )

    # --- 4.5 Cross-field validation -------------------------------------
    _validate_config(config, path)
    return config


def _validate_config(config: Config, path: pathlib.Path) -> None:
    """Step 4.5: cross-field checks.

    Raises ConfigError naming the first violation found.
    """
    if not (1 <= config.n <= 10_000):
        raise ConfigError(
            path, "n",
            f"must be in [1, 10000], got {config.n}")
    if not math.isfinite(config.t_max) or config.t_max <= 0:
        raise ConfigError(
            path, "t_max",
            f"must be a positive finite float, got {config.t_max}")
    if config.seeds.n_runs < 1:
        raise ConfigError(
            path, "seeds.n_runs",
            f"must be >= 1, got {config.seeds.n_runs}")

    valid_ids = set(range(config.n))
    for i, ph in enumerate(config.network):
        for j, part in enumerate(ph.partitions):
            for nid in (nid for g in part.groups for nid in g):
                if nid not in valid_ids:
                    raise ConfigError(
                        path,
                        f"network.phases[{i}].partitions[{j}]",
                        f"NodeId {nid} not in range(n)={config.n}")
