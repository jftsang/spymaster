"""Canonical, immutable positions derived from the game state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spymaster.spymaster import AgentCard, MissionCard, Spymaster


@dataclass(frozen=True)
class Position:
    """A compact, immutable (and therefore hashable) view of a game
    state from White's perspective.

    Players are presented with full game states (`Spymaster`), which
    also include game history and player identities, allowing players
    to make adaptive decisions based on them. This `Position` class is
    used for minimax search and other evaluations that do not use such
    information.

    This class is used both during a round, when `current_mission` is
    not None; and between rounds or at evaluator leaf positions, when
    `current_mission` is None. The set `missions` includes the current
    mission when one is set. Only the score margin matters to analysis,
    so `diff` stores `white_score - black_score`.
    """

    ours: frozenset[AgentCard]
    theirs: frozenset[AgentCard]
    missions: frozenset[MissionCard]
    current_mission: MissionCard | None
    diff: int

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
            diff=game_state.white_score - game_state.black_score,
        )

    def flipped(self) -> Position:
        """Return the same position from the other player's perspective."""
        return Position(
            ours=self.theirs,
            theirs=self.ours,
            missions=self.missions,
            current_mission=self.current_mission,
            diff=-self.diff,
        )
