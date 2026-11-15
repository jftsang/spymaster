from functools import partial

from spymaster.players import Player

from .adaptive import TUNED_ADAPTIVE_FACTORIES
from .benchmarks import (
    BENCHMARK_FACTORIES,
)
from .linear import LINEAR_PLAYERS_FACTORIES
from .minimax.nash_players import NASH_PLAYER_NAME, NashPlayer

FACTORIES = {}
FACTORIES[NASH_PLAYER_NAME] = partial(NashPlayer, name=NASH_PLAYER_NAME)
FACTORIES.update(BENCHMARK_FACTORIES)
FACTORIES.update(LINEAR_PLAYERS_FACTORIES)
FACTORIES.update(TUNED_ADAPTIVE_FACTORIES)


def new_computer_player(name: str) -> Player:
    """Create a fresh AI player instance. Fresh instances can play many
    games simultaneously without sharing mutable state."""
    try:
        return FACTORIES[name]()
    except KeyError as e:
        raise KeyError(f"Unknown computer player: {name}") from e
