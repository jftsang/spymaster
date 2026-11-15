"""Helpers for resolving simultaneous card choices."""

from spymaster import AgentCard, MissionCard, Position
from spymaster.spymaster import ASSASSIN


def child_position(
    position: Position,
    ours: AgentCard,
    theirs: AgentCard,
) -> Position:
    """Return the position after both players resolve the current mission."""
    assert position.current_mission is not None
    white_score, black_score = resolve_score(
        ours,
        theirs,
        position.current_mission,
    )
    return Position(
        ours=position.ours - {ours},
        theirs=position.theirs - {theirs},
        missions=position.missions - {position.current_mission},
        current_mission=None,
        white_score=position.white_score + white_score,
        black_score=position.black_score + black_score,
    )


def resolve_score(
    ours: AgentCard,
    theirs: AgentCard,
    mission: MissionCard,
) -> tuple[int, int]:
    """Return the White and Black scores from resolving one mission."""
    if ours == theirs:
        return 0, 0
    if ours == ASSASSIN:
        return int(theirs), 0
    if theirs == ASSASSIN:
        return 0, int(ours)
    if ours > theirs:
        return int(mission), 0
    return 0, int(mission)
