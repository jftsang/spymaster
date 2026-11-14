import unittest

import spymaster.players  # noqa: F401  (resolves Spymaster's Player forward ref)
from spymaster import GameHistoryStep, MissionCard, Spymaster
from spymaster.spymaster import AgentCard


def history_step(mission, white_played, black_played, white_score, black_score):
    return GameHistoryStep(
        mission=MissionCard(mission),
        white_played=AgentCard(white_played),
        black_played=AgentCard(black_played),
        white_score=white_score,
        black_score=black_score,
    )


class TestFlipped(unittest.TestCase):
    def test_flipped_swaps_sides_scores_and_cards(self):
        game = Spymaster(
            white_cards=[AgentCard(1), AgentCard(2)],
            black_cards=[AgentCard(3), AgentCard(4)],
            white_score=11,
            black_score=7,
            current_mission=MissionCard(9),
        )

        flipped = game.flipped()

        self.assertEqual(flipped.white_cards, [AgentCard(3), AgentCard(4)])
        self.assertEqual(flipped.black_cards, [AgentCard(1), AgentCard(2)])
        self.assertEqual(flipped.white_score, 7)
        self.assertEqual(flipped.black_score, 11)
        self.assertEqual(flipped.current_mission, MissionCard(9))

    def test_flipped_swaps_history(self):
        original = [
            history_step(4, 1, 2, 4, 0),
            history_step(7, 5, 6, 4, 7),
        ]
        game = Spymaster(history=original)

        flipped = game.flipped()

        self.assertEqual(
            flipped.history,
            [
                history_step(4, 2, 1, 0, 4),
                history_step(7, 6, 5, 7, 4),
            ],
        )
        # The original history is left untouched.
        self.assertEqual(game.history, original)

    def test_history_serializes_camel_case(self):
        game = Spymaster()
        game.history.append(history_step(4, 1, 2, 4, 0))

        self.assertEqual(
            game.to_dict()["history"],
            [
                {
                    "mission": 4,
                    "whitePlayed": 1,
                    "blackPlayed": 2,
                    "whiteScore": 4,
                    "blackScore": 0,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
