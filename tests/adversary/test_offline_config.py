import unittest
from adversary import offline_config as oc


class TestOfflineConfig(unittest.TestCase):
    def test_per_protocol_f_grid(self):
        assert oc.F_VALUES["pbft"] == (0.0, 0.10, 0.20, 0.33, 0.40)
        assert oc.F_VALUES["casper-ffg"] == (0.0, 0.10, 0.20, 0.33, 0.40)
        assert oc.F_VALUES["snowman"] == (0.0, 0.10, 0.20, 0.33)

    def test_no_magnitude_axis(self):
        assert not hasattr(oc, "M_VALUES")

    def test_n_and_seeds(self):
        assert oc.N_VALUES == (10, 25)
        assert oc.SEEDS == tuple(range(20))
