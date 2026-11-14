import unittest

from spymaster.players.minimax.matrix_game import solve_matrix_game


class TestSolveMatrixGame(unittest.TestCase):
    def test_single_entry(self):
        strategy, value = solve_matrix_game([[3.0]])

        self.assertEqual(strategy, [1.0])
        self.assertEqual(value, 3.0)

    def test_single_column(self):
        strategy, value = solve_matrix_game([[1.0], [2.0], [-1.0]])

        self.assertEqual(strategy, [0.0, 1.0, 0.0])
        self.assertEqual(value, 2.0)

    def test_single_row(self):
        strategy, value = solve_matrix_game([[2.0, -1.0]])

        self.assertEqual(strategy, [1.0])
        self.assertEqual(value, -1.0)

    def test_matching_pennies_has_uniform_mixture(self):
        strategy, value = solve_matrix_game([[1.0, -1.0], [-1.0, 1.0]])

        self.assertAlmostEqual(strategy[0], 0.5)
        self.assertAlmostEqual(strategy[1], 0.5)
        self.assertAlmostEqual(value, 0.0)

    def test_rock_paper_scissors_has_uniform_mixture(self):
        strategy, value = solve_matrix_game(
            [
                [0.0, -1.0, 1.0],
                [1.0, 0.0, -1.0],
                [-1.0, 1.0, 0.0],
            ]
        )

        for probability in strategy:
            self.assertAlmostEqual(probability, 1.0 / 3.0)
        self.assertAlmostEqual(value, 0.0)

    def test_dominant_row_is_played_pure(self):
        strategy, value = solve_matrix_game([[1.0, 1.0], [0.0, 0.0]])

        self.assertEqual(strategy, [1.0, 0.0])
        self.assertEqual(value, 1.0)

    def test_strategy_is_a_probability_distribution(self):
        strategy, value = solve_matrix_game([[3.0, -2.0], [1.0, 4.0]])

        self.assertAlmostEqual(sum(strategy), 1.0)
        self.assertTrue(all(probability >= 0.0 for probability in strategy))
        self.assertAlmostEqual(
            value,
            min(
                3.0 * strategy[0] + 1.0 * strategy[1],
                -2.0 * strategy[0] + 4.0 * strategy[1],
            ),
        )

    def test_empty_matrix_is_rejected(self):
        with self.assertRaises(ValueError):
            solve_matrix_game([])

    def test_ragged_matrix_is_rejected(self):
        with self.assertRaises(ValueError):
            solve_matrix_game([[1.0, 2.0], [3.0]])

    def test_non_finite_matrix_is_rejected(self):
        with self.assertRaises(ValueError):
            solve_matrix_game([[1.0, float("nan")]])


if __name__ == "__main__":
    unittest.main()
