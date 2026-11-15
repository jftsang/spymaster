"""Exact dynamic programming for small endgames."""

from functools import cache
from math import fsum

from spymaster import AgentCard, MissionCard, Position

from .guarantee import analyse_guarantee
from .matrix_game import solve_matrix_game
from .moves import child_position

EXACT_ROUNDS = 3


def exact_equity(position: Position) -> float:
    """Return the exact game value of an endgame position.

    The cache is keyed on the score difference rather than the two
    individual scores, since only the remaining margin matters.
    """
    diff = position.white_score - position.black_score
    return _exact_equity(
        position.ours,
        position.theirs,
        position.missions,
        position.current_mission,
        diff,
    )


@cache
def _exact_equity(
    ours: frozenset[AgentCard],
    theirs: frozenset[AgentCard],
    missions: frozenset[MissionCard],
    current_mission: MissionCard | None,
    diff: int,
) -> float:
    position = Position(
        ours=ours,
        theirs=theirs,
        missions=missions,
        current_mission=current_mission,
        white_score=diff,
        black_score=0,
    )
    guarantee = analyse_guarantee(position)
    if guarantee.equity is not None:
        return float(guarantee.equity)

    if current_mission is None:
        if not missions:
            return _outcome(diff)
        value = fsum(
            _exact_equity(ours, theirs, missions, mission, diff)
            for mission in missions
        )
        return value / len(missions)

    cards = sorted(ours)
    opponents = sorted(theirs)
    matrix = [
        [
            exact_equity(child_position(position, card, opponent))
            for opponent in opponents
        ]
        for card in cards
    ]
    _, value = solve_matrix_game(matrix)
    return value


def _outcome(diff: int) -> float:
    if diff > 0:
        return 1.0
    if diff < 0:
        return -1.0
    return 0.0
