import unittest

from spymaster.players.minimax import exact
from spymaster.players.minimax.exact import exact_equity
from spymaster.spymaster import AgentCard, MissionCard, Spymaster


class TestExactEquity(unittest.TestCase):
    def test_terminal_position_uses_score_difference(self):
        winning = Spymaster(white_score=5, black_score=2, remaining_missions=[])
        losing = Spymaster(white_score=2, black_score=5, remaining_missions=[])
        drawn = Spymaster(white_score=5, black_score=5, remaining_missions=[])

        self.assertEqual(exact_equity(winning.position), 1.0)
        self.assertEqual(exact_equity(losing.position), -1.0)
        self.assertEqual(exact_equity(drawn.position), 0.0)

    def test_single_mission_is_resolved_exactly(self):
        losing = Spymaster(
            white_cards=[AgentCard(1)],
            black_cards=[AgentCard(2)],
            current_mission=MissionCard(5),
            remaining_missions=[],
        )
        winning = Spymaster(
            white_cards=[AgentCard(2)],
            black_cards=[AgentCard(1)],
            current_mission=MissionCard(5),
            remaining_missions=[],
        )

        self.assertEqual(exact_equity(losing.position), -1.0)
        self.assertEqual(exact_equity(winning.position), 1.0)

    def test_next_mission_is_a_uniform_chance_node(self):
        situation = Spymaster(
            white_cards=[AgentCard(1), AgentCard(2)],
            black_cards=[AgentCard(1), AgentCard(3)],
            white_score=1,
            black_score=0,
            remaining_missions=[MissionCard(2), MissionCard(3)],
        )

        self.assertAlmostEqual(exact_equity(situation.position), -1.0 / 3.0)

    def test_pinned_win_guarantee_prunes_the_search(self):
        situation = Spymaster(
            white_cards=[AgentCard(10), AgentCard(2), AgentCard(1)],
            black_cards=[AgentCard(5), AgentCard(4), AgentCard(3)],
            white_score=1,
            black_score=0,
            current_mission=MissionCard(3),
            remaining_missions=[MissionCard(1), MissionCard(2)],
        )

        self.assertEqual(exact_equity(situation.position), 1.0)

    def test_pinned_loss_guarantee_prunes_the_search(self):
        situation = Spymaster(
            white_cards=[AgentCard(15), AgentCard(1)],
            black_cards=[AgentCard(14), AgentCard(2)],
            black_score=5,
            current_mission=MissionCard(2),
            remaining_missions=[MissionCard(1)],
        )

        self.assertEqual(exact_equity(situation.position), -1.0)

    def test_pinned_draw_guarantee_prunes_the_search(self):
        situation = Spymaster(
            white_cards=[AgentCard(15), AgentCard(14)],
            black_cards=[AgentCard(2), AgentCard(1)],
            black_score=3,
            current_mission=MissionCard(2),
            remaining_missions=[MissionCard(1)],
        )

        self.assertEqual(exact_equity(situation.position), 0.0)

    def test_cache_is_keyed_on_score_difference(self):
        exact.exact_equity.cache_clear()
        first = Spymaster(
            white_score=10,
            black_score=7,
            remaining_missions=[],
        )
        second = Spymaster(
            white_score=100,
            black_score=97,
            remaining_missions=[],
        )

        self.assertEqual(exact_equity(first.position), 1.0)
        self.assertEqual(exact_equity(second.position), 1.0)
        self.assertGreaterEqual(exact.exact_equity.cache_info().hits, 1)


if __name__ == "__main__":
    unittest.main()
