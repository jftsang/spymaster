import asyncio
import random
import unittest

from spymaster import Position
from spymaster.players.computer_players import new_computer_player
from spymaster.players.minimax.evaluation import Evaluator
from spymaster.players.minimax.nash_players import (
    NASH_PLAYER_NAME,
    NashAnalyser,
    NashPlayer,
)
from spymaster.spymaster import AgentCard, MissionCard, Spymaster


class RecordingEvaluator(Evaluator):
    def __init__(self, value: float = 0.0):
        self.value = value
        self.positions: list[Position] = []

    def evaluate(self, position: Position) -> float:
        self.positions.append(position)
        return self.value


class MatchingPenniesEvaluator(Evaluator):
    def evaluate(self, position: Position) -> float:
        ours = set(position.ours)
        theirs = set(position.theirs)
        if ours == {10} and theirs == {6}:
            return 1.0
        if ours == {10} and theirs == {3}:
            return -1.0
        if ours == {5} and theirs == {6}:
            return -1.0
        if ours == {5} and theirs == {3}:
            return 1.0
        raise AssertionError(f"Unexpected child position: {position}")


class CardEvaluator(Evaluator):
    def evaluate(self, position: Position) -> float:
        return 1.0 if AgentCard(5) in position.ours else -1.0


def make_state() -> Spymaster:
    return Spymaster(
        white_cards=[AgentCard(10), AgentCard(5)],
        black_cards=[AgentCard(6), AgentCard(3)],
        white_score=0,
        black_score=5,
        current_mission=MissionCard(7),
        remaining_missions=[MissionCard(2)],
    )


class TestNashPlayer(unittest.TestCase):
    def test_analysis_evaluates_every_child_position(self):
        evaluator = RecordingEvaluator()
        player = NashPlayer(
            "Test",
            analyser=NashAnalyser(
                evaluator=evaluator,
                exact_rounds=0,
                use_guarantees=False,
            ),
        )
        state = make_state()

        analysis = player.analyser.analyse(state.position)
        cards, strategy, value = analysis.cards, analysis.strategy, analysis.value

        self.assertEqual(cards, (AgentCard(5), AgentCard(10)))
        self.assertEqual(len(evaluator.positions), 4)
        self.assertAlmostEqual(sum(strategy), 1.0)
        self.assertAlmostEqual(value, 0.0)

    def test_child_position_updates_cards_diff_and_missions(self):
        evaluator = RecordingEvaluator()
        player = NashPlayer(
            "Test",
            analyser=NashAnalyser(
                evaluator=evaluator,
                exact_rounds=0,
                use_guarantees=False,
            ),
        )
        state = make_state()

        player.analyser.analyse(state.position)

        first = evaluator.positions[0]
        self.assertEqual(first.ours, {AgentCard(10)})
        self.assertEqual(first.theirs, {AgentCard(6)})
        self.assertEqual(first.diff, 2)
        self.assertIsNone(first.current_mission)
        self.assertEqual(first.missions, {MissionCard(2)})

    def test_assassin_scores_the_opponents_card(self):
        evaluator = RecordingEvaluator()
        player = NashPlayer(
            "Test",
            analyser=NashAnalyser(
                evaluator=evaluator,
                exact_rounds=0,
                use_guarantees=False,
            ),
        )
        state = Spymaster(
            white_cards=[AgentCard(0), AgentCard(10)],
            black_cards=[AgentCard(4), AgentCard(3)],
            current_mission=MissionCard(7),
            remaining_missions=[],
        )

        player.analyser.analyse(state.position)

        assassin_children = [
            position
            for position in evaluator.positions
            if AgentCard(10) in position.ours
        ]
        self.assertEqual(len(assassin_children), 2)
        self.assertEqual(
            sorted(situation.diff for situation in assassin_children),
            [3, 4],
        )

    def test_pure_optimal_action_is_always_picked(self):
        player = NashPlayer(
            "Test",
            analyser=NashAnalyser(
                evaluator=CardEvaluator(),
                exact_rounds=0,
                use_guarantees=False,
            ),
        )
        state = make_state()

        random.seed(0)
        picks = {asyncio.run(player.pick(state)) for _ in range(20)}

        self.assertEqual(picks, {AgentCard(10)})

    def test_pick_samples_from_the_equilibrium_mixture(self):
        player = NashPlayer(
            "Test",
            analyser=NashAnalyser(
                evaluator=MatchingPenniesEvaluator(),
                exact_rounds=0,
                use_guarantees=False,
            ),
        )
        state = make_state()
        analysis = player.analyser.analyse(state.position)
        cards, strategy, value = analysis.cards, analysis.strategy, analysis.value

        self.assertEqual(cards, (AgentCard(5), AgentCard(10)))
        self.assertAlmostEqual(strategy[0], 0.5)
        self.assertAlmostEqual(strategy[1], 0.5)
        self.assertAlmostEqual(value, 0.0)

        random.seed(1)
        picks = {asyncio.run(player.pick(state)) for _ in range(50)}

        self.assertEqual(picks, {AgentCard(5), AgentCard(10)})

    def test_pick_returns_a_legal_card(self):
        player = NashPlayer(
            "Test",
            analyser=NashAnalyser(
                evaluator=RecordingEvaluator(),
                exact_rounds=0,
                use_guarantees=False,
            ),
        )
        state = make_state()

        picked = asyncio.run(player.pick(state))

        self.assertIn(picked, state.white_cards)

    def test_pick_requires_a_current_mission(self):
        player = NashPlayer("Test", analyser=NashAnalyser(evaluator=RecordingEvaluator()))
        state = Spymaster(remaining_missions=[])

        with self.assertRaises(ValueError):
            asyncio.run(player.pick(state))

    def test_exact_endgame_skips_evaluator(self):
        evaluator = RecordingEvaluator()
        player = NashPlayer("Test", analyser=NashAnalyser(evaluator=evaluator))
        state = make_state()

        analysis = player.analyser.analyse(state.position)

        self.assertEqual(analysis.cards, (AgentCard(5), AgentCard(10)))
        self.assertAlmostEqual(sum(analysis.strategy), 1.0)
        self.assertEqual(evaluator.positions, [])

    def test_pinned_guarantee_skips_search(self):
        evaluator = RecordingEvaluator()
        player = NashPlayer("Test", analyser=NashAnalyser(evaluator=evaluator))
        state = Spymaster(
            white_cards=[AgentCard(10), AgentCard(2), AgentCard(1)],
            black_cards=[AgentCard(5), AgentCard(4), AgentCard(3)],
            white_score=1,
            black_score=0,
            current_mission=MissionCard(3),
            remaining_missions=[MissionCard(1), MissionCard(2)],
        )

        analysis = player.analyser.analyse(state.position)
        cards, strategy, value = analysis.cards, analysis.strategy, analysis.value

        self.assertEqual(cards, (AgentCard(1), AgentCard(2), AgentCard(10)))
        self.assertEqual(strategy, (0.0, 0.0, 1.0))
        self.assertEqual(value, 1.0)
        self.assertEqual(evaluator.positions, [])

    def test_guarantee_holds_on_nonrequired_mission(self):
        player = NashPlayer("Test", analyser=NashAnalyser(evaluator=RecordingEvaluator()))
        state = Spymaster(
            white_cards=[AgentCard(10), AgentCard(2), AgentCard(1)],
            black_cards=[AgentCard(5), AgentCard(4), AgentCard(3)],
            white_score=1,
            black_score=0,
            current_mission=MissionCard(1),
            remaining_missions=[MissionCard(3), MissionCard(2)],
        )

        analysis = player.analyser.analyse(state.position)
        cards, strategy, value = analysis.cards, analysis.strategy, analysis.value

        self.assertEqual(cards, (AgentCard(1), AgentCard(2), AgentCard(10)))
        self.assertEqual(strategy, (1.0, 0.0, 0.0))
        self.assertEqual(value, 1.0)

    def test_player_is_registered_with_the_computer_player_factory(self):
        player = new_computer_player(NASH_PLAYER_NAME)

        self.assertIsInstance(player, NashPlayer)
        self.assertEqual(player.name, NASH_PLAYER_NAME)


if __name__ == "__main__":
    unittest.main()
