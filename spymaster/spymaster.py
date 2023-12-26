import typing
from dataclasses import dataclass, field
from random import shuffle
from typing import List, Set

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass(kw_only=True)
class Situation:
    you: List[bool]
    opp: List[bool]
    you_score: int
    opp_score: int
    current_mission: int
    remaining_missions: Set[int]  # no order

    @property
    def your_cards(self):
        return [i for i in range(16) if self.you[i]]

    @property
    def opponents_cards(self):
        return [i for i in range(16) if self.opp[i]]

    def __str__(self):
        s = [f"Your cards: {self.your_cards}",
             f"Opponent's cards: {self.opponents_cards}",
             f"Score: {self.you_score} - {self.opp_score}",
             f"Mission: {self.current_mission}",
             f"Remaining missions: {self.remaining_missions}"]
        return "\n".join(s)

    def flipped(self):
        return Situation(
            you=self.opp,
            opp=self.you,
            you_score=self.opp_score,
            opp_score=self.you_score,
            current_mission=self.current_mission,
            remaining_missions=self.remaining_missions,
        )


@dataclass_json
@dataclass(kw_only=True)
class MissionResult:
    you_played: int
    opp_played: int
    you_scored: int
    opp_scored: int

    def __str__(self):
        s = [f"You played {self.you_played}, They played {self.opp_played}"]
        if self.you_scored:
            s.append(f"You scored {self.you_scored}")
        elif self.opp_scored:
            s.append(f"Opponent scored {self.opp_scored}")
        else:
            s.append("Drawn round")

        s.append("")
        return "\n".join(s)

    def flipped(self):
        return MissionResult(
            you_played=self.opp_played,
            opp_played=self.you_played,
            you_scored=self.opp_scored,
            opp_scored=self.you_scored,
        )


def card_factory() -> List[bool]:
    return [True] * 16


def mission_factory() -> List[int]:
    missions = list(range(1, 17))
    shuffle(missions)
    return missions


@dataclass_json
@dataclass(kw_only=True)
class Spymaster:
    white: "Player"
    black: "Player"
    white_cards: List[bool] = field(default_factory=card_factory)
    black_cards: List[bool] = field(default_factory=card_factory)
    white_score: int = field(default=0)
    black_score: int = field(default=0)
    missions: List[int] = field(default_factory=mission_factory)

    def print_score(self):
        print(f"{self.white.name} (White): {self.white_score}")
        print(f"{self.black.name} (Black): {self.black_score}")

    def play(self):
        while self.missions:
            mission = self.missions.pop()
            white_situation = Situation(
                you=self.white_cards,
                opp=self.black_cards,
                you_score=self.white_score,
                opp_score=self.black_score,
                current_mission=mission,
                remaining_missions=set(self.missions),
            )
            black_situation = white_situation.flipped()
            white_play = self.white.pick(white_situation)
            black_play = self.black.pick(black_situation)
            result = self.resolve(white_play, black_play, mission)
            self.white.receive(result)
            self.black.receive(result.flipped())

    def resolve(self, white_play: int, black_play: int, mission: int) -> MissionResult:
        """
        Resolve a mission
        @param white_play: The card that White played
        @param black_play: The card that Black played
        @param mission: The value of the mission
        @return: MissionResult from White's point of view
        """
        if not self.white_cards[white_play]:
            raise ValueError("White card not in hand")

        if not self.black_cards[black_play]:
            raise ValueError("Black card not in hand")

        self.white_cards[white_play] = False
        self.black_cards[black_play] = False

        dw = 0
        db = 0
        if white_play == black_play:
            pass
        elif white_play == 0:
            dw = black_play
        elif black_play == 0:
            db = white_play
        elif white_play > black_play:
            dw = mission
        elif white_play < black_play:
            db = mission
        else:
            raise RuntimeError

        self.white_score += dw
        self.black_score += db

        return MissionResult(
            you_played=white_play,
            opp_played=black_play,
            you_scored=dw,
            opp_scored=db,
        )


if __name__ == "__main__":
    from .players import HumanPlayer, britain, china, france, america, timothy #, russia

    game = Spymaster(white=timothy, black=timothy)
    game.play()
    game.print_score()
