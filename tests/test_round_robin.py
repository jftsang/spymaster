import asyncio
import unittest

from spymaster.players import Player
from spymaster.players.computer_players import computer_players
from spymaster.spymaster import Spymaster

players = list(computer_players.values())


class TestRoundRobin(unittest.TestCase):
    def setUp(self):
        Spymaster.model_rebuild(_types_namespace={"Player": Player})

    def test_round_robin(self):
        scores = [0] * len(players)
        for i, w in enumerate(players):
            for j, b in enumerate(players[i + 1 :], i + 1):
                with self.subTest(f"{w.name} vs {b.name}"):
                    for _ in range(100):
                        game = Spymaster(white=w, black=b)
                        asyncio.run(game.play())
                        # game.print_score()
                        if game.white_score > game.black_score:
                            scores[i] += 1
                            scores[j] -= 1
                        elif game.black_score > game.white_score:
                            scores[i] -= 1
                            scores[j] += 1
                        else:
                            pass  # draw, no score change
                        # print("---")

        for score, player in zip(scores, players):
            print(f"{player.name} scored {score} points")

        self.assertEqual(sum(scores), 0)
