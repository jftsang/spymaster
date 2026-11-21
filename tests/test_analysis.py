import unittest
from dataclasses import FrozenInstanceError

from spymaster import AgentCard
from spymaster.players.minimax.analysis import Analysis


class TestAnalysis(unittest.TestCase):
    def test_sequences_are_stored_as_tuples(self):
        cards = [AgentCard(1), AgentCard(2)]
        strategy = [0.25, 0.75]

        analysis = Analysis(cards, strategy, 0.5)

        self.assertEqual(analysis.cards, (1, 2))
        self.assertEqual(analysis.strategy, (0.25, 0.75))
        self.assertEqual(analysis.value, 0.5)
        self.assertIsInstance(analysis.cards, tuple)
        self.assertIsInstance(analysis.strategy, tuple)

    def test_is_immutable(self):
        analysis = Analysis((AgentCard(1),), (1.0,), 1.0)

        with self.assertRaises(FrozenInstanceError):
            setattr(analysis, "value", 0.0)  # noqa: B010  (test frozen dataclass)


if __name__ == "__main__":
    unittest.main()
