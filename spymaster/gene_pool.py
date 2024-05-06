import abc
import asyncio
from typing import List, Optional

import numpy as np
from tqdm import tqdm

from spymaster.players import Player, russia
from spymaster.players.evolutionary_players import (
    EvolutionaryPlayer,
    SingleLayerPerceptronPlayer,
)
from spymaster import Spymaster


class Tournament(abc.ABC):
    @abc.abstractmethod
    async def play(self, players: List[Player]) -> List[float]:
        pass


class RoundRobinTournament(Tournament):
    async def play(self, players: List[Player]):
        """Round-robin tournament between all pairs of players. Each
        pair plays two games.
        """
        n_players = len(players)
        scores = [0] * n_players

        games: List[Optional[Spymaster]] = [None] * n_players * n_players
        awaitables = []

        for i in range(n_players):
            for j in range(n_players):
                if i == j:
                    continue
                # print(i, j)
                white = players[i]
                black = players[j]
                game = Spymaster(white=white, black=black)
                games[i * n_players + j] = game
                awaitables.append(game.play())

        # Wait for all games to finish
        done, pending = await asyncio.wait(awaitables)

        for i in range(n_players):
            for j in range(n_players):
                if i == j:
                    continue

                game = games[i * n_players + j]
                # scores[i] += game.white_score
                # scores[j] += game.black_score
                if game.white_score > game.black_score:
                    scores[i] += 1
                elif game.black_score > game.white_score:
                    scores[j] += 1
                else:
                    scores[i] += 0.5
                    scores[j] += 0.5
        return scores


class PlayAgainstChallengerTournament(Tournament):
    def __init__(self, challenger: Player = russia):
        self.challenger = challenger

    async def play(self, players: List[Player]) -> List[float]:
        n_players = len(players)
        scores = [0] * n_players

        for i in range(n_players):
            white = players[i]
            black = self.challenger
            games = [Spymaster(white=white, black=black) for _ in range(30)]
            awaitables = [game.play() for game in games]
            done, pending = await asyncio.wait(awaitables)

            for game in games:
                scores[i] += game.white_score
                scores[i] -= game.black_score

        return scores


class FitnessEvaluator:
    async def evaluate_population(self, gene_pool: "GenePool") -> float:

        """Evaluate the population fitness by how well they play against
        the reference player.
        """
        fitness = 0
        games = []
        awaitables = []
        for i in range(gene_pool.n_players):
            white = gene_pool.players[i]
            black = russia
            game = Spymaster(white=white, black=black)
            games.append(game)
            awaitables.append(game.play())

        done, pending = await asyncio.wait(awaitables)

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
        reference_player: Player = russia,
        n_replace: int = 20,
        mutation_rate: float = 0.1
    ):
        self.n_players = n_players
        self.reference_player = reference_player
        self.players: List[EvolutionaryPlayer] = [
            SingleLayerPerceptronPlayer.randomized() for _ in range(n_players)
        ]
        self.tournament = tournament
        self.fitness_evaluator = FitnessEvaluator()
        self.n_replace = n_replace
        self.mutation_rate = mutation_rate

    def replacement(self, scores):
        # Rank the players from worst to best
        sorted_players_indices = sorted(range(self.n_players), key=lambda i: scores[i])

        # Replace the worst players
        for i in range(self.n_replace):
            idx_to_replace = sorted_players_indices[i]
            new_parent_idx = sorted_players_indices[-i - 1]
            self.players[idx_to_replace] = self.players[new_parent_idx].create_offspring(self.mutation_rate)

        # Replace the worst players with the offspring of the best players
        parents = self.players[:self.n_replace]
        children = [parent.create_offspring(self.mutation_rate) for parent in parents]
        self.players[-self.n_replace:] = children

    async def simulate(self, n_iterations):
        for t in tqdm(range(n_iterations)):
            scores = await self.tournament.play(self.players)
            fitness = await self.fitness_evaluator.evaluate_population(self)
            print(
                f"{t}: max score = {max(scores)}, "
                f"min score = {min(scores)}, "
                f"fitness = {fitness}"
            )

            self.replacement(scores)

    @property
    def best_player(self):
        return self.players[0]


if __name__ == "__main__":
    np.random.seed(0)
    pool = GenePool(n_players=32, tournament=PlayAgainstChallengerTournament(russia), n_replace=8, mutation_rate=0.1)
    asyncio.run(pool.simulate(n_iterations=1000))
    print(pool.best_player)
