from collections.abc import Sequence
from functools import partial
from pathlib import Path
from random import gauss, random

import numpy as np

from spymaster.gene_pool import evaluate_and_report, make_gene_pool

from .benchmarks import (
    BENCHMARK_FACTORIES,
    RussiaPlayer,
)
from .evolutionary_players import EvolutionaryPlayer

WEIGHTS_DIR = Path(__file__).parent.parent / "weights"
TUNED_ADAPTIVE_NAME = "AI (Adaptive Ducker)"
TUNED_ADAPTIVE_PARAMS_PATH = WEIGHTS_DIR / "adaptive_ducker.npy"


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
    def randomized(cls) -> TunedAdaptivePlayer:
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

    def create_offspring(self, mutation_rate: float = 0.1) -> TunedAdaptivePlayer:
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
    ) -> TunedAdaptivePlayer:
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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


async def train_tuned_adaptive(
    opponent_names: Sequence[str] | None = None,
    n_players: int = 32,
    n_iterations: int = 100,
    n_games: int = 20,
    n_replace: int = 8,
    mutation_rate: float = 0.1,
    seed: int | None = 0,
) -> TunedAdaptivePlayer:
    """Evolve a population of TunedAdaptivePlayers against the named
    benchmark players and return the best individual found.
    """
    pool = make_gene_pool(
        opponent_names,
        n_players=n_players,
        n_games=n_games,
        n_replace=n_replace,
        mutation_rate=mutation_rate,
        seed=seed,
        population_factory=TunedAdaptivePlayer.randomized,
    )
    await pool.simulate(n_iterations)

    best = pool.best_player
    assert isinstance(best, TunedAdaptivePlayer)
    return best


async def run_tuning(
    n_players: int = 32,
    n_iterations: int = 100,
    n_games: int = 20,
    n_replace: int = 8,
    mutation_rate: float = 0.1,
    seed: int | None = 0,
    test_games: int = 100,
    opponent_names: Sequence[str] | None = None,
    output: str | Path = TUNED_ADAPTIVE_PARAMS_PATH,
) -> dict[str, tuple[int, int, int]]:
    """Evolve TunedAdaptivePlayer's parameters against all five
    benchmark players, save them to ``output``, then play ``test_games``
    games against each benchmark player and report the results.
    """
    best = await train_tuned_adaptive(
        opponent_names=opponent_names,
        n_players=n_players,
        n_iterations=n_iterations,
        n_games=n_games,
        n_replace=n_replace,
        mutation_rate=mutation_rate,
        seed=seed,
    )

    output = Path(output)
    best.save(str(output))
    print(f"Saved tuned parameters to {output.resolve()}")
    print(best)

    tuned = TunedAdaptivePlayer.load(str(output), name="Tuned Adaptive Player")
    names = list(opponent_names) if opponent_names else list(BENCHMARK_FACTORIES.keys())
    return await evaluate_and_report(
        tuned,
        names,
        test_games,
        "Tuned player vs benchmark players",
    )


TUNED_ADAPTIVE_FACTORIES = {
    TUNED_ADAPTIVE_NAME: partial(
        TunedAdaptivePlayer.load, TUNED_ADAPTIVE_PARAMS_PATH, TUNED_ADAPTIVE_NAME
    )
}
