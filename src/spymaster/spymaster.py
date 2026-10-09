import typing
from random import shuffle
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer

if typing.TYPE_CHECKING:
    from spymaster.players import Player


class MissionResult(BaseModel):
    model_config = {"populate_by_name": True, "alias_generator": None}

    you_played: int
    opp_played: int
    mission: int
    you_scored: int = 0
    opp_scored: int = 0
    game_over: bool = False

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
            game_over=self.game_over,
        )

    def model_dump(self, **kwargs):
        return super().model_dump(by_alias=True, **kwargs)

    def to_dict(self):
        return self.model_dump()


def card_factory() -> List[int]:
    return list(range(16))


def mission_factory() -> List[int]:
    return list(range(1, 17))


def playerencoder(player: "Player") -> str:
    return player.name


class Spymaster(BaseModel):
    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True, "alias_generator": None}

    white: Optional["Player"] = None
    black: Optional["Player"] = None
    white_cards: List[int] = Field(default_factory=card_factory)
    black_cards: List[int] = Field(default_factory=card_factory)
    white_score: int = 0
    black_score: int = 0
    current_mission: Optional[int] = None
    remaining_missions: List[int] = Field(default_factory=mission_factory)

    @field_serializer("white", "black")
    def serialize_players(self, player: Optional["Player"], _info):
        return player.name if player is not None else None

    def model_dump(self, **kwargs):
        return super().model_dump(by_alias=True, **kwargs)

    def to_dict(self):
        return self.model_dump()

    def print_score(self):
        assert self.white is not None and self.black is not None
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
        assert self.white is not None and self.black is not None
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

    def resolve(self, white_play: int, black_play: int) -> "MissionResult":
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
        elif white_play > black_play and self.current_mission is not None:
            dw = self.current_mission
        elif white_play < black_play and self.current_mission is not None:
            db = self.current_mission
        else:
            raise RuntimeError

        self.white_score += dw
        self.black_score += db

        return MissionResult(
            you_played=white_play,
            opp_played=black_play,
            mission=self.current_mission if self.current_mission is not None else 0,
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
        raise RuntimeError("Unreachable")
