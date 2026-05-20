"""Unit tests for src/config/loader.py — ConfigError + load_config."""
from __future__ import annotations

import pathlib
import tempfile
import textwrap
import unittest

from config.loader import ConfigError, load_config
from _helpers import MINIMAL_YAML, write_yaml


class _LoaderTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class TestParse(_LoaderTestBase):
    def test_canonical_minimal_yaml_loads(self):
        path = write_yaml(self.tmp_path, MINIMAL_YAML)
        cfg = load_config(path)
        self.assertEqual(cfg.n, 4)
        self.assertEqual(cfg.t_max, 1000.0)

    def test_yaml_parse_error_wraps(self):
        path = write_yaml(self.tmp_path, "n: 4\n  bad indent: oops\n")
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("parse failed", str(cm.exception).lower())

    def test_top_level_must_be_dict(self):
        path = write_yaml(self.tmp_path, "- 1\n- 2\n- 3\n")
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_yaml_tags_rejected_by_safe_load(self):
        # safe_load refuses Python-object tags. The loader's parse-step
        # wraps the resulting yaml.YAMLError as ConfigError.
        path = write_yaml(self.tmp_path,
                          "n: !!python/object/apply:os.system ['echo']\n")
        with self.assertRaises(ConfigError):
            load_config(path)


class TestRequiredKeys(_LoaderTestBase):
    REQUIRED_TOP_LEVEL = (
        "n", "t_max", "seeds", "network",
        "adversary", "protocol_knobs", "workload",
    )

    def _yaml_without(self, key):
        # Build a YAML missing exactly one required top-level key.
        lines = []
        skip = False
        for line in MINIMAL_YAML.splitlines(keepends=True):
            stripped = line.split(":", 1)[0].strip()
            if not line.startswith((" ", "-")) and stripped == key:
                skip = True
                continue
            if skip and (line.startswith(" ") or line.startswith("-")):
                continue           # consume the value block of the removed key
            skip = False
            lines.append(line)
        return "".join(lines)

    def test_each_top_level_key_required(self):
        for key in self.REQUIRED_TOP_LEVEL:
            with self.subTest(missing=key):
                path = write_yaml(self.tmp_path, self._yaml_without(key))
                with self.assertRaises(ConfigError) as cm:
                    load_config(path)
                self.assertIn(key, str(cm.exception))

    def test_unknown_top_level_key_rejected(self):
        body = MINIMAL_YAML + "n_run: 99\n"     # typo of n_runs at top level
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("n_run", str(cm.exception))

    def test_seeds_n_runs_required(self):
        body = MINIMAL_YAML.replace("seeds:\n  n_runs: 1\n", "seeds: {}\n")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("n_runs", str(cm.exception))

    def test_network_phases_required(self):
        path = write_yaml(self.tmp_path,
                          "n: 4\nt_max: 1000.0\nseeds:\n  n_runs: 1\n"
                          "network: {}\nadversary: {}\n"
                          "protocol_knobs: {}\nworkload: {}\n")
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("phases", str(cm.exception))


class TestErrorFormat(_LoaderTestBase):
    def test_str_contains_path_key_and_reason(self):
        body = MINIMAL_YAML.replace("n: 4\n", "")    # drop required n
        path = write_yaml(self.tmp_path, body)
        try:
            load_config(path)
        except ConfigError as e:
            s = str(e)
            self.assertIn(str(path), s)
            self.assertIn("n", s)
            return
        self.fail("ConfigError not raised")


class TestCoercion(_LoaderTestBase):
    def test_t_max_string_is_coerced(self):
        body = MINIMAL_YAML.replace("t_max: 1000.0", 't_max: "1000"')
        path = write_yaml(self.tmp_path, body)
        cfg = load_config(path)
        self.assertEqual(cfg.t_max, 1000.0)
        self.assertIsInstance(cfg.t_max, float)

    def test_t_max_list_rejected(self):
        body = MINIMAL_YAML.replace("t_max: 1000.0", "t_max: [1000]")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("t_max", str(cm.exception))

    def test_n_int_coerced_from_string(self):
        body = MINIMAL_YAML.replace("n: 4", 'n: "4"')
        path = write_yaml(self.tmp_path, body)
        cfg = load_config(path)
        self.assertEqual(cfg.n, 4)
        self.assertIsInstance(cfg.n, int)

    def test_inf_t_end_loads(self):
        # YAML `.inf` parses as math.inf; the loader passes it through to
        # Phase, which accepts non-finite t_end only on the final phase
        # (validate_timeline enforces; the loader does not).
        path = write_yaml(self.tmp_path, MINIMAL_YAML)
        cfg = load_config(path)
        import math
        self.assertEqual(cfg.network[0].t_end, math.inf)


class TestLeafConstructionErrors(_LoaderTestBase):
    def test_unknown_delay_kind_surfaced(self):
        body = MINIMAL_YAML.replace("kind: constant", "kind: triangular")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("delay", str(cm.exception))
        self.assertIn("triangular", str(cm.exception))

    def test_constant_zero_delay_surfaced(self):
        body = MINIMAL_YAML.replace("delay: 50.0", "delay: 0")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("constant delay", str(cm.exception).lower())

    def test_opaque_sections_round_trip(self):
        body = MINIMAL_YAML.replace(
            "adversary: {}",
            "adversary: { strategy: delay-emission, fraction: 0.1 }",
        )
        path = write_yaml(self.tmp_path, body)
        cfg = load_config(path)
        # Opaque, but contents survive verbatim:
        self.assertEqual(cfg.adversary,
                         {"strategy": "delay-emission", "fraction": 0.1})


class TestCrossField(_LoaderTestBase):
    def test_zero_n_rejected(self):
        body = MINIMAL_YAML.replace("n: 4", "n: 0")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("n", str(cm.exception))

    def test_huge_n_rejected(self):
        # The sanity ceiling is 10_000 (spec § 4.5).
        body = MINIMAL_YAML.replace("n: 4", "n: 100000")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_zero_t_max_rejected(self):
        body = MINIMAL_YAML.replace("t_max: 1000.0", "t_max: 0")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("t_max", str(cm.exception))

    def test_nan_t_max_rejected(self):
        body = MINIMAL_YAML.replace("t_max: 1000.0", "t_max: .nan")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("t_max", str(cm.exception))

    def test_zero_n_runs_rejected(self):
        body = MINIMAL_YAML.replace("n_runs: 1", "n_runs: 0")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("n_runs", str(cm.exception))

    def test_partition_nodeid_out_of_range_rejected(self):
        # n = 4, so valid NodeIds are 0..3. NodeId 99 must be rejected.
        body = MINIMAL_YAML.replace(
            "partitions: []",
            "partitions:\n        - groups: [[0, 1], [99]]\n",
        )
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("99", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
