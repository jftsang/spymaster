from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from random import choice, randint, random
from typing import Optional

from spymaster.spymaster import MissionResult, Spymaster
from .aim import aim, chuck, mx, prefer


@dataclass
class Player(ABC):
    name: str

    @abstractmethod
    async def pick(self, state: Spymaster) -> int:
        pass

    async def receive(self, state: Spymaster, result: MissionResult) -> None:
        """Do something with the result from a round."""
        pass

    async def warn_illegal_choice(self, situation: Spymaster, picked):
        """Warn the player that she picked an illegal card. For AI
        players this should raise an exception; for online players it
        should display a warning message.
        """
        raise ValueError("Illegal choice")


def tryint(x: str) -> Optional[int]:
    try:
        return int(x)
    except ValueError:
        return None


class HumanPlayer(Player):
    @staticmethod
    def display_situation(situation: Spymaster):
        s = [f"Your cards: {situation.white_cards}",
             f"Opponent's cards: {situation.black_cards}",
             f"Score: {situation.white_score} - {situation.black_score}",
             f"Mission: {situation.current_mission}",
             f"Remaining missions: {situation.remaining_missions}"]
        print("\n".join(s))

    async def pick(self, state: Spymaster) -> int:
        self.display_situation(state)
        while (x := tryint(input("Choose a card: "))) not in state.white_cards:
            print(f"{x} is not a valid card")
        return x

    async def receive(self, state, result: MissionResult) -> None:
        print(result)
        input("Press enter to continue...")


class RandomPlayer(Player):
    """Naive player that just plays cards at random."""
    async def pick(self, state: Spymaster) -> int:
        return choice(state.white_cards)


class SimpleAimingPlayer(Player):
    """Player that tries to aim for a few points above the value of each
    mission.
    """
    def __init__(self, name, variance=2):
        super().__init__(name)
        self.variance = variance

    async def pick(self, state: Spymaster) -> int:
        target = state.current_mission + randint(1, self.variance)
        return aim(state.white_cards, target)


@dataclass
class AmericaPlayer(Player):
    """Player that adjusts its aim if it is defeated in a previous
    round.
    """
    def __post_init__(self):
        self.diff: int = randint(0, 2)

    async def pick(self, state: Spymaster) -> int:
        target = state.current_mission + self.diff + 1
        return aim(state.white_cards, target)

    async def receive(self, state, result: MissionResult) -> None:
        if result.opp_played >= result.you_played:
            self.diff = result.opp_played - result.you_played


def check(probability: float) -> bool:
    return random() < probability


@dataclass
class RussiaPlayer(Player):
    stabbiness: float = field(default=0.5)
    paranoia: float = field(default=0.5)
    idleness: float = field(default=0.33)

    def __post_init__(self):
        self.diff = randint(0, 2)

    async def pick(self, state: Spymaster) -> int:
        # This is broken in the original game (as of 2023-12-27); the
        # Russia AI calculates its options and then throws it away, and
        # just does the America AI's action instead!
        p = state.current_mission
        mine = state.white_cards
        theirs = state.black_cards

        def _mx(l, h):
            return mx(mine, theirs, l, h)

        def _aim(t):
            return aim(mine, t)

        if p < 5:
            # Try to win in the range if we can, otherwise discard
            return prefer(_mx(p, p + 4), chuck(mine))
        elif p < 9:
            # Try to win in the range if we can, otherwise aim just above
            return prefer(_mx(p, p + 3), _aim(randint(p + 1, p + 3)))
        elif p < 13:
            # If the assassin is available, play it with 50% chance
            return prefer(
                _mx(p, p + 2),
                0 if (0 in mine and check(self.stabbiness)) else None,
                _aim(randint(p + 1, p + 2)),
            )
        else:
            # For really high value missions, follow a similar strategy...
            e = prefer(
                _mx(13, 15),
                0 if (0 in mine and check(self.stabbiness)) else None,
                _aim(randint(p, 16))
            )
            # ...but if we are about to play a high-value card, then...

            if e > 13:
                paranoid = 0 in theirs and check(self.paranoia)
                if paranoid:
                    e = chuck(mine)

            if e > 13 and check(self.idleness):
                e = _aim(randint(5, 7))

            return e


china = RandomPlayer("China")
france = SimpleAimingPlayer("France", 2)
britain = SimpleAimingPlayer("Britain", 4)
america = AmericaPlayer("America")
russia = RussiaPlayer("Russia", stabbiness=0.5, paranoia=0.5, idleness=0.33)

players = {p.name: p for p in [russia, america, britain, france, china]}
