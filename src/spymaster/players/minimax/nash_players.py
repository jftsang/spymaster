"""One-ply minimax player using equity evaluation of child positions."""

from random import choices

from spymaster import AgentCard, MissionCard, Position, Spymaster
from spymaster.players import Player
from spymaster.spymaster import ASSASSIN

from .evaluation import CrudeEvaluator, Evaluator
from .matrix_game import solve_matrix_game

NASH_PLAYER_NAME = "AI (Nash, 1-ply)"


class NashPlayer(Player):
    """Play the equilibrium mixture of the current mission's payoff matrix.

    Each entry is the evaluator's equity estimate for the position that
    results when both players choose the corresponding card. The
    opponent is modelled as adversarial, so the root action is sampled
    from the row player's equilibrium strategy.
    """

    def __init__(self, name: str, evaluator: Evaluator | None = None):
        super().__init__(name=name)
        self.evaluator = evaluator if evaluator is not None else CrudeEvaluator()

    async def pick(self, state: Spymaster) -> AgentCard:
        position = state.position
        if position.current_mission is None:
            raise ValueError("NashPlayer requires a current mission")

        cards, strategy, _value = self.analyse(position)
        return choices(cards, weights=strategy, k=1)[0]

    def analyse(
        self, position: Position
    ) -> tuple[list[AgentCard], list[float], float]:
        """Return legal cards, their equilibrium probabilities, and value."""
        if position.current_mission is None:
            raise ValueError("NashPlayer requires a current mission")

        cards = sorted(position.ours)
        opponents = sorted(position.theirs)
        matrix = [
            [
                self.evaluator.evaluate(
                    _child_position(position, card, opponent).to_spymaster()
                )
                for opponent in opponents
            ]
            for card in cards
        ]
        strategy, value = solve_matrix_game(matrix)
        return cards, strategy, value


def _child_position(
    position: Position,
    ours: AgentCard,
    theirs: AgentCard,
) -> Position:
    assert position.current_mission is not None
    white_score, black_score = _score(ours, theirs, position.current_mission)
    return Position(
        ours=position.ours - {ours},
        theirs=position.theirs - {theirs},
        missions=position.missions - {position.current_mission},
        current_mission=None,
        white_score=position.white_score + white_score,
        black_score=position.black_score + black_score,
    )


def _score(
    ours: AgentCard,
    theirs: AgentCard,
    mission: MissionCard,
) -> tuple[int, int]:
    if ours == theirs:
        return 0, 0
    if ours == ASSASSIN:
        return int(theirs), 0
    if theirs == ASSASSIN:
        return 0, int(ours)
    if ours > theirs:
        return int(mission), 0
    return 0, int(mission)
