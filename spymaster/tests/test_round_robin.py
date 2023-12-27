import asyncio
import unittest

from ..players import players
from ..spymaster import Spymaster

players = players.values()


class TestRoundRobin(unittest.TestCase):
    def test_round_robin(self):
        for i in players:
            for j in players:
                with self.subTest(f"{i.name} vs {j.name}"):
                    game = Spymaster(white=i, black=j)
                    asyncio.run(game.play())
                    game.print_score()
                    print("---")
