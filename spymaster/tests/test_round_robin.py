import asyncio
import unittest

from spymaster.players import players
from ..spymaster import Spymaster

players = list(players.values())


class TestRoundRobin(unittest.TestCase):
    def test_round_robin(self):
        scores = [0] * len(players)
        for i, w in enumerate(players):
            for j, b in enumerate(players[i + 1 :], i + 1):
                with self.subTest(f"{w.name} vs {b.name}"):
                    for _ in range(10):
                        game = Spymaster(white=w, black=b)
                        asyncio.run(game.play())
                        # game.print_score()
                        if game.white_score > game.black_score:
                            scores[i] += 1
                        elif game.black_score > game.white_score:
                            scores[j] += 1
                        else:
                            scores[i] += 0.5
                            scores[j] += 0.5
                        # print("---")

        for score, player in zip(scores, players):
            print(f"{player.name} scored {score} points")

        self.assertTrue(all(score >= 0 for score in scores))
