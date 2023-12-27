import unittest

from ..players import china, france, britain, america, russia
from ..spymaster import Spymaster


class TestRoundRobin(unittest.TestCase):
    def test_round_robin(self):
        players = [china, france, britain, america, russia]
        for i in players:
            for j in players:
                with self.subTest(f"{i.name} vs {j.name}"):
                    game = Spymaster(white=i, black=j)
                    game.play()
                    game.print_score()
                    print("---")
