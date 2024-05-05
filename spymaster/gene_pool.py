import asyncio
from typing import List, Optional

import numpy as np
from tqdm import tqdm

from spymaster.players.evolutionary_players import (
    EvolutionaryPlayer,
    SingleLayerPerceptronPlayer,
)
from spymaster import Spymaster


class GenePool:
    def __init__(self, n_players: int = 100, n_replace: int = 20, mutation_rate: float = 0.1):
        self.n_players = n_players
        self.players: List[EvolutionaryPlayer] = [
            SingleLayerPerceptronPlayer.randomized() for _ in range(n_players)
        ]
        self.n_replace = n_replace
        self.mutation_rate = mutation_rate

    async def calculate_fitnesses(self):
        scores = [0] * self.n_players

        games: List[Optional[Spymaster]] = [None] * self.n_players * self.n_players
        awaitables = []

        # Each pair of players plays two games against each other
        for i in range(self.n_players):
            for j in range(self.n_players):
                if i == j:
                    continue
                # print(i, j)
                white = self.players[i]
                black = self.players[j]
                game = Spymaster(white=white, black=black)
                games[i * self.n_players + j] = game
                awaitables.append(game.play())

        # Wait for all games to finish
        done, pending = await asyncio.wait(awaitables)

        for i in range(self.n_players):
            for j in range(self.n_players):
                if i == j:
                    continue

                game = games[i * self.n_players + j]
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
            scores = await self.calculate_fitnesses()
            print(
                f"{t}: max score = {max(scores)}, "
                f"min score = {min(scores)}"
            )
            self.replacement(scores)

    @property
    def best_player(self):
        return self.players[0]


if __name__ == "__main__":
    np.random.seed(0)
    pool = GenePool(n_players=32, n_replace=4, mutation_rate=0.05)
    asyncio.run(pool.simulate(n_iterations=1000))
    print(pool.best_player)
