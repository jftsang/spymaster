import abc
import asyncio
from pathlib import Path
from random import choice
from typing import Callable, List, Optional, Sequence

import numpy as np
from tqdm import tqdm

from spymaster.players import Player
from spymaster.players.benchmarks import default_computer_player_names
from spymaster.players.computer_players import (
    TUNED_ADAPTIVE_PARAMS_PATH,
    TunedAdaptivePlayer,
    computer_players,
    new_computer_player,
)
from spymaster.players.evolutionary_players import (
    EvolutionaryPlayer,
    LinearPlayer,
)
from spymaster import Spymaster

PlayerFactory = Callable[[], Player]
EvolutionaryPlayerFactory = Callable[[], EvolutionaryPlayer]

DEFAULT_WEIGHTS_PATH = Path("slp_weights.npy")


def america_factory() -> Player:
    """Create a fresh America player. Fresh instances can play many
    games simultaneously without sharing mutable state."""
    return new_computer_player("AI (Hard)")


class Tournament(abc.ABC):
    @abc.abstractmethod
    async def play(self, players: Sequence[Player]) -> List[float]:
        pass


class RoundRobinTournament(Tournament):
    async def play(self, players: Sequence[Player]) -> List[float]:
        """Round-robin tournament between all pairs of players. Each
        pair plays two games.
        """
        n_players = len(players)
        scores: List[float] = [0.0] * n_players

        games: List[Optional[Spymaster]] = [None] * n_players * n_players
        awaitables = []

        for i in range(n_players):
            for j in range(n_players):
                if i == j:
                    continue
                white = players[i]
                black = players[j]
                game = Spymaster(white=white, black=black)
                games[i * n_players + j] = game
                awaitables.append(game.play())

        await asyncio.gather(*awaitables)

        for i in range(n_players):
            for j in range(n_players):
                if i == j:
                    continue

                game = games[i * n_players + j]
                if game is None:
                    continue
                if game.white_score > game.black_score:
                    scores[i] += 1
                elif game.black_score > game.white_score:
                    scores[j] += 1
                else:
                    scores[i] += 0.5
                    scores[j] += 0.5
        return scores


class PlayAgainstChallengerTournament(Tournament):
    """Play each player against one or more challengers, using factories
    so that every game gets a fresh challenger instance (challengers such
    as AmericaPlayer keep mutable state between rounds).

    When several challengers are given, each game picks one uniformly at
    random, so the candidates face a shuffled, evenly-mixed mix of
    opponents.
    """

    def __init__(
        self,
        challenger_factories: Sequence[PlayerFactory] = (america_factory,),
        n_games: int = 30,
    ):
        self.challenger_factories: List[PlayerFactory] = list(challenger_factories)
        self.n_games = n_games

    async def play(self, players: Sequence[Player]) -> List[float]:
        per_player_games: List[List[Spymaster]] = []
        for white in players:
            player_games = []
            for _ in range(self.n_games):
                factory = choice(self.challenger_factories)
                player_games.append(Spymaster(white=white, black=factory()))
            per_player_games.append(player_games)

        await asyncio.gather(
            *(game.play() for games in per_player_games for game in games)
        )

        return [
            sum(game.white_score - game.black_score for game in games)
            for games in per_player_games
        ]


class FitnessEvaluator:
    def __init__(self, reference_factory: PlayerFactory = america_factory):
        self.reference_factory = reference_factory

    async def evaluate_population(self, gene_pool: "GenePool") -> float:
        """Evaluate the population fitness by how well they play against
        the reference player.
        """
        games = [
            Spymaster(
                white=gene_pool.players[i], black=self.reference_factory()
            )
            for i in range(gene_pool.n_players)
        ]
        await asyncio.gather(*(game.play() for game in games))

        fitness = 0.0
        for game in games:
            if game.white_score > game.black_score:
                fitness += 1
            elif game.white_score == game.black_score:
                fitness += 0.5

        return fitness


class GenePool:
    def __init__(
        self,
        n_players: int,
        tournament: Tournament,
        population_factory: EvolutionaryPlayerFactory = LinearPlayer.randomized,
        reference_factory: PlayerFactory = america_factory,
        n_replace: int = 20,
        mutation_rate: float = 0.1,
    ):
        self.n_players = n_players
        self.reference_factory = reference_factory
        self.players: List[EvolutionaryPlayer] = [
            population_factory() for _ in range(n_players)
        ]
        self.tournament = tournament
        self.fitness_evaluator = FitnessEvaluator(reference_factory)
        self.n_replace = n_replace
        self.mutation_rate = mutation_rate
        self._best_player: Optional[EvolutionaryPlayer] = None
        self._best_score = float("-inf")

    def replacement(self, scores):
        # Rank the players from best to worst
        ranked = sorted(
            range(self.n_players), key=lambda i: scores[i], reverse=True
        )
        n_survivors = max(1, self.n_players - self.n_replace)
        survivors = [self.players[i] for i in ranked[:n_survivors]]

        # Replace the worst players with offspring of the best players
        for offset, idx in enumerate(ranked[n_survivors:]):
            parent = survivors[offset % len(survivors)]
            self.players[idx] = parent.create_offspring(self.mutation_rate)

    async def simulate(self, n_iterations: int):
        for t in tqdm(range(n_iterations)):
            scores = await self.tournament.play(self.players)
            best_idx = max(range(self.n_players), key=lambda i: scores[i])
            if scores[best_idx] > self._best_score:
                self._best_score = scores[best_idx]
                self._best_player = self.players[best_idx]

            fitness = await self.fitness_evaluator.evaluate_population(self)
            print(
                f"{t}: max score = {max(scores)}, "
                f"min score = {min(scores)}, "
                f"fitness = {fitness}"
            )

            self.replacement(scores)

    @property
    def best_player(self) -> EvolutionaryPlayer:
        if self._best_player is not None:
            return self._best_player
        return self.players[0]


async def train_against(
    opponent_name: str = "AI (Hard)",
    n_players: int = 32,
    n_iterations: int = 200,
    n_games: int = 30,
    n_replace: int = 8,
    mutation_rate: float = 0.1,
    seed: Optional[int] = 0,
) -> LinearPlayer:
    """Train a population of SingleLayerPerceptronPlayers against the
    named computer player and return the best player found.
    """
    if seed is not None:
        np.random.seed(seed)

    def factory() -> Player:
        return new_computer_player(opponent_name)

    pool = GenePool(
        n_players=n_players,
        tournament=PlayAgainstChallengerTournament([factory], n_games=n_games),
        reference_factory=factory,
        n_replace=n_replace,
        mutation_rate=mutation_rate,
    )
    await pool.simulate(n_iterations)

    best = pool.best_player
    assert isinstance(best, LinearPlayer)
    return best


def benchmark_player_factories(
    names: Optional[Sequence[str]] = None,
) -> List[PlayerFactory]:
    """Return a fresh factory for each benchmark player named, or for
    every default computer player when ``names`` is ``None``.
    """
    if names is None:
        names = default_computer_player_names
    return [lambda name=name: new_computer_player(name) for name in names]


async def train_tuned_adaptive(
    opponent_names: Optional[Sequence[str]] = None,
    n_players: int = 32,
    n_iterations: int = 100,
    n_games: int = 20,
    n_replace: int = 8,
    mutation_rate: float = 0.1,
    seed: Optional[int] = 0,
) -> TunedAdaptivePlayer:
    """Evolve a population of TunedAdaptivePlayers against the named
    benchmark players and return the best individual found.
    """
    if seed is not None:
        np.random.seed(seed)

    factories = benchmark_player_factories(opponent_names)
    pool = GenePool(
        n_players=n_players,
        tournament=PlayAgainstChallengerTournament(factories, n_games=n_games),
        population_factory=TunedAdaptivePlayer.randomized,
        reference_factory=factories[0],
        n_replace=n_replace,
        mutation_rate=mutation_rate,
    )
    await pool.simulate(n_iterations)

    best = pool.best_player
    assert isinstance(best, TunedAdaptivePlayer)
    return best


async def evaluate_against_computer_players(
    player: Player,
    n_games: int = 100,
    opponent_names: Optional[List[str]] = None,
) -> dict[str, tuple[int, int, int]]:
    """Play ``n_games`` games against each default computer player,
    always as White. Returns a mapping of opponent name to a
    ``(wins, draws, losses)`` tuple.
    """
    if opponent_names is None:
        opponent_names = list(computer_players.keys())

    results: dict[str, tuple[int, int, int]] = {}
    for name in opponent_names:
        games = [
            Spymaster(white=player, black=new_computer_player(name))
            for _ in range(n_games)
        ]
        await asyncio.gather(*(game.play() for game in games))

        wins = sum(g.white_score > g.black_score for g in games)
        draws = sum(g.white_score == g.black_score for g in games)
        losses = n_games - wins - draws
        results[name] = (wins, draws, losses)

    return results


async def head_to_head(
    player_a: Player,
    player_b: Player,
    n_games: int = 100,
) -> tuple[int, int, int]:
    """Play ``player_a`` against ``player_b``, ``n_games`` with each as
    White. Returns ``(a_wins, draws, b_wins)`` from A's point of view.

    Both players must be stateless (safe to reuse across games) -- true
    for SingleLayerPerceptronPlayers.
    """
    games = [
        Spymaster(white=player_a, black=player_b) for _ in range(n_games)
    ] + [
        Spymaster(white=player_b, black=player_a) for _ in range(n_games)
    ]
    await asyncio.gather(*(game.play() for game in games))

    a_wins = draws = b_wins = 0
    for game in games:
        if game.white is player_a:
            a_score, b_score = game.white_score, game.black_score
        else:
            a_score, b_score = game.black_score, game.white_score
        if a_score > b_score:
            a_wins += 1
        elif a_score < b_score:
            b_wins += 1
        else:
            draws += 1
    return a_wins, draws, b_wins


async def run_gene_pool(
    opponent_name: str = "AI (Hard)",
    n_players: int = 32,
    n_iterations: int = 200,
    n_games: int = 30,
    n_replace: int = 8,
    mutation_rate: float = 0.1,
    seed: Optional[int] = 0,
    test_games: int = 100,
    output: str | Path = DEFAULT_WEIGHTS_PATH,
) -> dict[str, tuple[int, int, int]]:
    """Train the gene pool against ``opponent_name``, save the best
    weights to ``output``, then play ``test_games`` games against each
    default computer player and report the results.
    """
    best = await train_against(
        opponent_name=opponent_name,
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
    results = await evaluate_against_computer_players(
        optimized, n_games=test_games
    )

    print(f"\nOptimized player vs default computer players ({test_games} games):")
    for name, (wins, draws, losses) in results.items():
        points = wins + 0.5 * draws
        print(
            f"  {name}: {wins}W {draws}D {losses}L "
            f"({points / test_games:.1%})"
        )

    return results


async def run_tuning(
    n_players: int = 32,
    n_iterations: int = 100,
    n_games: int = 20,
    n_replace: int = 8,
    mutation_rate: float = 0.1,
    seed: Optional[int] = 0,
    test_games: int = 100,
    opponent_names: Optional[Sequence[str]] = None,
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
        list(opponent_names)
        if opponent_names
        else list(default_computer_player_names)
    )
    results = await evaluate_against_computer_players(
        tuned, n_games=test_games, opponent_names=names
    )

    print(f"\nTuned player vs benchmark players ({test_games} games):")
    for name, (wins, draws, losses) in results.items():
        points = wins + 0.5 * draws
        print(
            f"  {name}: {wins}W {draws}D {losses}L "
            f"({points / test_games:.1%})"
        )

    return results


if __name__ == "__main__":
    asyncio.run(run_gene_pool())
