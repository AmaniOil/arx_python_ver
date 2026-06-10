import unittest

from safepub.criterion import EDDifferentialPrivacy
from safepub.tabular import safe_pub_anonymize


class TestCriterionAndTabular(unittest.TestCase):
    def test_criterion_samples_deterministically(self):
        criterion = EDDifferentialPrivacy(
            2.0,
            0.5,
            data_dependent=False,
            deterministic=True,
        )
        first = criterion.initialize(20).sampled_indices
        second = EDDifferentialPrivacy(
            2.0,
            0.5,
            data_dependent=False,
            deterministic=True,
        ).initialize(20)
        self.assertEqual(first, second.sampled_indices)
        self.assertEqual(criterion.k, 6)

    def test_data_dependent_defaults_to_ten_percent_search_budget(self):
        criterion = EDDifferentialPrivacy(2.0, 0.5, data_dependent=True)
        criterion.initialize(20)
        self.assertAlmostEqual(criterion.dp_search_budget, 0.2)

    def test_tiny_tabular_anonymization_runs(self):
        data = [
            {"age": "34", "gender": "male"},
            {"age": "45", "gender": "female"},
            {"age": "66", "gender": "male"},
            {"age": "70", "gender": "female"},
            {"age": "36", "gender": "male"},
            {"age": "52", "gender": "female"},
            {"age": "39", "gender": "male"},
            {"age": "61", "gender": "female"},
            {"age": "44", "gender": "male"},
            {"age": "73", "gender": "female"},
            {"age": "31", "gender": "male"},
            {"age": "58", "gender": "female"},
        ]
        hierarchies = {
            "age": {
                value: (value, "<50" if int(value) < 50 else ">=50", "*")
                for value in {row["age"] for row in data}
            },
            "gender": {
                "male": ("male", "*"),
                "female": ("female", "*"),
            },
        }

        result = safe_pub_anonymize(
            data,
            ("age", "gender"),
            hierarchies,
            epsilon=2.0,
            delta=0.5,
            deterministic=True,
        )
        self.assertEqual(result.k, 6)
        self.assertTrue(result.rows)
        self.assertGreaterEqual(min(result.equivalence_class_counts.values()), result.k)
        self.assertEqual(result.utility.metric, "arx_precision")
        self.assertAlmostEqual(result.quality_loss, result.utility.value)

    def test_data_dependent_tabular_anonymization_uses_exponential_search(self):
        data = [
            {"age": str(30 + (index % 20)), "gender": "male" if index % 2 else "female"}
            for index in range(40)
        ]
        hierarchies = {
            "age": {
                value: (value, "<40" if int(value) < 40 else ">=40", "*")
                for value in {row["age"] for row in data}
            },
            "gender": {
                "male": ("male", "*"),
                "female": ("female", "*"),
            },
        }

        result = safe_pub_anonymize(
            data,
            ("age", "gender"),
            hierarchies,
            epsilon=2.0,
            delta=0.5,
            deterministic=True,
            data_dependent=True,
            dp_search_budget=0.2,
        )

        self.assertEqual(result.search_strategy, "exponential_mechanism")
        self.assertEqual(result.search_expansion_limit, 5)
        self.assertIsNotNone(result.search_result)
        self.assertEqual(result.search_result.steps[0].pivot, (2, 1))
        self.assertGreaterEqual(min(result.equivalence_class_counts.values()), result.k)


if __name__ == "__main__":
    unittest.main()
