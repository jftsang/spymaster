import asyncio
import unittest

from spymaster.players.evolutionary_players import LinearPlayer
from spymaster.spymaster import Spymaster
from spymaster.players import Player


class TestSingleLayerPerceptronPlayer(unittest.TestCase):
    def setUp(self):
        Spymaster.model_rebuild(_types_namespace={'Player': Player})

    def test_single_layer_perceptron(self):
        white = LinearPlayer.randomized()
        black = LinearPlayer.randomized()
        game = Spymaster(white=white, black=black)
        asyncio.run(game.play())
        game.print_score()
        print("---")
