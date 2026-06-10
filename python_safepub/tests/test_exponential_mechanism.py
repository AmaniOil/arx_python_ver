import unittest

from safepub.exponential_mechanism import ExponentialMechanism


class TestExponentialMechanism(unittest.TestCase):
    def test_distribution_is_normalized_and_prefers_higher_score(self):
        mechanism = ExponentialMechanism[str](2.0, deterministic=True)
        mechanism.set_distribution(["low", "high"], [0.0, 10.0])
        distribution = mechanism.distribution()
        self.assertAlmostEqual(sum(item.probability for item in distribution), 1.0)
        self.assertGreater(distribution[1].probability, distribution[0].probability)

    def test_sampling_requires_distribution(self):
        mechanism = ExponentialMechanism[str](1.0, deterministic=True)
        with self.assertRaises(ValueError):
            mechanism.sample()


if __name__ == "__main__":
    unittest.main()
