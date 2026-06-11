import unittest

from safepub.criterion import EDDifferentialPrivacy
from safepub.tabular import (
    SCORE_FUNCTIONS,
    SUPPRESSED_VALUE,
    _classification_dp_score,
    _domain_share_maps,
    _root_values,
    equivalence_class_counts,
    resolve_generalization_scheme,
    safe_pub_anonymize,
)


def _tiny_data():
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
    return data, hierarchies


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

    def test_data_independent_requires_generalization_scheme(self):
        data, hierarchies = _tiny_data()
        with self.assertRaises(ValueError):
            safe_pub_anonymize(
                data,
                ("age", "gender"),
                hierarchies,
                epsilon=2.0,
                delta=0.5,
                deterministic=True,
            )

    def test_data_independent_fixed_scheme(self):
        data, hierarchies = _tiny_data()
        result = safe_pub_anonymize(
            data,
            ("age", "gender"),
            hierarchies,
            epsilon=2.0,
            delta=0.5,
            deterministic=True,
            generalization_levels={"age": 2, "gender": 1},
        )
        self.assertEqual(result.search_strategy, "fixed_scheme")
        self.assertEqual(result.levels, (2, 1))
        # ARX measures conventional information loss for fixed schemes; the
        # DP score only exists for data-dependent runs.
        self.assertIsNone(result.score)
        self.assertEqual(result.k, 6)
        # ARX-style output: one output row per input row.
        self.assertEqual(len(result.rows), len(data))
        self.assertEqual(result.utility.metric, "arx_precision")
        self.assertAlmostEqual(result.quality_loss, result.utility.value)

    def test_output_suppresses_non_sampled_and_small_class_rows(self):
        data, hierarchies = _tiny_data()
        # Levels below the top so generalized rows are distinguishable from
        # fully suppressed rows.
        result = safe_pub_anonymize(
            data,
            ("age", "gender"),
            hierarchies,
            epsilon=2.0,
            delta=0.5,
            deterministic=True,
            generalization_levels={"age": 1, "gender": 0},
        )

        sampled = set(result.sampled_indices)
        suppressed_row = {attribute: SUPPRESSED_VALUE for attribute in data[0]}
        suppressed_sample_rows = 0
        for index, row in enumerate(result.rows):
            if index not in sampled:
                self.assertEqual(row, suppressed_row)
                continue
            key = tuple(row[attribute] for attribute in ("age", "gender"))
            if row == suppressed_row:
                suppressed_sample_rows += 1
            else:
                self.assertGreaterEqual(result.equivalence_class_counts[key], result.k)
        self.assertEqual(suppressed_sample_rows, result.suppressed_sample_count)
        self.assertEqual(result.non_sampled_count, len(data) - len(sampled))

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
        # Like ARX's ILScore, the reported score of the solution is negative
        # (higher is better) and matches the tracked best score.
        self.assertIsNotNone(result.score)
        self.assertLess(result.score, 0.0)
        self.assertEqual(result.score, result.search_result.best_score)
        # Every step's candidate set follows the lattice only; with the
        # expansion limit equal to the local lattice size minus one, the
        # search may visit any transformation, including ones with small
        # classes, which end up suppressed instead of rejected.
        self.assertEqual(len(result.rows), len(data))

    def test_data_dependent_rejects_fixed_scheme_arguments(self):
        data, hierarchies = _tiny_data()
        with self.assertRaises(ValueError):
            safe_pub_anonymize(
                data,
                ("age", "gender"),
                hierarchies,
                epsilon=2.0,
                delta=0.5,
                deterministic=True,
                data_dependent=True,
                generalization_degree="medium",
            )


class TestScoreFunctionSelection(unittest.TestCase):
    def _search_data(self):
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
        return data, hierarchies

    def test_every_score_function_runs(self):
        data, hierarchies = self._search_data()
        negative_models = {
            "arx_precision",
            "arx_loss",
            "arx_discernibility",
            "arx_entropy",
        }
        for metric in SCORE_FUNCTIONS:
            with self.subTest(metric=metric):
                response_variables = (
                    ("gender",) if metric == "arx_classification" else None
                )
                result = safe_pub_anonymize(
                    data,
                    ("age", "gender"),
                    hierarchies,
                    epsilon=2.0,
                    delta=0.5,
                    deterministic=True,
                    data_dependent=True,
                    dp_search_budget=0.2,
                    utility_metric=metric,
                    response_variables=response_variables,
                )
                self.assertEqual(result.score_function, metric)
                self.assertIsNotNone(result.score)
                if metric in negative_models:
                    self.assertLessEqual(result.score, 0.0)
                else:
                    # AECS and Classification scores are positive in Java too.
                    self.assertGreaterEqual(result.score, 0.0)

    def test_metric_aliases_are_accepted(self):
        data, hierarchies = self._search_data()
        result = safe_pub_anonymize(
            data,
            ("age", "gender"),
            hierarchies,
            epsilon=2.0,
            delta=0.5,
            deterministic=True,
            data_dependent=True,
            utility_metric="non_uniform_entropy",
        )
        self.assertEqual(result.score_function, "arx_entropy")

    def test_classification_requires_response_variables(self):
        data, hierarchies = self._search_data()
        with self.assertRaises(ValueError):
            safe_pub_anonymize(
                data,
                ("age", "gender"),
                hierarchies,
                epsilon=2.0,
                delta=0.5,
                deterministic=True,
                data_dependent=True,
                utility_metric="arx_classification",
            )

    def test_response_variables_require_classification(self):
        data, hierarchies = self._search_data()
        with self.assertRaises(ValueError):
            safe_pub_anonymize(
                data,
                ("age", "gender"),
                hierarchies,
                epsilon=2.0,
                delta=0.5,
                deterministic=True,
                data_dependent=True,
                utility_metric="arx_precision",
                response_variables=("gender",),
            )

    def test_unknown_metric_raises(self):
        data, hierarchies = self._search_data()
        with self.assertRaises(ValueError):
            safe_pub_anonymize(
                data,
                ("age", "gender"),
                hierarchies,
                epsilon=2.0,
                delta=0.5,
                deterministic=True,
                data_dependent=True,
                utility_metric="no_such_metric",
            )


class TestScoreHelpers(unittest.TestCase):
    HIERARCHIES = {
        "age": {
            "34": ("34", "<50", "*"),
            "45": ("45", "<50", "*"),
            "36": ("36", "<50", "*"),
            "39": ("39", "<50", "*"),
            "44": ("44", "<50", "*"),
            "66": ("66", ">=50", "*"),
            "70": ("70", ">=50", "*"),
            "73": ("73", ">=50", "*"),
        },
        "gender": {
            "male": ("male", "*"),
            "female": ("female", "*"),
        },
    }

    def test_domain_share_maps(self):
        maps = _domain_share_maps(self.HIERARCHIES["age"], 2)
        self.assertAlmostEqual(maps[0]["34"], 1.0 / 8.0)
        self.assertAlmostEqual(maps[1]["<50"], 5.0 / 8.0)
        self.assertAlmostEqual(maps[1][">=50"], 3.0 / 8.0)
        self.assertAlmostEqual(maps[2]["*"], 1.0)

    def test_root_values(self):
        roots = _root_values(("age", "gender"), self.HIERARCHIES, (2, 1))
        self.assertEqual(roots, ("*", "*"))

    def test_classification_dp_score_non_qi_target(self):
        # MetricSDClassification#getScore: each class of size >= k adds the
        # frequency of its most frequent raw target value; divided by
        # k * number of response variables.
        data = [
            {"age": "34", "gender": "male", "job": "A"},
            {"age": "45", "gender": "male", "job": "A"},
            {"age": "36", "gender": "male", "job": "B"},
            {"age": "39", "gender": "male", "job": "B"},
            {"age": "44", "gender": "male", "job": "B"},
            {"age": "66", "gender": "female", "job": "A"},
            {"age": "70", "gender": "female", "job": "A"},
            {"age": "73", "gender": "female", "job": "A"},
        ]
        levels = (1, 0)
        sampled = tuple(range(len(data)))
        counts = equivalence_class_counts(
            data, ("age", "gender"), self.HIERARCHIES, levels, sampled
        )

        score = _classification_dp_score(
            data,
            ("age", "gender"),
            self.HIERARCHIES,
            levels,
            (2, 1),
            sampled,
            counts,
            3,
            ("job",),
        )
        # Classes: (<50, male) -> jobs [A,A,B,B,B], top1 = 3
        #          (>=50, female) -> jobs [A,A,A], top1 = 3
        # score = 6 / (k * 1) = 6 / 3
        self.assertAlmostEqual(score, 2.0)

    def test_classification_dp_score_qi_target_scales_with_level(self):
        data = [
            {"age": "34", "gender": "male"},
            {"age": "45", "gender": "male"},
            {"age": "36", "gender": "male"},
            {"age": "39", "gender": "male"},
            {"age": "44", "gender": "male"},
            {"age": "66", "gender": "female"},
            {"age": "70", "gender": "female"},
            {"age": "73", "gender": "female"},
        ]
        levels = (1, 0)
        sampled = tuple(range(len(data)))
        counts = equivalence_class_counts(
            data, ("age", "gender"), self.HIERARCHIES, levels, sampled
        )

        score = _classification_dp_score(
            data,
            ("age", "gender"),
            self.HIERARCHIES,
            levels,
            (2, 1),
            sampled,
            counts,
            3,
            ("gender",),
        )
        # Pools without the gender dimension: (<50,) -> {male: 5},
        # (>=50,) -> {female: 3}; top1 sum = 8; scale = 1 - 0/1 = 1
        # score = 8 / (k * 1) = 8 / 3
        self.assertAlmostEqual(score, 8.0 / 3.0)


class TestResolveGeneralizationScheme(unittest.TestCase):
    def test_explicit_levels_win_and_are_clamped(self):
        levels = resolve_generalization_scheme(
            ("age", "gender"),
            (4, 1),
            {"age": 9},
            "none",
        )
        self.assertEqual(levels, (4, 0))

    def test_degree_uses_java_math_round(self):
        # MEDIUM = 0.5; max level 5 -> round(2.5) = 3 with Java Math.round
        levels = resolve_generalization_scheme(
            ("zipcode",),
            (5,),
            None,
            "medium",
        )
        self.assertEqual(levels, (3,))

    def test_missing_scheme_raises(self):
        with self.assertRaises(ValueError):
            resolve_generalization_scheme(("age",), (4,), None, None)
        with self.assertRaises(ValueError):
            resolve_generalization_scheme(("age", "gender"), (4, 1), {"age": 1}, None)

    def test_unknown_attribute_raises(self):
        with self.assertRaises(ValueError):
            resolve_generalization_scheme(("age",), (4,), {"zipcode": 1}, None)


if __name__ == "__main__":
    unittest.main()
