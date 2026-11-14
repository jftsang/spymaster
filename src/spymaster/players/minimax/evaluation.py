"""Leaf-position evaluation for AI players."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from itertools import product

from spymaster import AgentCard, Spymaster
from spymaster.spymaster import ASSASSIN, MissionCard


class Evaluator(ABC):
    """Estimate the final equity of a position from White's perspective.

    Values are expected to lie in the interval [-1, 1], where +1 is a
    sure win, 0 is a draw, and -1 is a sure loss.
    """

    @abstractmethod
    def evaluate(self, situation: Spymaster) -> float:
        """Return the estimated equity of the situation for White."""
        raise NotImplementedError


class CrudeEvaluator(Evaluator):
    """A simple, deterministic evaluator based on expected random play.

    The current score difference is added to the expected scoring from
    randomly pairing the remaining cards for each remaining mission. The
    result is normalised by the total value of the remaining missions and
    clipped to [-1, 1].
    """

    def evaluate(self, situation: Spymaster) -> float:
        missions = _remaining_missions(situation)
        diff = situation.white_score - situation.black_score
        if not missions:
            return _outcome(diff)

        total = sum(missions)
        white, black = self._expected_scores(
            situation.white_cards,
            situation.black_cards,
            missions,
        )
        margin = diff + white - black
        return max(-1.0, min(1.0, margin / total))

    @staticmethod
    def _expected_scores(
        ours: Iterable[AgentCard],
        theirs: Iterable[AgentCard],
        missions: Iterable[MissionCard],
    ) -> tuple[float, float]:
        ours = list(ours)
        theirs = list(theirs)
        if not ours or not theirs:
            return 0.0, 0.0

        white = 0.0
        black = 0.0
        for mission, our_card, their_card in product(missions, ours, theirs):
            if our_card == their_card:
                continue
            if our_card == ASSASSIN:
                white += their_card
            elif their_card == ASSASSIN:
                black += our_card
            elif our_card > their_card:
                white += mission
            else:
                black += mission

        pairs = len(ours) * len(theirs)
        return white / pairs, black / pairs


def _remaining_missions(situation: Spymaster) -> list[MissionCard]:
    missions = set(situation.remaining_missions)
    if situation.current_mission is not None:
        missions.add(situation.current_mission)
    return sorted(missions)


def _outcome(diff: int) -> float:
    if diff > 0:
        return 1.0
    if diff < 0:
        return -1.0
    return 0.0
