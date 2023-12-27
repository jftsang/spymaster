import argparse
import asyncio
import typing
from dataclasses import dataclass, field
from random import shuffle
from typing import List, Set

from dataclasses_json import LetterCase, dataclass_json

if typing.TYPE_CHECKING:
    from .players import Player


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass(kw_only=True)
class Situation:
    your_cards: List[int]
    opponents_cards: List[int]
    you_score: int
    opp_score: int
    current_mission: int
    remaining_missions: Set[int]  # no order

    def __str__(self):
        s = [f"Your cards: {self.your_cards}",
             f"Opponent's cards: {self.opponents_cards}",
             f"Score: {self.you_score} - {self.opp_score}",
             f"Mission: {self.current_mission}",
             f"Remaining missions: {self.remaining_missions}"]
        return "\n".join(s)

    def flipped(self):
        return Situation(
            your_cards=self.opponents_cards,
            opponents_cards=self.your_cards,
            you_score=self.opp_score,
            opp_score=self.you_score,
            current_mission=self.current_mission,
            remaining_missions=self.remaining_missions,
        )

    @classmethod
    def for_white(cls, state: "Spymaster"):
        return cls(
            your_cards=state.white_cards,
            opponents_cards=state.black_cards,
            you_score=state.white_score,
            opp_score=state.black_score,
            current_mission=None,  # type: ignore
            remaining_missions=set(state.missions),
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
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


def card_factory() -> List[int]:
    return list(range(16))


def mission_factory() -> List[int]:
    missions = list(range(1, 17))
    shuffle(missions)
    return missions


@dataclass_json
@dataclass(kw_only=True)
class Spymaster:
    white: "Player"
    black: "Player"
    white_cards: List[int] = field(default_factory=card_factory)
    black_cards: List[int] = field(default_factory=card_factory)
    white_score: int = field(default=0)
    black_score: int = field(default=0)
    missions: List[int] = field(default_factory=mission_factory)

    def print_score(self):
        print(f"{self.white.name} (White): {self.white_score}")
        print(f"{self.black.name} (Black): {self.black_score}")

    async def play(self):
        while self.missions:
            mission = self.missions.pop()
            white_situation = Situation.for_white(self)
            white_situation.current_mission = mission
            black_situation = white_situation.flipped()

            white_play = await self.white.pick(white_situation)
            black_play = await self.black.pick(black_situation)
            result = self.resolve(white_play, black_play, mission)
            await self.white.receive(result)
            await self.black.receive(result.flipped())

    def resolve(
        self, white_play: int, black_play: int, mission: int
    ) -> MissionResult:
        """
        Resolve a mission
        @param white_play: The card that White played
        @param black_play: The card that Black played
        @param mission: The value of the mission
        @return: MissionResult from White's point of view
        """
        if white_play not in self.white_cards:
            raise ValueError("White card not in hand")

        if black_play not in self.black_cards:
            raise ValueError("Black card not in hand")

        self.white_cards.remove(white_play)
        self.black_cards.remove(black_play)

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


async def main():
    from .players import HumanPlayer, players

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "p1", choices=[p for p in players.keys()],
    )
    parser.add_argument(
        "p2", choices=[p for p in players.keys()], nargs="?"
    )
    args = parser.parse_args()
    if args.p2 is None:
        p1 = HumanPlayer("You")
        p2 = players[args.p1]
    else:
        p1 = players[args.p1]
        p2 = players[args.p2]

    game = Spymaster(white=p1, black=p2)
    await game.play()
    game.print_score()


if __name__ == "__main__":
    asyncio.run(main())
