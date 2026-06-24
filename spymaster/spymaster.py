import typing
from dataclasses import dataclass, field
from random import shuffle
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from pydantic.alias_generators import to_camel

if typing.TYPE_CHECKING:
    from spymaster.players import Player


class MissionResult(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    you_played: int
    opp_played: int
    mission: int
    you_scored: int
    opp_scored: int
    game_over: bool = Field(default=False)

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
            mission=self.mission,
            you_scored=self.opp_scored,
            opp_scored=self.you_scored,
        )


def card_factory() -> List[int]:
    return list(range(16))


def mission_factory() -> List[int]:
    return list(range(1, 17))


def playerencoder(player: "Player") -> str:
    return player.name


@dataclass(kw_only=True)
class Spymaster:
    white: "Player"
    black: "Player"
    white_cards: List[int] = field(default_factory=card_factory)
    black_cards: List[int] = field(default_factory=card_factory)
    white_score: int = field(default=0)
    black_score: int = field(default=0)
    current_mission: int = field(default=None)  # type: ignore
    remaining_missions: List[int] = field(default_factory=mission_factory)

    def print_score(self):
        print(f"{self.white.name} (White): {self.white_score}")
        print(f"{self.black.name} (Black): {self.black_score}")

    def flipped(self):
        return Spymaster(
            white=self.black,
            black=self.white,
            white_cards=self.black_cards,
            black_cards=self.white_cards,
            white_score=self.black_score,
            black_score=self.white_score,
            current_mission=self.current_mission,
            remaining_missions=self.remaining_missions,
        )

    async def play(self):
        while self.remaining_missions:
            shuffle(self.remaining_missions)
            self.current_mission = self.remaining_missions.pop()
            self.remaining_missions.sort()

            white_play = self.choose_and_validate(self.white)
            black_play = self.flipped().choose_and_validate(self.black)
            result = self.resolve(await white_play, await black_play)

            if not self.white_cards:
                assert not self.black_cards
                result.game_over = True

            wr = self.white.receive(self, result)
            br = self.black.receive(self, result.flipped())
            await wr
            await br

    def resolve(self, white_play: int, black_play: int) -> MissionResult:
        """
        Resolve a mission. Remove the cards that were played, update the
        scores, and then emit a MissionResult from White's point of
        view.

        @param white_play: The card that White played
        @param black_play: The card that Black played
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
            dw = self.current_mission
        elif white_play < black_play:
            db = self.current_mission
        else:
            raise RuntimeError

        self.white_score += dw
        self.black_score += db

        return MissionResult(
            you_played=white_play,
            opp_played=black_play,
            mission=self.current_mission,
            you_scored=dw,
            opp_scored=db,
        )

    async def choose_and_validate(self, player: "Player") -> int:
        picked = None
        while picked not in self.white_cards:
            picked = await player.pick(self)
            if picked in self.white_cards:
                return picked
            else:
                print(f"{player.name} chose an illegal card: {picked}")
                await player.warn_illegal_choice(self, picked)

    def to_dto(self) -> GameStateDTO:
        return GameStateDTO(
            white=self.white.name,
            black=self.black.name,
            white_cards=self.white_cards,
            black_cards=self.black_cards,
            white_score=self.white_score,
            black_score=self.black_score,
            current_mission=self.current_mission,
            remaining_missions=self.remaining_missions,
        )

class GameStateDTO(BaseModel):
    white: str  # player's name
    black: str  # player's name
    white_cards: list[int] = Field(default_factory=card_factory)
    black_cards: list[int] = Field(default_factory=card_factory)
    white_score: int = Field(default=0)
    black_score: int = Field(default=0)
    current_mission: int = Field(default=None)  # type: ignore
    remaining_missions: list[int] = Field(default_factory=mission_factory)
