from pathlib import Path
from random import gauss, random

import numpy as np

from spymaster.players import Player

from .benchmarks import (
    AmericaPlayer,
    RandomPlayer,
    RussiaPlayer,
    SimpleAimingPlayer,
    default_computer_players,
)
from .evolutionary_players import EvolutionaryPlayer

WEIGHTS_DIR = Path(__file__).parent.parent / "weights"
LINEAR_AMERICA_WEIGHTS_PATH = WEIGHTS_DIR / "linear_weights_america.npy"
LINEAR_RUSSIA_WEIGHTS_PATH = WEIGHTS_DIR / "linear_weights_russia.npy"

TUNED_ADAPTIVE_PARAMS_PATH = WEIGHTS_DIR / "tuned_adaptive.npy"

LINEAR_AMERICA_NAME = "AI (Single Linear Layer #1)"
LINEAR_RUSSIA_NAME = "AI (Single Linear Layer #2)"

_perceptron_cache: dict[Path, Player] = {}


def load_perceptron(name: str, weights_path: Path) -> Player:
    """Load a SingleLayerPerceptronPlayer from saved weights. Loaded
    players are cached and reused; they carry no mutable state, so a
    single instance can play many games simultaneously.
    """
    from spymaster.players.evolutionary_players import LinearPlayer

    if weights_path not in _perceptron_cache:
        _perceptron_cache[weights_path] = LinearPlayer.load(
            str(weights_path), name=name
        )
    return _perceptron_cache[weights_path]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class TunedAdaptivePlayer(RussiaPlayer, EvolutionaryPlayer):
    """A RussiaPlayer whose bloodthirst, paranoia, and idleness are
    evolved by the gene pool instead of being hand-set.

    The tuned parameters live in a three-dimensional genome encoded by
    the ``save``/``load`` functions, so they can be written to and read
    back from a ``.npy`` file like the perceptron weights.
    """

    def __init__(
        self,
        name: str = "Tuned Adaptive Player",
        bloodthirst: float = 0.5,
        paranoia: float = 0.5,
        idleness: float = 0.33,
    ):
        super().__init__(
            name=name,
            bloodthirst=bloodthirst,
            paranoia=paranoia,
            idleness=idleness,
        )

    @classmethod
    def randomized(cls) -> "TunedAdaptivePlayer":
        return cls(
            name="Randomized Tuned Adaptive Player",
            bloodthirst=random(),
            paranoia=random(),
            idleness=random(),
        )

    @property
    def genome(self) -> np.ndarray:
        return np.array(
            [self.bloodthirst, self.paranoia, self.idleness], dtype=np.float64
        )

    def create_offspring(self, mutation_rate: float = 0.1) -> "TunedAdaptivePlayer":
        return TunedAdaptivePlayer(
            name=self.name,
            bloodthirst=_clamp(self.bloodthirst + gauss(0.0, mutation_rate)),
            paranoia=_clamp(self.paranoia + gauss(0.0, mutation_rate)),
            idleness=_clamp(self.idleness + gauss(0.0, mutation_rate)),
        )

    def save(self, path: str | Path) -> None:
        np.save(path, self.genome)

    @classmethod
    def load(
        cls, path: str | Path, name: str = "Tuned Adaptive Player"
    ) -> "TunedAdaptivePlayer":
        params = np.load(path)
        return cls(
            name=name,
            bloodthirst=float(params[0]),
            paranoia=float(params[1]),
            idleness=float(params[2]),
        )

    def __str__(self) -> str:
        return (
            "TunedAdaptivePlayer(\n"
            f"    bloodthirst={self.bloodthirst},\n"
            f"    paranoia={self.paranoia},\n"
            f"    idleness={self.idleness},\n)"
        )


def new_computer_player(name: str) -> Player:
    """Create a fresh AI player instance. Fresh instances can play many
    games simultaneously without sharing mutable state."""
    factories = {
        "AI (Easiest)": lambda: RandomPlayer(name="AI (Easiest)"),
        "AI (Easy)": lambda: SimpleAimingPlayer(name="AI (Easy)", variance=2),
        "AI (Medium)": lambda: SimpleAimingPlayer(name="AI (Medium)", variance=4),
        "AI (Hard)": lambda: AmericaPlayer(name="AI (Hard)"),
        "AI (Hardest)": lambda: RussiaPlayer(
            name="AI (Hardest)", bloodthirst=0.5, paranoia=0.5, idleness=0.33
        ),
        LINEAR_AMERICA_NAME: lambda: load_perceptron(
            LINEAR_AMERICA_NAME, LINEAR_AMERICA_WEIGHTS_PATH
        ),
        LINEAR_RUSSIA_NAME: lambda: load_perceptron(
            LINEAR_RUSSIA_NAME, LINEAR_RUSSIA_WEIGHTS_PATH
        ),
    }
    try:
        return factories[name]()
    except KeyError:
        raise KeyError(f"Unknown computer player: {name}")


computer_players: dict[str, Player] = {p.name: p for p in default_computer_players}

# Trained SingleLayerPerceptron players are registered only once their
# weight artifacts exist, so a fresh checkout still imports cleanly.
for _name, _path in [
    (LINEAR_AMERICA_NAME, LINEAR_AMERICA_WEIGHTS_PATH),
    (LINEAR_RUSSIA_NAME, LINEAR_RUSSIA_WEIGHTS_PATH),
]:
    if _path.exists():
        computer_players[_name] = load_perceptron(_name, _path)
