import asyncio
import random
import unittest
from unittest.mock import Mock, patch

from spymaster import Position
from spymaster.players.computer_players import new_computer_player
from spymaster.players.minimax.analysis import Analysis
from spymaster.players.minimax.evaluation import Evaluator
from spymaster.players.minimax.nash_players import (
    ADAPTIVE_ANALYSER,
    NASH_ANALYSER,
    NASH_PLAYER_NAME,
    TWO_PLY_PLAYER_NAME,
    AdaptiveNashAnalyser,
    NashAnalyser,
    NashPlayer,
    TwoPlyNashAnalyser,
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
        assert isinstance(player, NashPlayer)

        self.assertEqual(player.name, NASH_PLAYER_NAME)
        self.assertIs(player.analyser, NASH_ANALYSER)


class TestTwoPlyNashAnalyser(unittest.TestCase):
    def test_root_matrix_uses_values_after_two_rounds(self):
        evaluator = RecordingEvaluator()
        analyser = TwoPlyNashAnalyser(
            evaluator=evaluator,
            exact_rounds=0,
            use_guarantees=False,
        )

        analysis = analyser.analyse(make_state().position)

        self.assertEqual(len(evaluator.positions), 3)
        self.assertTrue(
            all(
                not position.ours
                and not position.theirs
                and not position.missions
                and position.current_mission is None
                for position in evaluator.positions
            )
        )
        self.assertEqual(
            sorted(position.diff for position in evaluator.positions),
            [-10, 0, 4],
        )
        self.assertEqual(analysis.cards, (AgentCard(5), AgentCard(10)))
        self.assertAlmostEqual(sum(analysis.strategy), 1.0)

    def test_exact_rounds_five_skips_the_second_ply(self):
        state = Spymaster(
            white_cards=[AgentCard(card) for card in range(10, 4, -1)],
            black_cards=[AgentCard(card) for card in (15, 14, 13, 12, 11, 1)],
            current_mission=MissionCard(6),
            remaining_missions=[MissionCard(mission) for mission in range(1, 6)],
        )
        evaluator = RecordingEvaluator()
        analyser = TwoPlyNashAnalyser(evaluator=evaluator, use_guarantees=False)

        with patch(
            "spymaster.players.minimax.nash_players.exact_equity",
            return_value=0.25,
        ) as exact:
            analysis = analyser.analyse(state.position)

        self.assertEqual(exact.call_count, 36)
        self.assertEqual(evaluator.positions, [])
        self.assertAlmostEqual(analysis.value, 0.25)

    def test_cache_size_and_clear_cache_cover_all_caches(self):
        analyser = TwoPlyNashAnalyser(
            evaluator=RecordingEvaluator(),
            exact_rounds=0,
            use_guarantees=False,
        )

        analyser.analyse(make_state().position)

        self.assertGreater(analyser.cache_size(), 0)
        analyser.clear_cache()
        self.assertEqual(analyser.cache_size(), 0)


class TestAdaptiveNashAnalyser(unittest.TestCase):
    def _position_with_cards(self, count: int) -> Position:
        state = Spymaster(
            white_cards=[AgentCard(card) for card in range(1, count + 1)],
            black_cards=[AgentCard(card) for card in range(16 - count, 16)],
            current_mission=MissionCard(count),
            remaining_missions=[MissionCard(mission) for mission in range(1, count)],
        )
        return state.position

    def test_delegates_by_hand_size(self):
        one_ply = Mock()
        two_ply = Mock()
        result = Analysis((AgentCard(1),), (1.0,), 0.0)
        one_ply.analyse.return_value = result
        two_ply.analyse.return_value = result
        analyser = AdaptiveNashAnalyser(
            one_ply=one_ply,
            two_ply=two_ply,
            two_ply_max_cards=8,
        )

        self.assertIs(
            analyser.analyse(self._position_with_cards(9)),
            result,
        )
        one_ply.analyse.assert_called_once()
        two_ply.analyse.assert_not_called()

        self.assertIs(
            analyser.analyse(self._position_with_cards(8)),
            result,
        )
        two_ply.analyse.assert_called_once()

    def test_cache_methods_are_delegated(self):
        one_ply = Mock()
        two_ply = Mock()
        one_ply.cache_size.return_value = 2
        two_ply.cache_size.return_value = 3
        analyser = AdaptiveNashAnalyser(one_ply=one_ply, two_ply=two_ply)

        self.assertEqual(analyser.cache_size(), 5)
        analyser.clear_cache()
        one_ply.clear_cache.assert_called_once()
        two_ply.clear_cache.assert_called_once()

    def test_two_ply_player_is_registered_with_the_adaptive_analyser(self):
        player = new_computer_player(TWO_PLY_PLAYER_NAME)
        assert isinstance(player, NashPlayer)

        self.assertEqual(player.name, TWO_PLY_PLAYER_NAME)
        self.assertIs(player.analyser, ADAPTIVE_ANALYSER)
        self.assertIsInstance(ADAPTIVE_ANALYSER.two_ply, TwoPlyNashAnalyser)


if __name__ == "__main__":
    unittest.main()
