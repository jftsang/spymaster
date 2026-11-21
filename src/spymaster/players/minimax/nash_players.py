"""One-ply minimax player using equity evaluation of child positions."""

import logging
from functools import partial
from random import choices

from spymaster import AgentCard, Position, Spymaster
from spymaster.players import Player

from .analysis import Analyser, Analysis
from .evaluation import CrudeEvaluator, Evaluator
from .exact import EXACT_ROUNDS, exact_equity
from .guarantee import Guarantee, GuaranteeKind, analyse_guarantee
from .matrix_game import solve_matrix_game
from .moves import child_position

logger = logging.getLogger("spymaster.players.minimax.nash_players")


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
        return min(position.ours)

    winners = set(guarantee.guaranteed_winners)
    if position.current_mission in guarantee.required_missions and winners:
        return min(winners)

    reserves = [card for card in position.ours if card not in winners]
    if reserves:
        return min(reserves)
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


# Players are fresh; NASH_ANALYSER owns the shared analysis cache.
NASH_ANALYSER = NashAnalyser()
NASH_PLAYER_NAME = "AI (Nash, 1-ply)"
NASH_FACTORIES = {
    NASH_PLAYER_NAME: partial(NashPlayer, name=NASH_PLAYER_NAME, analyser=NASH_ANALYSER)
}
