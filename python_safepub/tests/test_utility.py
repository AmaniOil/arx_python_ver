import unittest

from safepub.utility import arx_precision, arx_precision_dp_score


class TestUtility(unittest.TestCase):
    def test_arx_precision_default_arithmetic_mean(self):
        result = arx_precision(
            ("age", "sex", "workclass"),
            (4, 0, 2),
            (4, 1, 2),
        )

        self.assertEqual(result.metric, "arx_precision")
        self.assertEqual(result.aggregate_function, "ARITHMETIC_MEAN")
        self.assertAlmostEqual(result.value, (1.0 + 0.0 + 1.0) / 3.0)
        self.assertEqual(
            result.values_by_attribute,
            {"age": 1.0, "sex": 0.0, "workclass": 1.0},
        )

    def test_arx_precision_with_arx_generalization_factor(self):
        result = arx_precision(
            ("age",),
            (2,),
            (4,),
            generalization_factor=0.5,
        )

        self.assertAlmostEqual(result.value, 0.25)

    def test_arx_precision_dp_score_is_higher_for_lower_loss(self):
        top_score = arx_precision_dp_score(
            ("age", "sex"),
            (4, 1),
            (4, 1),
            record_count=12,
            k=4,
        )
        lower_loss_score = arx_precision_dp_score(
            ("age", "sex"),
            (2, 0),
            (4, 1),
            record_count=12,
            k=4,
        )

        self.assertAlmostEqual(top_score, -4.0)
        self.assertAlmostEqual(lower_loss_score, -1.0)
        self.assertGreater(lower_loss_score, top_score)


if __name__ == "__main__":
    unittest.main()
