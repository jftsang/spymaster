"""Position analysis interface for minimax players."""

from typing import Protocol

from spymaster import AgentCard, Position

Analysis = tuple[tuple[AgentCard, ...], tuple[float, ...], float]


class Analyser(Protocol):
    def analyse(self, position: Position) -> tuple[list[AgentCard], list[float], float]: ...
