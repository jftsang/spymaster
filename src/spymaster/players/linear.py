from collections.abc import Sequence
from pathlib import Path

from spymaster.gene_pool import evaluate_and_report, make_gene_pool
from spymaster.players.evolutionary_players import LinearPlayer

DEFAULT_WEIGHTS_PATH = Path("slp_weights.npy")


async def train_against(
    opponent_names: str | Sequence[str] = "AI (Hard)",
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
    opponent_names: str | Sequence[str] = "AI (Hard)",
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
    return await evaluate_and_report(
        optimized,
        list(opponent_names),
        test_games,
        "Optimized player vs opponents",
    )
