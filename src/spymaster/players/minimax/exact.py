"""Exact dynamic programming for small endgames."""

from dataclasses import replace
from functools import cache
from math import fsum

from spymaster import Position

from .guarantee import analyse_guarantee
from .matrix_game import solve_matrix_game
from .moves import child_position

EXACT_ROUNDS = 3


@cache
def exact_equity(position: Position) -> float:
    """Return the exact game value of an endgame position.

    Results are cached on the position itself. A `Position` records only
    the score difference, so positions that differ solely in the absolute
    scores share a cache entry.
    """
    guarantee = analyse_guarantee(position)
    if guarantee.equity is not None:
        return float(guarantee.equity)

    if position.current_mission is None:
        if not position.missions:
            return _outcome(position.diff)
        value = fsum(
            exact_equity(replace(position, current_mission=mission))
            for mission in position.missions
        )
        return value / len(position.missions)

    cards = sorted(position.ours)
    opponents = sorted(position.theirs)
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
