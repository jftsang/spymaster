"""Leaf-position evaluation for AI players."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from itertools import product

from spymaster import AgentCard, Position
from spymaster.spymaster import ASSASSIN, MissionCard


class Evaluator(ABC):
    """Estimate the final equity of a position from White's perspective.

    Values are expected to lie in the interval [-1, 1], where +1 is a
    sure win, 0 is a draw, and -1 is a sure loss.
    """

    @abstractmethod
    def evaluate(self, position: Position) -> float:
        """Return the estimated equity of the position for White."""
        raise NotImplementedError


class CrudeEvaluator(Evaluator):
    """A simple, deterministic evaluator based on expected random play.

    The current score difference is added to the expected scoring from
    the remaining cards and missions. Guaranteed winners are assumed to be
    played on the best remaining missions and guaranteed losers on the
    worst remaining missions; the remaining cards and missions are scored
    by random pairing. The result is normalised by the total value of the
    remaining missions and clipped to [-1, 1].
    """

    def evaluate(self, position: Position) -> float:
        missions = sorted(position.missions)
        diff = position.diff
        if not missions:
            return _outcome(diff)

        total = sum(missions)
        white, black = self._expected_scores(
            position.ours,
            position.theirs,
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
        missions = list(missions)
        if not ours or not theirs or not missions:
            return 0.0, 0.0

        white_fixed = 0.0
        black_fixed = 0.0

        if ASSASSIN not in ours and ASSASSIN not in theirs:
            our_best = max(ours)
            our_worst = min(ours)
            their_best = max(theirs)
            their_worst = min(theirs)

            our_winners = sorted(card for card in ours if card > their_best)
            their_winners = sorted(card for card in theirs if card > our_best)
            our_losers = sorted(card for card in ours if card < their_worst)
            their_losers = sorted(card for card in theirs if card < our_worst)

            desc = sorted(missions, reverse=True)
            asc = sorted(missions)

            used_missions: set[int] = set()
            used_ours: set[AgentCard] = set()
            used_theirs: set[AgentCard] = set()

            # Guaranteed winners take the best remaining missions.
            wi = 0
            for card in reversed(our_winners):
                while wi < len(desc) and desc[wi] in used_missions:
                    wi += 1
                if wi >= len(desc):
                    break
                mission = desc[wi]
                used_missions.add(mission)
                used_ours.add(card)
                white_fixed += mission
                wi += 1

            wi = 0
            for card in reversed(their_winners):
                while wi < len(desc) and desc[wi] in used_missions:
                    wi += 1
                if wi >= len(desc):
                    break
                mission = desc[wi]
                used_missions.add(mission)
                used_theirs.add(card)
                black_fixed += mission
                wi += 1

            # Guaranteed losers are spent on the worst remaining missions.
            li = 0
            for card in our_losers:
                if card in used_ours:
                    continue
                while li < len(asc) and asc[li] in used_missions:
                    li += 1
                if li >= len(asc):
                    break
                mission = asc[li]
                used_missions.add(mission)
                used_ours.add(card)
                li += 1

            li = 0
            for card in their_losers:
                if card in used_theirs:
                    continue
                while li < len(asc) and asc[li] in used_missions:
                    li += 1
                if li >= len(asc):
                    break
                mission = asc[li]
                used_missions.add(mission)
                used_theirs.add(card)
                li += 1

            ours = [card for card in ours if card not in used_ours]
            theirs = [card for card in theirs if card not in used_theirs]
            missions = [mission for mission in missions if mission not in used_missions]

        white_rand, black_rand = CrudeEvaluator._random_expected_scores(
            ours, theirs, missions
        )
        return white_fixed + white_rand, black_fixed + black_rand

    @staticmethod
    def _random_expected_scores(
        ours: list[AgentCard],
        theirs: list[AgentCard],
        missions: list[MissionCard],
    ) -> tuple[float, float]:
        if not ours or not theirs or not missions:
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


def _outcome(diff: int) -> float:
    if diff > 0:
        return 1.0
    if diff < 0:
        return -1.0
    return 0.0
