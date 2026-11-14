import asyncio
import random
import unittest

from spymaster.players.computer_players import new_computer_player
from spymaster.players.minimax.evaluation import Evaluator
from spymaster.players.minimax.nash_players import NASH_PLAYER_NAME, NashPlayer
from spymaster.spymaster import AgentCard, MissionCard, Spymaster


class RecordingEvaluator(Evaluator):
    def __init__(self, value: float = 0.0):
        self.value = value
        self.situations: list[Spymaster] = []

    def evaluate(self, situation: Spymaster) -> float:
        self.situations.append(situation)
        return self.value


class MatchingPenniesEvaluator(Evaluator):
    def evaluate(self, situation: Spymaster) -> float:
        ours = set(situation.white_cards)
        theirs = set(situation.black_cards)
        if ours == {10} and theirs == {4}:
            return 1.0
        if ours == {10} and theirs == {3}:
            return -1.0
        if ours == {5} and theirs == {4}:
            return -1.0
        if ours == {5} and theirs == {3}:
            return 1.0
        raise AssertionError(f"Unexpected child position: {situation}")


class CardEvaluator(Evaluator):
    def evaluate(self, situation: Spymaster) -> float:
        return 1.0 if AgentCard(5) in situation.white_cards else -1.0


def make_state() -> Spymaster:
    return Spymaster(
        white_cards=[AgentCard(10), AgentCard(5)],
        black_cards=[AgentCard(4), AgentCard(3)],
        white_score=1,
        black_score=0,
        current_mission=MissionCard(7),
        remaining_missions=[MissionCard(2), MissionCard(1)],
    )


class TestNashPlayer(unittest.TestCase):
    def test_analysis_evaluates_every_child_position(self):
        evaluator = RecordingEvaluator()
        player = NashPlayer("Test", evaluator=evaluator)
        state = make_state()

        cards, strategy, value = player.analyse(state.position)

        self.assertEqual(cards, [AgentCard(5), AgentCard(10)])
        self.assertEqual(len(evaluator.situations), 4)
        self.assertAlmostEqual(sum(strategy), 1.0)
        self.assertAlmostEqual(value, 0.0)

    def test_child_position_updates_cards_scores_and_missions(self):
        evaluator = RecordingEvaluator()
        player = NashPlayer("Test", evaluator=evaluator)
        state = make_state()

        player.analyse(state.position)

        first = evaluator.situations[0]
        self.assertEqual(first.white_cards, [AgentCard(10)])
        self.assertEqual(first.black_cards, [AgentCard(4)])
        self.assertEqual(first.white_score, 8)
        self.assertEqual(first.black_score, 0)
        self.assertIsNone(first.current_mission)
        self.assertEqual(
            first.remaining_missions,
            [MissionCard(1), MissionCard(2)],
        )

    def test_assassin_scores_the_opponents_card(self):
        evaluator = RecordingEvaluator()
        player = NashPlayer("Test", evaluator=evaluator)
        state = Spymaster(
            white_cards=[AgentCard(0), AgentCard(10)],
            black_cards=[AgentCard(4), AgentCard(3)],
            current_mission=MissionCard(7),
            remaining_missions=[],
        )

        player.analyse(state.position)

        assassin_children = [
            situation
            for situation in evaluator.situations
            if AgentCard(10) in situation.white_cards
        ]
        self.assertEqual(len(assassin_children), 2)
        self.assertEqual(
            sorted(situation.white_score for situation in assassin_children),
            [3, 4],
        )
        self.assertTrue(
            all(situation.black_score == 0 for situation in assassin_children)
        )

    def test_pure_optimal_action_is_always_picked(self):
        player = NashPlayer("Test", evaluator=CardEvaluator())
        state = make_state()

        random.seed(0)
        picks = {asyncio.run(player.pick(state)) for _ in range(20)}

        self.assertEqual(picks, {AgentCard(10)})

    def test_pick_samples_from_the_equilibrium_mixture(self):
        player = NashPlayer("Test", evaluator=MatchingPenniesEvaluator())
        state = make_state()
        cards, strategy, value = player.analyse(state.position)

        self.assertEqual(cards, [AgentCard(5), AgentCard(10)])
        self.assertAlmostEqual(strategy[0], 0.5)
        self.assertAlmostEqual(strategy[1], 0.5)
        self.assertAlmostEqual(value, 0.0)

        random.seed(1)
        picks = {asyncio.run(player.pick(state)) for _ in range(50)}

        self.assertEqual(picks, {AgentCard(5), AgentCard(10)})

    def test_pick_returns_a_legal_card(self):
        player = NashPlayer("Test", evaluator=RecordingEvaluator())
        state = make_state()

        picked = asyncio.run(player.pick(state))

        self.assertIn(picked, state.white_cards)

    def test_pick_requires_a_current_mission(self):
        player = NashPlayer("Test", evaluator=RecordingEvaluator())
        state = Spymaster(remaining_missions=[])

        with self.assertRaises(ValueError):
            asyncio.run(player.pick(state))

    def test_player_is_registered_with_the_computer_player_factory(self):
        player = new_computer_player(NASH_PLAYER_NAME)

        self.assertIsInstance(player, NashPlayer)
        self.assertEqual(player.name, NASH_PLAYER_NAME)


if __name__ == "__main__":
    unittest.main()
