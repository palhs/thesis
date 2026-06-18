import unittest
from adversary import equivocate_config as ec


class TestEquivocateConfig(unittest.TestCase):
    def test_per_protocol_f_grid(self):
        assert ec.F_VALUES["pbft"] == (0.0, 0.10, 0.20, 0.33, 0.40, 0.50)
        assert ec.F_VALUES["casper-ffg"] == (0.0, 0.10, 0.20, 0.33, 0.40, 0.50)
        assert ec.F_VALUES["snowman"] == (0.0, 0.10, 0.20, 0.33)

    def test_n_and_seeds(self):
        assert ec.N_VALUES == (10, 25)
        assert ec.SEEDS == tuple(range(20))

    def test_t_max(self):
        assert ec.T_MAX == ec.WINDOW_S + ec.BUFFER_S
