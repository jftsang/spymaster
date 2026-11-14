"""Guaranteed-win analysis for Spymaster players."""

from dataclasses import dataclass
from enum import Enum
from functools import partial

from spymaster import AgentCard, Position
from spymaster.spymaster import ASSASSIN, MissionCard


class GuaranteeKind(Enum):
    WIN = "win"
    DRAW_ONLY = "draw_only"
    DEFENSIVE_DRAW = "defensive_draw"
    LOSS = "loss"
    NONE = "none"


@dataclass(frozen=True)
class Guarantee:
    """The result of guaranteed-winner analysis.

    Attributes:
        kind: Classification of the position.
        equity: Exact guaranteed equity (+1, 0, or -1), or None when the
            result is not an unconditional exact guarantee.
            DEFENSIVE_DRAW returns None because the caller may still
            choose to play for a win, although its draw policy
            guarantees at least a draw.
        win_threshold: Smallest k for which scoring the k highest-value
            missions guarantees a win, or None if no such k exists.
        draw_threshold: Smallest k for which scoring the k highest-value
            missions guarantees at least a draw, or None if no such k
            exists.
        guaranteed_winners: Our cards that are strictly higher than the
            opponent's highest card, sorted ascending.
        required_missions: Highest-value unresolved missions that the
            active policy aims to score, sorted descending. Empty when
            no policy applies.
    """

    kind: GuaranteeKind
    equity: int | None = None
    win_threshold: int | None = None
    draw_threshold: int | None = None
    guaranteed_winners: tuple[AgentCard, ...] = ()
    required_missions: tuple[MissionCard, ...] = ()


def analyse_guarantee(position: Position) -> Guarantee:
    """Classify a position using only guaranteed winners.

    ``required_missions`` contains the highest-value missions needed by
    the active policy. Play a guaranteed winner on one of those missions
    and hold otherwise.
    """
    missions = _unresolved_missions(position)
    if not missions:
        return Guarantee(GuaranteeKind.NONE)

    total = sum(missions)
    diff = position.white_score - position.black_score

    if diff + total < 0:
        return Guarantee(kind=GuaranteeKind.LOSS, equity=-1)

    if ASSASSIN in position.ours or ASSASSIN in position.theirs:
        return Guarantee(kind=GuaranteeKind.NONE)

    their_best = max(position.theirs, default=-1)
    winners = tuple(sorted(card for card in position.ours if card > their_best))
    target = total - diff
    win_threshold = _threshold(missions, target, strict=True)
    draw_threshold = _threshold(missions, target, strict=False)
    available = len(winners)
    policy = partial(
        _policy,
        win_threshold=win_threshold,
        draw_threshold=draw_threshold,
        winners=winners,
        missions=missions,
    )

    if diff + total == 0:
        equity = (
            0
            if draw_threshold is not None and draw_threshold <= available
            else None
        )
        return policy(GuaranteeKind.DRAW_ONLY, equity, draw_threshold)

    if win_threshold is not None and win_threshold <= available:
        return policy(GuaranteeKind.WIN, 1, win_threshold)

    if draw_threshold is not None and draw_threshold <= available:
        return policy(GuaranteeKind.DEFENSIVE_DRAW, None, draw_threshold)

    return policy(GuaranteeKind.NONE, None, None)


def _unresolved_missions(position: Position) -> tuple[MissionCard, ...]:
    missions = set(position.missions)
    if position.current_mission is not None:
        missions.add(position.current_mission)
    return tuple(sorted(missions, reverse=True))


def _threshold(
    missions: tuple[MissionCard, ...],
    target: int,
    *,
    strict: bool,
) -> int | None:
    cumulative = 0
    for count, mission in enumerate(missions, start=1):
        cumulative += mission
        if strict and 2 * cumulative > target:
            return count
        if not strict and 2 * cumulative >= target:
            return count
    return None


def _policy(
    kind: GuaranteeKind,
    equity: int | None,
    active_threshold: int | None,
    *,
    win_threshold: int | None,
    draw_threshold: int | None,
    winners: tuple[AgentCard, ...],
    missions: tuple[MissionCard, ...],
) -> Guarantee:
    return Guarantee(
        kind=kind,
        equity=equity,
        win_threshold=win_threshold,
        draw_threshold=draw_threshold,
        guaranteed_winners=winners,
        required_missions=(
            missions[:active_threshold] if active_threshold is not None else ()
        ),
    )
