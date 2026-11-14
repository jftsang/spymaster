import unittest

from spymaster.position import Position
from spymaster.spymaster import AgentCard, MissionCard, Spymaster


class TestPosition(unittest.TestCase):
    def test_property_captures_cards_scores_and_missions(self):
        situation = Spymaster(
            white_cards=[AgentCard(10), AgentCard(2)],
            black_cards=[AgentCard(5), AgentCard(1)],
            white_score=7,
            black_score=3,
            current_mission=MissionCard(4),
            remaining_missions=[MissionCard(3), MissionCard(1)],
        )

        position = situation.position

        self.assertEqual(position.ours, frozenset({AgentCard(10), AgentCard(2)}))
        self.assertEqual(position.theirs, frozenset({AgentCard(5), AgentCard(1)}))
        self.assertEqual(
            position.missions,
            frozenset({MissionCard(4), MissionCard(3), MissionCard(1)}),
        )
        self.assertEqual(position.current_mission, MissionCard(4))
        self.assertEqual(position.white_score, 7)
        self.assertEqual(position.black_score, 3)

    def test_position_can_be_constructed_directly(self):
        situation = Spymaster(
            white_cards=[AgentCard(10)],
            black_cards=[AgentCard(5)],
            current_mission=MissionCard(4),
            remaining_missions=[],
        )

        self.assertEqual(situation.position, Position.of(situation))

    def test_property_recomputes_after_state_changes(self):
        situation = Spymaster(
            white_cards=[AgentCard(0), AgentCard(1), AgentCard(2)],
            black_cards=[AgentCard(0), AgentCard(1), AgentCard(2)],
            current_mission=MissionCard(4),
            remaining_missions=[],
        )
        before = situation.position

        situation.resolve(AgentCard(1), AgentCard(2))

        self.assertNotEqual(situation.position, before)
        self.assertEqual(
            situation.position.ours,
            frozenset({AgentCard(0), AgentCard(2)}),
        )
        self.assertEqual(
            situation.position.theirs,
            frozenset({AgentCard(0), AgentCard(1)}),
        )

    def test_position_round_trips_through_spymaster(self):
        situation = Spymaster(
            white_cards=[AgentCard(10), AgentCard(2)],
            black_cards=[AgentCard(5), AgentCard(1)],
            white_score=7,
            black_score=3,
            current_mission=MissionCard(4),
            remaining_missions=[MissionCard(3), MissionCard(1)],
        )

        self.assertEqual(situation.position.to_spymaster().position, situation.position)

    def test_position_is_hashable(self):
        self.assertIsInstance(hash(Spymaster().position), int)


if __name__ == "__main__":
    unittest.main()
