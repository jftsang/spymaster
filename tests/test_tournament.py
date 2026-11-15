import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from spymaster import AgentCard, Spymaster
from spymaster.gene_pool import _points
from spymaster.players import Player
from spymaster.tournament import TournamentResults, _net_score, run_round_robin


class LowestCardPlayer(Player):
    async def pick(self, state: Spymaster) -> AgentCard:
        return AgentCard(min(state.white_cards))


class HighestCardPlayer(Player):
    async def pick(self, state: Spymaster) -> AgentCard:
        return AgentCard(max(state.white_cards))


class TestMatchPoints(unittest.TestCase):
    def test_win_draw_and_loss(self):
        win = Spymaster(white_score=5, black_score=2)
        draw = Spymaster(white_score=3, black_score=3)
        loss = Spymaster(white_score=2, black_score=5)

        self.assertEqual(_net_score(True, win), 1)
        self.assertEqual(_net_score(False, win), -1)
        self.assertEqual(_net_score(True, draw), 0)
        self.assertEqual(_net_score(False, draw), 0)
        self.assertEqual(_points(win), 1)
        self.assertEqual(_points(draw), 0)
        self.assertEqual(_points(loss), -1)


class TestTournamentResults(unittest.TestCase):
    def test_save_load_round_trip(self):
        results = TournamentResults(
            scores=np.array([[0, 3], [-3, 0]], dtype=np.int16),
            player_names=["Alice", "Bob"],
            evaluator_names=["Alice", "Bob"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tournament_results.npz"
            results.save(path)
            loaded = TournamentResults.load(path)

        np.testing.assert_array_equal(loaded.scores, results.scores)
        self.assertEqual(loaded.player_names, results.player_names)
        self.assertEqual(loaded.evaluator_names, results.evaluator_names)


class TestRoundRobinResults(unittest.IsolatedAsyncioTestCase):
    async def test_matrix_is_antisymmetric(self):
        def make_player(name: str) -> Player:
            if name == "High":
                return HighestCardPlayer(name)
            return LowestCardPlayer(name)

        with patch("spymaster.tournament._new_player", side_effect=make_player):
            results = await run_round_robin(
                player_names=["High", "Low"],
                evaluator_names=["High", "Low"],
                n_games=4,
                seed=None,
                progress=False,
            )

        self.assertEqual(results.scores.shape, (2, 2))
        self.assertEqual(results.scores[0, 0], 0)
        self.assertEqual(results.scores[1, 1], 0)
        self.assertEqual(results.scores[0, 1], -results.scores[1, 0])


if __name__ == "__main__":
    unittest.main()
