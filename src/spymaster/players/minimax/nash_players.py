"""Nash-style analysis at one or two plies, and the players that use it."""

import logging
from dataclasses import replace
from functools import partial
from math import fsum
from random import choices
from typing import Protocol

from spymaster import AgentCard, Position, Spymaster
from spymaster.players import Player

from .analysis import Analyser, Analysis
from .evaluation import CrudeEvaluator, Evaluator
from .exact import EXACT_ROUNDS, exact_equity
from .guarantee import Guarantee, GuaranteeKind, analyse_guarantee
from .matrix_game import solve_matrix_game
from .moves import child_position

logger = logging.getLogger("spymaster.players.minimax.nash_players")

TWO_PLY_EXACT_ROUNDS = 5


class _CacheableAnalyser(Protocol):
    def analyse(self, position: Position) -> Analysis: ...

    def clear_cache(self) -> None: ...

    def cache_size(self) -> int: ...


class _CachingEvaluator(Evaluator):
    """Cache leaf evaluations by position.

    Two-ply search reaches the same terminal position through different
    orderings of the two missions, so caching avoids repeated evaluations.
    """

    def __init__(self, evaluator: Evaluator):
        self.evaluator = evaluator
        self._cache: dict[Position, float] = {}

    def evaluate(self, position: Position) -> float:
        if position not in self._cache:
            self._cache[position] = self.evaluator.evaluate(position)
        return self._cache[position]

    def clear_cache(self) -> None:
        self._cache.clear()

    def cache_size(self) -> int:
        return len(self._cache)


class NashAnalyser:
    def __init__(
        self,
        evaluator: Evaluator | None = None,
        exact_rounds: int = EXACT_ROUNDS,
        use_guarantees: bool = True,
    ):
        self.evaluator = evaluator if evaluator is not None else CrudeEvaluator()
        self.exact_rounds = exact_rounds
        self.use_guarantees = use_guarantees
        self._analysis_cache: dict[Position, Analysis] = {}

    def analyse(self, position: Position) -> Analysis:
        """Return legal cards, their equilibrium probabilities, and value.

        Results are cached per player instance, so a long-lived player
        (such as the webserver's shared analysis player) reuses analyses
        across positions and games.
        """
        cached = self._analysis_cache.get(position)
        if cached is None:
            cached = self._compute_analysis(position)
            self._analysis_cache[position] = cached
        return cached

    def clear_cache(self) -> None:
        self._analysis_cache.clear()

    def cache_size(self) -> int:
        return len(self._analysis_cache)

    def _compute_analysis(self, position: Position) -> Analysis:
        if position.current_mission is None:
            raise ValueError("NashPlayer requires a current mission")

        if self.use_guarantees:
            guarantee = analyse_guarantee(position)
            pinned = _pinned_guarantee(position, guarantee)
            if pinned is not None:
                return pinned

        cards = sorted(position.ours)
        opponents = sorted(position.theirs)
        matrix = [
            [
                self._value_after_round(position, card, opponent)
                for opponent in opponents
            ]
            for card in cards
        ]
        strategy, value = solve_matrix_game(matrix)
        return Analysis(cards, strategy, value)

    def _value_after_round(
        self,
        position: Position,
        ours: AgentCard,
        theirs: AgentCard,
    ) -> float:
        child = child_position(position, ours, theirs)
        if self.use_guarantees:
            guarantee = analyse_guarantee(child)
            if guarantee.equity is not None:
                return float(guarantee.equity)
        if self.exact_rounds and len(child.missions) <= self.exact_rounds:
            return exact_equity(child)
        return self.evaluator.evaluate(child)


class TwoPlyNashAnalyser(NashAnalyser):
    """Evaluate root plays by the equilibrium value of the next mission.

    The root payoff for a pair of cards is the mean equilibrium value over
    all possible next missions. The second ply uses the same leaf policy
    as `NashAnalyser`: a pinned guarantee, then exact DP when the
    configured exact-rounds threshold is reached, otherwise the crude
    evaluator.
    """

    def __init__(
        self,
        evaluator: Evaluator | None = None,
        exact_rounds: int = TWO_PLY_EXACT_ROUNDS,
        use_guarantees: bool = True,
    ):
        super().__init__(evaluator, exact_rounds, use_guarantees)
        self._cached_evaluator = _CachingEvaluator(self.evaluator)
        self._inner = NashAnalyser(
            evaluator=self._cached_evaluator,
            exact_rounds=exact_rounds,
            use_guarantees=use_guarantees,
        )

    def _value_after_round(
        self,
        position: Position,
        ours: AgentCard,
        theirs: AgentCard,
    ) -> float:
        child = child_position(position, ours, theirs)
        if self.use_guarantees:
            guarantee = analyse_guarantee(child)
            if guarantee.equity is not None:
                return float(guarantee.equity)
        if self.exact_rounds and len(child.missions) <= self.exact_rounds:
            return exact_equity(child)
        if not child.missions:
            return self._cached_evaluator.evaluate(child)

        values = (
            self._inner.analyse(replace(child, current_mission=mission)).value
            for mission in sorted(child.missions)
        )
        return fsum(values) / len(child.missions)

    def clear_cache(self) -> None:
        super().clear_cache()
        self._inner.clear_cache()
        self._cached_evaluator.clear_cache()

    def cache_size(self) -> int:
        return (
            super().cache_size()
            + self._inner.cache_size()
            + self._cached_evaluator.cache_size()
        )


class AdaptiveNashAnalyser:
    """Use 1-ply when cards are plentiful and 2-ply in the mid-game.

    Two-ply grows as ``n^2 (n-1)^3`` with ``n`` cards per hand, so running
    it from the opening is prohibitively expensive. The configured exact
    cutoff defaults to the existing three rounds; a five-round exact solve
    is correct but too slow for live play and tests.
    """

    def __init__(
        self,
        evaluator: Evaluator | None = None,
        two_ply_max_cards: int = 8,
        exact_rounds: int = EXACT_ROUNDS,
        one_ply: _CacheableAnalyser | None = None,
        two_ply: _CacheableAnalyser | None = None,
    ):
        self.two_ply_max_cards = two_ply_max_cards
        self.one_ply = one_ply if one_ply is not None else NashAnalyser(evaluator)
        self.two_ply = (
            two_ply
            if two_ply is not None
            else TwoPlyNashAnalyser(evaluator=evaluator, exact_rounds=exact_rounds)
        )

    def analyse(self, position: Position) -> Analysis:
        if len(position.ours) > self.two_ply_max_cards:
            return self.one_ply.analyse(position)
        return self.two_ply.analyse(position)

    def clear_cache(self) -> None:
        self.one_ply.clear_cache()
        self.two_ply.clear_cache()

    def cache_size(self) -> int:
        return self.one_ply.cache_size() + self.two_ply.cache_size()


def _pinned_guarantee(
    position: Position,
    guarantee: Guarantee,
) -> Analysis | None:
    if guarantee.equity is None:
        return None

    cards = sorted(position.ours)
    card = _guarantee_card(position, guarantee)
    strategy = [1.0 if candidate == card else 0.0 for candidate in cards]
    return Analysis(cards, strategy, float(guarantee.equity))


def _guarantee_card(position: Position, guarantee: Guarantee) -> AgentCard:
    if guarantee.kind is GuaranteeKind.LOSS:
        # keep chucking bad cards and pray the opponent blunders
        return min(position.ours)

    winners = set(guarantee.guaranteed_winners)
    if position.current_mission in guarantee.required_missions and winners:
        # snap up the missions that we need to secure a win, don't care
        # about anything else
        return min(winners)

    reserves = [card for card in position.ours if card not in winners]
    if reserves:
        return min(reserves)  # chuck cards
    return min(position.ours)


class NashPlayer(Player):
    """Play the equilibrium mixture of the current mission's payoff matrix.

    Each entry is an exact or estimated equity for the position that
    results when both players choose the corresponding card. The
    opponent is modelled as adversarial, so the root action is sampled
    from the row player's equilibrium strategy.
    """

    def __init__(self, name: str, analyser: Analyser):
        super().__init__(name=name)
        self.analyser = analyser
        self.logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}.{id(self)}"
        )

    async def pick(self, state: Spymaster) -> AgentCard:
        position = state.position
        if position.current_mission is None:
            raise ValueError("NashPlayer requires a current mission")

        analysis = self.analyser.analyse(position)
        crude_evaluation = CrudeEvaluator().evaluate(position)
        self.logger.debug(
            "Evaluation: %.3f; Crude Evaluation: %.3f",
            analysis.value,
            crude_evaluation,
        )
        self.logger.debug(
            "Strategy: {%s}",
            ", ".join(
                f"{c}: {s:.3f}"
                for c, s in sorted(
                    zip(analysis.cards, analysis.strategy),
                    key=lambda cs: cs[1],
                    reverse=True,
                )
            ),
        )
        return choices(analysis.cards, weights=analysis.strategy, k=1)[0]


# Players are fresh; the analysers own the shared analysis caches.
NASH_ANALYSER = NashAnalyser()
NASH_PLAYER_NAME = "AI (Nash, 1-ply)"
NASH_FACTORIES = {
    NASH_PLAYER_NAME: partial(NashPlayer, name=NASH_PLAYER_NAME, analyser=NASH_ANALYSER)
}

# Deployed with the existing three-round exact cutoff; TwoPlyNashAnalyser
# itself still defaults to the requested five rounds for direct use.
ADAPTIVE_ANALYSER = AdaptiveNashAnalyser(two_ply_max_cards=8)
TWO_PLY_PLAYER_NAME = "AI (Nash, 2-ply)"
TWO_PLY_FACTORIES = {
    TWO_PLY_PLAYER_NAME: partial(
        NashPlayer,
        name=TWO_PLY_PLAYER_NAME,
        analyser=ADAPTIVE_ANALYSER,
    )
}
