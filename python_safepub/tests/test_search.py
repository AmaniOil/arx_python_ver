import unittest

from safepub.search import DataDependentEDDPSearch


class TestDataDependentEDDPSearch(unittest.TestCase):
    def test_traverse_uses_predecessors_and_tracks_best_score(self):
        predecessors = {
            (2, 2): [(1, 2), (2, 1)],
            (1, 2): [(0, 2), (1, 1)],
            (2, 1): [(1, 1), (2, 0)],
            (0, 2): [(0, 1)],
            (1, 1): [(0, 1), (1, 0)],
            (2, 0): [(1, 0)],
            (0, 1): [(0, 0)],
            (1, 0): [(0, 0)],
            (0, 0): [],
        }
        scores = {
            (2, 2): 0.0,
            (1, 2): 1.0,
            (2, 1): 2.0,
            (0, 2): 3.0,
            (1, 1): 4.0,
            (2, 0): 5.0,
            (0, 1): 6.0,
            (1, 0): 7.0,
            (0, 0): 8.0,
        }

        search = DataDependentEDDPSearch(
            top=(2, 2),
            predecessors=lambda item: predecessors[item],
            score=lambda item: scores[item],
            expansion_limit=5,
            epsilon_search=1.0,
            deterministic=True,
        )
        result = search.traverse()
        self.assertGreaterEqual(result.best_score, 0.0)
        self.assertGreaterEqual(len(result.steps), 1)

    def test_equal_scores_prefer_lower_transformation_level(self):
        # Mirrors AbstractAlgorithm#trackOptimum: on equal scores the
        # transformation with the lower level wins.
        predecessors = {
            (1, 1): [(0, 1), (1, 0)],
            (0, 1): [(0, 0)],
            (1, 0): [(0, 0)],
            (0, 0): [],
        }
        scores = {(1, 1): 1.0, (0, 1): 1.0, (1, 0): 1.0, (0, 0): 1.0}

        search = DataDependentEDDPSearch(
            top=(1, 1),
            predecessors=lambda item: predecessors[item],
            score=lambda item: scores[item],
            expansion_limit=3,
            epsilon_search=1.0,
            deterministic=True,
            level=sum,
        )
        result = search.traverse()
        self.assertEqual(result.best, (0, 0))
        self.assertEqual(result.best_score, 1.0)


if __name__ == "__main__":
    unittest.main()
