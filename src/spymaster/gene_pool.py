import asyncio
from collections.abc import Callable, Sequence
from functools import partial
from random import choice

import numpy as np
from tqdm.auto import tqdm

from spymaster import Spymaster
from spymaster.players import Player
from spymaster.players.benchmarks import BENCHMARK_FACTORIES
from spymaster.players.evolutionary_players import EvolutionaryPlayer
from spymaster.players.linear import LinearPlayer
from spymaster.tournament import Tournament

PlayerFactory = Callable[[], Player]
EvolutionaryPlayerFactory = Callable[[], EvolutionaryPlayer]


def _points(game: Spymaster) -> int:
    """Match points from White's perspective: 1 for a win, 0 for a
    draw, -1 for a loss. The margin of victory is irrelevant.
    """
    if game.white_score > game.black_score:
        return 1
    if game.white_score < game.black_score:
        return -1
    return 0


class PlayAgainstChallengerTournament(Tournament):
    """Play each player against one or more challengers, using FACTORIES
    so that every game gets a fresh challenger instance (challengers such
    as AdaptiveAimingPlayer keep mutable state between rounds).

    When several challengers are given, each game picks one uniformly at
    random, so the candidates face a shuffled, evenly-mixed mix of
    opponents.
    """

    def __init__(
        self,
        challenger_factories: Sequence[PlayerFactory],
        n_games: int = 30,
    ):
        self.challenger_factories: list[PlayerFactory] = list(challenger_factories)
        self.n_games = n_games

    async def play(self, players: Sequence[Player]) -> list[float]:
        per_player_games: list[list[Spymaster]] = []
        for white in players:
            player_games = []
            for _ in range(self.n_games):
                factory = choice(self.challenger_factories)
                player_games.append(Spymaster(white=white, black=factory()))
            per_player_games.append(player_games)

        await asyncio.gather(
            *(game.play() for games in per_player_games for game in games)
        )

        return [sum(_points(game) for game in games) for games in per_player_games]


class FitnessEvaluator:
    def __init__(
        self,
        reference_factories: Sequence[PlayerFactory],
    ):
        self.reference_factories = list(reference_factories)

    async def evaluate_population(self, gene_pool: GenePool) -> float:
        """Evaluate the population fitness by how well they play against
        the reference players. Each player faces every reference once.
        """
        games = [
            Spymaster(white=player, black=factory())
            for player in gene_pool.players
            for factory in self.reference_factories
        ]
        await asyncio.gather(*(game.play() for game in games))

        return sum(_points(game) for game in games)


class GenePool:
    def __init__(
        self,
        n_players: int,
        tournament: Tournament,
        population_factory: EvolutionaryPlayerFactory,
        reference_factories: Sequence[PlayerFactory],
        n_replace: int = 20,
        mutation_rate: float = 0.1,
    ):
        self.n_players = n_players
        self.reference_factories = list(reference_factories)
        self.players: list[EvolutionaryPlayer] = [
            population_factory() for _ in range(n_players)
        ]
        self.tournament = tournament
        self.fitness_evaluator = FitnessEvaluator(self.reference_factories)
        self.n_replace = n_replace
        self.mutation_rate = mutation_rate
        self._best_player: EvolutionaryPlayer | None = None
        self._best_score = float("-inf")

    def replacement(self, scores):
        # Rank the players from best to worst
        ranked = sorted(range(self.n_players), key=lambda i: scores[i], reverse=True)
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


def make_gene_pool(
    opponent_names: Sequence[str] | None,
    *,
    n_players: int,
    n_games: int,
    n_replace: int,
    mutation_rate: float,
    seed: int | None,
    population_factory: EvolutionaryPlayerFactory = LinearPlayer.randomized,
) -> GenePool:
    if seed is not None:
        np.random.seed(seed)

    factories = _opponent_factories(opponent_names)
    return GenePool(
        n_players=n_players,
        tournament=PlayAgainstChallengerTournament(factories, n_games=n_games),
        population_factory=population_factory,
        reference_factories=factories,
        n_replace=n_replace,
        mutation_rate=mutation_rate,
    )


def _opponent_factories(
    opponent_names: Sequence[str] | None,
) -> list[PlayerFactory]:
    """Return fresh-instance factories for the named opponents.

    Falls back to the benchmark players when no names are given. The
    import is deferred to avoid a circular import, since the computer
    player factories pull in modules that depend on this one.
    """
    if opponent_names is None:
        return list(BENCHMARK_FACTORIES.values())

    if not opponent_names:
        raise ValueError("At least one opponent name is required")

    from spymaster.players.computer_players import new_computer_player

    return [partial(new_computer_player, name) for name in opponent_names]


async def evaluate_against_computer_players(
    player: Player,
    n_games: int = 100,
    opponent_names: list[str] | None = None,
) -> dict[str, tuple[int, int, int]]:
    """Play ``n_games`` games against each default computer player,
    always as White. Returns a mapping of opponent name to a
    ``(wins, draws, losses)`` tuple.
    """
    from spymaster.players.computer_players import new_computer_player

    if opponent_names is None:
        opponent_names = list(BENCHMARK_FACTORIES.keys())

    results: dict[str, tuple[int, int, int]] = {}
    for opp_name in opponent_names:
        games = [
            Spymaster(white=player, black=new_computer_player(opp_name))
            for _ in range(n_games)
        ]

        with tqdm(desc=f"{player.name} vs {opp_name}", total=len(games)) as pbar:
            for fut in asyncio.as_completed([game.play() for game in games]):
                await fut
                pbar.update(1)

        wins = sum(g.white_score > g.black_score for g in games)
        draws = sum(g.white_score == g.black_score for g in games)
        losses = n_games - wins - draws
        results[opp_name] = (wins, draws, losses)

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
    games = [Spymaster(white=player_a, black=player_b) for _ in range(n_games)] + [
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


async def evaluate_and_report(
    player: Player,
    opponent_names: list[str],
    n_games: int,
    title: str,
) -> dict[str, tuple[int, int, int]]:
    results = await evaluate_against_computer_players(
        player, n_games=n_games, opponent_names=opponent_names
    )

    print(f"\n{title} ({n_games} games):")
    for name, (wins, draws, losses) in results.items():
        points = wins - losses
        print(f"  {name}: {wins}W {draws}D {losses}L (net {points:+d})")

    return results
