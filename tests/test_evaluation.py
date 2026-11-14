import unittest

from spymaster.players.minimax.evaluation import CrudeEvaluator
from spymaster.spymaster import AgentCard, MissionCard, Spymaster


class TestCrudeEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = CrudeEvaluator()

    def test_equal_position_is_zero(self):
        situation = Spymaster()
        self.assertEqual(self.evaluator.evaluate(situation), 0.0)

    def test_finished_game_uses_score_difference(self):
        winning = Spymaster(
            white_score=5,
            black_score=2,
            remaining_missions=[],
        )
        losing = Spymaster(
            white_score=2,
            black_score=5,
            remaining_missions=[],
        )
        drawn = Spymaster(
            white_score=5,
            black_score=5,
            remaining_missions=[],
        )

        self.assertEqual(self.evaluator.evaluate(winning), 1.0)
        self.assertEqual(self.evaluator.evaluate(losing), -1.0)
        self.assertEqual(self.evaluator.evaluate(drawn), 0.0)

    def test_current_mission_is_included(self):
        situation = Spymaster(
            white_cards=[AgentCard(16)],
            black_cards=[AgentCard(1)],
            current_mission=MissionCard(16),
            remaining_missions=[],
        )

        self.assertEqual(self.evaluator.evaluate(situation), 1.0)

    def test_stronger_hand_has_positive_equity(self):
        situation = Spymaster(
            white_cards=[AgentCard(15), AgentCard(14)],
            black_cards=[AgentCard(2), AgentCard(1)],
            current_mission=MissionCard(10),
            remaining_missions=[],
        )

        self.assertGreater(self.evaluator.evaluate(situation), 0.0)

    def test_evaluation_is_bounded(self):
        situation = Spymaster(
            white_cards=[AgentCard(15), AgentCard(14)],
            black_cards=[AgentCard(2), AgentCard(1)],
            white_score=100,
            black_score=0,
            remaining_missions=[],
        )

        self.assertEqual(self.evaluator.evaluate(situation), 1.0)


if __name__ == "__main__":
    unittest.main()
