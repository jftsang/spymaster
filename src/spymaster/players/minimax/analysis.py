"""Position analysis interface for minimax players."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from spymaster import AgentCard, Position


@dataclass(frozen=True)
class Analysis:
    """Equilibrium cards, strategy probabilities, and value for a position.

    The constructor accepts any sequences; they are stored as tuples so
    that cached analyses cannot be mutated through the original containers.
    """

    cards: tuple[AgentCard, ...]
    strategy: tuple[float, ...]
    value: float

    def __init__(
        self,
        cards: Sequence[AgentCard],
        strategy: Sequence[float],
        value: float,
    ) -> None:
        object.__setattr__(self, "cards", tuple(cards))
        object.__setattr__(self, "strategy", tuple(strategy))
        object.__setattr__(self, "value", value)


class Analyser(Protocol):
    def analyse(self, position: Position) -> Analysis: ...
