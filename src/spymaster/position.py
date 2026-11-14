"""Canonical, immutable positions derived from the game state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spymaster.spymaster import AgentCard, MissionCard, Spymaster


@dataclass(frozen=True)
class Position:
    """A compact view of a game state from White's perspective.

    History, player identities, and mission order are omitted because
    they do not affect minimax search. Players are still presented with
    full game states rather than positions, since they may make adaptive
    decisions based on game history or the identity of the other player.
    The missions include the current mission when one is set, and
    ``current_mission`` identifies it. For evaluator leaf positions,
    ``current_mission`` is None.
    """

    ours: frozenset[AgentCard]
    theirs: frozenset[AgentCard]
    missions: frozenset[MissionCard]
    current_mission: MissionCard | None
    white_score: int
    black_score: int

    @classmethod
    def of(cls, game_state: Spymaster) -> Position:
        """Build a position from the current state of a game."""
        missions = set(game_state.remaining_missions)
        if game_state.current_mission is not None:
            missions.add(game_state.current_mission)
        return cls(
            ours=frozenset(game_state.white_cards),
            theirs=frozenset(game_state.black_cards),
            missions=frozenset(missions),
            current_mission=game_state.current_mission,
            white_score=game_state.white_score,
            black_score=game_state.black_score,
        )
