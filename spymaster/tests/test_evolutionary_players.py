import asyncio
import unittest

from spymaster.players.evolutionary_players import SingleLayerPerceptronPlayer
from spymaster.spymaster import Spymaster


class TestSingleLayerPerceptronPlayer(unittest.TestCase):
    def test_single_layer_perceptron(self):
        white = SingleLayerPerceptronPlayer.randomized()
        black = SingleLayerPerceptronPlayer.randomized()
        game = Spymaster(white=white, black=black)
        asyncio.run(game.play())
        game.print_score()
        print("---")
