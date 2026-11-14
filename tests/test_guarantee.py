import unittest

from spymaster.players.minimax.guarantee import GuaranteeKind, analyse_guarantee
from spymaster.spymaster import AgentCard, MissionCard, Spymaster


class TestGuaranteeAnalysis(unittest.TestCase):
    def test_win(self):
        situation = Spymaster(
            white_cards=[AgentCard(10), AgentCard(2), AgentCard(1)],
            black_cards=[AgentCard(5), AgentCard(4), AgentCard(3)],
            white_score=1,
            black_score=0,
            current_mission=MissionCard(3),
            remaining_missions=[MissionCard(1), MissionCard(2)],
        )

        guarantee = analyse_guarantee(situation)

        self.assertEqual(guarantee.kind, GuaranteeKind.WIN)
        self.assertEqual(guarantee.equity, 1)
        self.assertEqual(guarantee.win_threshold, 1)
        self.assertEqual(guarantee.draw_threshold, 1)
        self.assertEqual(guarantee.guaranteed_winners, (10,))
        self.assertEqual(guarantee.required_missions, (3,))

    def test_draw_only(self):
        situation = Spymaster(
            white_cards=[AgentCard(15), AgentCard(14)],
            black_cards=[AgentCard(2), AgentCard(1)],
            black_score=3,
            current_mission=MissionCard(2),
            remaining_missions=[MissionCard(1)],
        )

        guarantee = analyse_guarantee(situation)

        self.assertEqual(guarantee.kind, GuaranteeKind.DRAW_ONLY)
        self.assertEqual(guarantee.equity, 0)
        self.assertIsNone(guarantee.win_threshold)
        self.assertEqual(guarantee.draw_threshold, 2)
        self.assertEqual(guarantee.guaranteed_winners, (14, 15))
        self.assertEqual(guarantee.required_missions, (2, 1))

    def test_unsecurable_draw_only(self):
        situation = Spymaster(
            white_cards=[AgentCard(15), AgentCard(1)],
            black_cards=[AgentCard(14), AgentCard(2)],
            black_score=3,
            current_mission=MissionCard(2),
            remaining_missions=[MissionCard(1)],
        )

        guarantee = analyse_guarantee(situation)

        self.assertEqual(guarantee.kind, GuaranteeKind.DRAW_ONLY)
        self.assertIsNone(guarantee.equity)
        self.assertEqual(guarantee.draw_threshold, 2)
        self.assertEqual(guarantee.guaranteed_winners, (15,))
        self.assertEqual(guarantee.required_missions, (2, 1))

    def test_defensive_draw(self):
        situation = Spymaster(
            white_cards=[AgentCard(10), AgentCard(2), AgentCard(1)],
            black_cards=[AgentCard(5), AgentCard(4), AgentCard(3)],
            current_mission=MissionCard(5),
            remaining_missions=[MissionCard(3), MissionCard(2)],
        )

        guarantee = analyse_guarantee(situation)

        self.assertEqual(guarantee.kind, GuaranteeKind.DEFENSIVE_DRAW)
        self.assertIsNone(guarantee.equity)
        self.assertEqual(guarantee.win_threshold, 2)
        self.assertEqual(guarantee.draw_threshold, 1)
        self.assertEqual(guarantee.guaranteed_winners, (10,))
        self.assertEqual(guarantee.required_missions, (5,))

    def test_loss(self):
        situation = Spymaster(
            white_cards=[AgentCard(15), AgentCard(1)],
            black_cards=[AgentCard(14), AgentCard(2)],
            black_score=5,
            current_mission=MissionCard(2),
            remaining_missions=[MissionCard(1)],
        )

        guarantee = analyse_guarantee(situation)

        self.assertEqual(guarantee.kind, GuaranteeKind.LOSS)
        self.assertEqual(guarantee.equity, -1)

    def test_loss_takes_precedence_over_assassin(self):
        situation = Spymaster(
            white_cards=[AgentCard(0), AgentCard(1)],
            black_cards=[AgentCard(15), AgentCard(14)],
            black_score=5,
            current_mission=MissionCard(2),
            remaining_missions=[MissionCard(1)],
        )

        guarantee = analyse_guarantee(situation)

        self.assertEqual(guarantee.kind, GuaranteeKind.LOSS)

    def test_assassin_disables_analysis(self):
        guarantee = analyse_guarantee(Spymaster())

        self.assertEqual(guarantee.kind, GuaranteeKind.NONE)
        self.assertIsNone(guarantee.equity)

    def test_no_guarantee(self):
        situation = Spymaster(
            white_cards=[AgentCard(3), AgentCard(2), AgentCard(1)],
            black_cards=[AgentCard(6), AgentCard(5), AgentCard(4)],
            current_mission=MissionCard(5),
            remaining_missions=[MissionCard(3), MissionCard(2)],
        )

        guarantee = analyse_guarantee(situation)

        self.assertEqual(guarantee.kind, GuaranteeKind.NONE)
        self.assertEqual(guarantee.win_threshold, 2)
        self.assertEqual(guarantee.draw_threshold, 1)
        self.assertEqual(guarantee.guaranteed_winners, ())
        self.assertEqual(guarantee.required_missions, ())

    def test_no_missions(self):
        guarantee = analyse_guarantee(Spymaster(remaining_missions=[]))

        self.assertEqual(guarantee.kind, GuaranteeKind.NONE)


if __name__ == "__main__":
    unittest.main()
