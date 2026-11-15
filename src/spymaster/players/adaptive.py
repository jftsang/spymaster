from collections.abc import Sequence
from pathlib import Path

from spymaster.gene_pool import evaluate_and_report, make_gene_pool
from spymaster.players.benchmarks import default_computer_player_names
from spymaster.players.computer_players import (
    TUNED_ADAPTIVE_PARAMS_PATH,
    TunedAdaptivePlayer,
)


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
    names = (
        list(opponent_names) if opponent_names else list(default_computer_player_names)
    )
    return await evaluate_and_report(
        tuned,
        names,
        test_games,
        "Tuned player vs benchmark players",
    )
