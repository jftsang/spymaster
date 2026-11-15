"""One-ply minimax player using equity evaluation of child positions."""

import logging
from random import choices

from spymaster import AgentCard, Position, Spymaster
from spymaster.players import Player

from .evaluation import CrudeEvaluator, Evaluator
from .exact import EXACT_ROUNDS, exact_equity
from .guarantee import Guarantee, GuaranteeKind, analyse_guarantee
from .matrix_game import solve_matrix_game
from .moves import child_position

NASH_PLAYER_NAME = "AI (Nash, 1-ply)"

logger = logging.getLogger("spymaster.players.minimax.nash_players")


class NashPlayer(Player):
    """Play the equilibrium mixture of the current mission's payoff matrix.

    Each entry is an exact or estimated equity for the position that
    results when both players choose the corresponding card. The
    opponent is modelled as adversarial, so the root action is sampled
    from the row player's equilibrium strategy.
    """

    def __init__(
        self,
        name: str,
        evaluator: Evaluator | None = None,
        exact_rounds: int = EXACT_ROUNDS,
        use_guarantees: bool = True,
    ):
        super().__init__(name=name)
        self.evaluator = evaluator if evaluator is not None else CrudeEvaluator()
        self.exact_rounds = exact_rounds
        self.use_guarantees = use_guarantees
        self.logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}.{id(self)}"
        )

    async def pick(self, state: Spymaster) -> AgentCard:
        position = state.position
        if position.current_mission is None:
            raise ValueError("NashPlayer requires a current mission")

        cards, strategy, _value = self.analyse(position)
        crude_evaluation = CrudeEvaluator().evaluate(position)
        self.logger.info(
            "Evaluation: %.3f; Crude Evaluation: %.3f", _value, crude_evaluation
        )
        self.logger.info(
            "Strategy: {%s}",
            ", ".join(
                f"{c}: {s:.3f}"
                for c, s in sorted(
                    zip(cards, strategy), key=lambda cs: cs[1], reverse=True
                )
            ),
        )
        return choices(cards, weights=strategy, k=1)[0]

    def analyse(self, position: Position) -> tuple[list[AgentCard], list[float], float]:
        """Return legal cards, their equilibrium probabilities, and value."""
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
        return cards, strategy, value

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
) -> tuple[list[AgentCard], list[float], float] | None:
    if guarantee.equity is None:
        return None

    cards = sorted(position.ours)
    card = _guarantee_card(position, guarantee)
    strategy = [1.0 if candidate == card else 0.0 for candidate in cards]
    return cards, strategy, float(guarantee.equity)


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
