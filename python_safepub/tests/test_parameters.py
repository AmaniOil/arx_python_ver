import math
import unittest

from safepub.parameters import ParameterCalculation


class TestParameterCalculation(unittest.TestCase):
    def test_beta_matches_safepub_formula(self):
        parameters = ParameterCalculation(2.0, 1e-5).as_parameters()
        self.assertAlmostEqual(parameters.beta, 1.0 - math.exp(-2.0))
        self.assertAlmostEqual(parameters.gamma, 1.0 - math.exp(-4.0))

    def test_known_k_values_from_python_port(self):
        cases = [
            (2.0, 0.5, 6),
            (2.0, 0.3, 10),
            (2.0, 0.1, 17),
            (2.0, 1e-5, 114),
        ]
        for epsilon, delta, expected_k in cases:
            with self.subTest(epsilon=epsilon, delta=delta):
                self.assertEqual(ParameterCalculation(epsilon, delta).get_k(), expected_k)

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            ParameterCalculation(0.0, 0.1)
        with self.assertRaises(ValueError):
            ParameterCalculation(1.0, 1.0)


if __name__ == "__main__":
    unittest.main()
