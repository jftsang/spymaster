import unittest
from unittest.mock import call, patch

from spymaster import AgentCard, Spymaster
from spymaster.gene_pool import make_gene_pool
from spymaster.players import Player
from spymaster.players.benchmarks import BENCHMARK_FACTORIES


class StubPlayer(Player):
    async def pick(self, state: Spymaster) -> AgentCard:
        return AgentCard(min(state.white_cards))


def _make_pool(opponent_names):
    return make_gene_pool(
        opponent_names,
        n_players=1,
        n_games=1,
        n_replace=0,
        mutation_rate=0.0,
        seed=0,
    )


class TestMakeGenePool(unittest.TestCase):
    def test_defaults_to_benchmark_players(self):
        pool = _make_pool(None)

        self.assertEqual(
            pool.tournament.challenger_factories,
            list(BENCHMARK_FACTORIES.values()),
        )
        self.assertEqual(
            pool.reference_factories,
            list(BENCHMARK_FACTORIES.values()),
        )

    def test_uses_named_opponents(self):
        with patch(
            "spymaster.players.computer_players.new_computer_player",
            side_effect=lambda name: StubPlayer(name),
        ) as new_player:
            pool = _make_pool(["AI (Nash, 1-ply)", "AI (Adaptive)"])
            challengers = [
                factory() for factory in pool.tournament.challenger_factories
            ]

        self.assertEqual(
            new_player.call_args_list,
            [call("AI (Nash, 1-ply)"), call("AI (Adaptive)")],
        )
        self.assertEqual(
            [player.name for player in challengers],
            ["AI (Nash, 1-ply)", "AI (Adaptive)"],
        )
        self.assertEqual(
            pool.reference_factories,
            pool.tournament.challenger_factories,
        )

    def test_rejects_empty_opponent_list(self):
        with self.assertRaises(ValueError):
            _make_pool([])


if __name__ == "__main__":
    unittest.main()
