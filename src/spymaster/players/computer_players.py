from spymaster.players import Player

from .adaptive import TUNED_ADAPTIVE_FACTORIES
from .benchmarks import (
    BENCHMARK_FACTORIES,
)
from .linear import LINEAR_PLAYERS_FACTORIES
from .minimax.nash_players import NASH_FACTORIES

FACTORIES = {}
FACTORIES.update(NASH_FACTORIES)
FACTORIES.update(TUNED_ADAPTIVE_FACTORIES)
FACTORIES.update(BENCHMARK_FACTORIES)
FACTORIES.update(LINEAR_PLAYERS_FACTORIES)


def new_computer_player(name: str) -> Player:
    """Create or return an AI player instance.

    Factories should generally return a fresh instance of a Player, so
    that different Players play different games without sharing mutable
    state. However, if a Player does not have mutable state then they
    may be cached across games; the factory should be responsible for
    making that decision.
    """
    try:
        return FACTORIES[name]()
    except KeyError as e:
        raise KeyError(f"Unknown computer player: {name}") from e
