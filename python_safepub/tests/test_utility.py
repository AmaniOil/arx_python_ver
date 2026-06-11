import unittest

from safepub.utility import (
    arx_aecs_dp_score,
    arx_discernibility_dp_score,
    arx_entropy_dp_score,
    arx_loss_dp_score,
    arx_precision,
    arx_precision_dp_score,
)


class TestUtility(unittest.TestCase):
    def test_arx_precision_default_arithmetic_mean(self):
        result = arx_precision(
            ("age", "sex", "workclass"),
            (4, 0, 2),
            (4, 1, 2),
        )

        self.assertEqual(result.metric, "safepub_precision")
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

    def test_arx_precision_with_suppression(self):
        # MetricMDNMPrecision#getInformationLossInternal:
        # per dimension (unsuppressed * value + suppressed) / rowCount
        result = arx_precision(
            ("age", "sex"),
            (2, 0),
            (4, 1),
            record_count=10,
            suppressed_count=4,
        )

        self.assertAlmostEqual(
            result.values_by_attribute["age"], (6 * 0.5 + 4) / 10
        )
        self.assertAlmostEqual(result.values_by_attribute["sex"], (6 * 0.0 + 4) / 10)
        self.assertAlmostEqual(result.value, ((6 * 0.5 + 4) / 10 + 4 / 10) / 2)

    def test_arx_precision_with_zero_records_is_zero(self):
        result = arx_precision(
            ("age",),
            (2,),
            (4,),
            record_count=0,
            suppressed_count=0,
        )
        self.assertEqual(result.value, 0.0)

    def test_arx_precision_dp_score_counts_suppressed_records(self):
        # MetricMDNMPrecision#getScore: per dimension
        # unsuppressed * (level/height) + suppressed, then * -1/dimensions,
        # then / (k - 1).
        score = arx_precision_dp_score(
            ("age", "sex"),
            (2, 0),
            (4, 1),
            record_count=12,
            k=4,
            suppressed_count=5,
        )

        expected = -((7 * 0.5 + 5) + (7 * 0.0 + 5)) / 2 / 3
        self.assertAlmostEqual(score, expected)

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


class TestScoreFunctions(unittest.TestCase):
    """Hand-computed examples mirroring the Java score formulas.

    Shared setup: classes {("<50","male"): 6, (">=50","female"): 2} on 10
    sampled rows out of 12 records with k=4, so the class of size 2 and the
    2 non-sampled records are suppressed (suppressed total = 4).
    """

    CLASS_COUNTS = {("<50", "male"): 6, (">=50", "female"): 2}

    def test_arx_loss_dp_score(self):
        # MetricMDNMLoss#getScore: per dimension
        # suppressed_total + sum(share * count) over classes >= k,
        # then * -1/dimensions, / (k - 1).
        shares = [{"<50": 0.5, ">=50": 0.5}, {"male": 0.5, "female": 0.5}]
        score = arx_loss_dp_score(
            self.CLASS_COUNTS,
            shares,
            record_count=12,
            sample_count=10,
            k=4,
        )
        # dim0: 4 + 6*0.5 = 7; dim1: 7; sum 14; * -1/2 = -7; / 3
        self.assertAlmostEqual(score, -7.0 / 3.0)

    def test_arx_loss_dp_score_unknown_value_counts_as_whole_domain(self):
        shares = [{}]
        score = arx_loss_dp_score(
            {("anything",): 6},
            shares,
            record_count=6,
            sample_count=6,
            k=4,
        )
        # dim0: 0 + 6*1.0 = 6; * -1/1; / 3
        self.assertAlmostEqual(score, -2.0)

    def test_arx_discernibility_dp_score(self):
        # MetricSDNMDiscernability#getScore:
        # -(N * suppressed + sum count²) / (N * (k²/(k-1) + 1))
        score = arx_discernibility_dp_score(
            self.CLASS_COUNTS,
            record_count=12,
            sample_count=10,
            k=4,
        )
        # -(12*4 + 36) / (12 * (16/3 + 1)) = -84/76
        self.assertAlmostEqual(score, -84.0 / 76.0)

    def test_arx_discernibility_dp_score_k_one_sensitivity(self):
        score = arx_discernibility_dp_score(
            {("a",): 3},
            record_count=3,
            sample_count=3,
            k=1,
        )
        # -(3*0 + 9) / (3 * 5)
        self.assertAlmostEqual(score, -9.0 / 15.0)

    def test_arx_entropy_dp_score(self):
        # MetricMDNUEntropyPrecomputed#getScore.
        score = arx_entropy_dp_score(
            self.CLASS_COUNTS,
            ("*", "*"),
            record_count=12,
            sample_count=10,
            k=4,
        )
        # per dim: pooled 6² + outlier 2*12 + non-sampled 2*12 = 84
        # both dims: 168; * -1/(12*2) = -7; / (19/3) = -21/19
        self.assertAlmostEqual(score, -21.0 / 19.0)

    def test_arx_entropy_dp_score_root_value_counts_as_suppressed(self):
        score = arx_entropy_dp_score(
            {("*", "male"): 6},
            ("*", "*"),
            record_count=6,
            sample_count=6,
            k=4,
        )
        # dim0: value == root -> 6*6 = 36; dim1: pooled 6² = 36
        # sum 72; * -1/(6*2) = -6; / (19/3) = -18/19
        self.assertAlmostEqual(score, -18.0 / 19.0)

    def test_arx_aecs_dp_score(self):
        # MetricSDAECS#getScore: non-suppressed classes + 1 if any suppressed.
        score = arx_aecs_dp_score(
            self.CLASS_COUNTS,
            record_count=12,
            sample_count=10,
            k=4,
        )
        self.assertEqual(score, 2.0)

    def test_arx_aecs_dp_score_without_suppression(self):
        score = arx_aecs_dp_score(
            {("a",): 6},
            record_count=6,
            sample_count=6,
            k=4,
        )
        self.assertEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
