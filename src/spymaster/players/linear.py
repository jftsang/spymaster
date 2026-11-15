from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import ClassVar

import numpy as np

from spymaster import AgentCard, Spymaster
from spymaster.players.evolutionary_players import EvolutionaryPlayer

DEFAULT_WEIGHTS_PATH = Path("slp_weights.npy")


class LinearPlayer(EvolutionaryPlayer):
    INPUTS_LENGTH: ClassVar[int] = 16 + 16 + 16 + 1 + 1 + 1

    def __init__(self, name: str, weights_matrix: np.ndarray):
        super().__init__(name=name)
        weights_matrix = weights_matrix.astype(np.float32)
        if weights_matrix.shape != (16, self.INPUTS_LENGTH):
            raise ValueError(f"Invalid shape: {weights_matrix.shape}")
        self.weights_matrix = weights_matrix

    @classmethod
    def randomized(cls) -> LinearPlayer:
        return cls(
            name="Randomized Single Linear Layer Player",
            weights_matrix=np.random.normal(0, 1, (16, cls.INPUTS_LENGTH)),
        )

    def save(self, path: str) -> None:
        np.save(path, self.weights_matrix)

    @classmethod
    def load(
        cls, path: str, name: str = "Single Layer Perceptron Player"
    ) -> LinearPlayer:
        return cls(name=name, weights_matrix=np.load(path))

    def __str__(self):
        white_weights = self.weights_matrix[:, :16]
        black_weights = self.weights_matrix[:, 16:32]
        mission_weights = self.weights_matrix[:, 32:48]
        current_mission_weight = self.weights_matrix[:, 48]
        score_weights = self.weights_matrix[:, 49:51]
        return f"""{self.__class__.__name__}(
    white_weights={white_weights},
    black_weights={black_weights},
    mission_weights={mission_weights},
    current_mission_weight={current_mission_weight},
    score_weights={score_weights},
)"""

    def create_offspring(self, mutation_rate: float = 0.1) -> LinearPlayer:
        new_weights = self.weights_matrix.copy()
        new_weights += np.random.normal(0, mutation_rate, self.weights_matrix.shape)
        return LinearPlayer(name=self.name, weights_matrix=new_weights)

    def to_vector(self, state: Spymaster) -> np.ndarray:
        vec = np.zeros(self.INPUTS_LENGTH, dtype=np.float32)
        for i in state.white_cards:
            vec[i] = 1
        for i in state.black_cards:
            vec[i + 16] = 1
        for i in state.remaining_missions:
            vec[i - 1 + 32] = 1

        vec[16 + 16 + 16] = state.current_mission
        vec[16 + 16 + 16 + 1] = state.white_score
        vec[16 + 16 + 16 + 2] = state.black_score
        return vec

    async def pick(self, state: Spymaster) -> AgentCard:
        vec = self.to_vector(state)
        choices_weights = self.weights_matrix @ vec
        choices_weights[vec[:16] == 0] = -np.inf
        max_weight = np.max(choices_weights)
        exp_weights = np.exp(choices_weights - max_weight)
        probabilities = exp_weights / np.sum(exp_weights)
        choice = int(np.random.choice(len(probabilities), p=probabilities))
        return AgentCard(choice)


async def train_against(
    opponent_names: str | Sequence[str] = "AI (Benchmark, Hard)",
    n_players: int = 32,
    n_iterations: int = 200,
    n_games: int = 30,
    n_replace: int = 8,
    mutation_rate: float = 0.1,
    seed: int | None = 0,
) -> LinearPlayer:
    """Train a population of SingleLayerPerceptronPlayers against one or
    more named computer players and return the best player found.

    When several opponents are named, each game picks one uniformly at
    random, so candidates face a shuffled, evenly-mixed set of
    opponents.
    """
    if isinstance(opponent_names, str):
        opponent_names = [opponent_names]

    from spymaster.gene_pool import make_gene_pool

    pool = make_gene_pool(
        opponent_names,
        n_players=n_players,
        n_games=n_games,
        n_replace=n_replace,
        mutation_rate=mutation_rate,
        seed=seed,
    )
    await pool.simulate(n_iterations)

    best = pool.best_player
    assert isinstance(best, LinearPlayer)
    return best


async def run_gene_pool(
    opponent_names: str | Sequence[str] = "AI (Benchmark, Hard)",
    n_players: int = 32,
    n_iterations: int = 200,
    n_games: int = 30,
    n_replace: int = 8,
    mutation_rate: float = 0.1,
    seed: int | None = 0,
    test_games: int = 100,
    output: str | Path = DEFAULT_WEIGHTS_PATH,
) -> dict[str, tuple[int, int, int]]:
    """Train the gene pool against the named opponent(s), save the best
    weights to ``output``, then play ``test_games`` games against each
    named opponent and report the results.
    """
    if isinstance(opponent_names, str):
        opponent_names = [opponent_names]

    best = await train_against(
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
    print(f"Saved best weights to {output.resolve()}")

    optimized = LinearPlayer.load(
        str(output), name="Optimized Single Layer Perceptron Player"
    )
    from spymaster.gene_pool import evaluate_and_report

    return await evaluate_and_report(
        optimized,
        list(opponent_names),
        test_games,
        "Optimized player vs opponents",
    )


WEIGHTS_DIR = Path(__file__).parent.parent / "weights"
LINEAR_CHINA_WEIGHTS_PATH = WEIGHTS_DIR / "linear_weights_china.npy"
LINEAR_FRANCE_WEIGHTS_PATH = WEIGHTS_DIR / "linear_weights_france.npy"
LINEAR_BRITAIN_WEIGHTS_PATH = WEIGHTS_DIR / "linear_weights_britain.npy"
LINEAR_AMERICA_WEIGHTS_PATH = WEIGHTS_DIR / "linear_weights_america.npy"
LINEAR_RUSSIA_WEIGHTS_PATH = WEIGHTS_DIR / "linear_weights_russia.npy"
LINEAR_BENCHMARK_WEIGHTS_PATH = WEIGHTS_DIR / "linear_weights_benchmark.npy"

LINEAR_CHINA_NAME = "AI (Linear Layer #1)"
LINEAR_FRANCE_NAME = "AI (Linear Layer #2)"
LINEAR_BRITAIN_NAME = "AI (Linear Layer #3)"
LINEAR_AMERICA_NAME = "AI (Linear Layer #4)"
LINEAR_RUSSIA_NAME = "AI (Linear Layer #5)"
LINEAR_BENCHMARK_NAME = "AI (Linear Layer #6)"

# Trained SingleLinearLayer players, keyed by display name.
LINEAR_PLAYER_SPECS: list[tuple[str, Path]] = [
    (LINEAR_CHINA_NAME, LINEAR_CHINA_WEIGHTS_PATH),
    (LINEAR_FRANCE_NAME, LINEAR_FRANCE_WEIGHTS_PATH),
    (LINEAR_BRITAIN_NAME, LINEAR_BRITAIN_WEIGHTS_PATH),
    (LINEAR_AMERICA_NAME, LINEAR_AMERICA_WEIGHTS_PATH),
    (LINEAR_RUSSIA_NAME, LINEAR_RUSSIA_WEIGHTS_PATH),
    (LINEAR_BENCHMARK_NAME, LINEAR_BENCHMARK_WEIGHTS_PATH),
]

LINEAR_PLAYERS_FACTORIES = {
    _name: partial(LinearPlayer.load, str(_path), _name)
    for _name, _path in LINEAR_PLAYER_SPECS
    if _path.exists()
}
