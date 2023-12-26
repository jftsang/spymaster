from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import choice, randint
from typing import Optional

from dataclasses_json import dataclass_json

from .aim import aim
from .spymaster import MissionResult, Situation


@dataclass_json
@dataclass
class Player(ABC):
    name: str

    @abstractmethod
    def pick(self, state: Situation) -> int:
        pass

    def receive(self, result: MissionResult) -> None:
        """Do something with the result from a round."""
        pass


def tryint(x: str) -> Optional[int]:
    try:
        return int(x)
    except ValueError:
        return None


class HumanPlayer(Player):
    def pick(self, state: Situation) -> int:
        print(state)
        while (x := tryint(input("Choose a card: "))) not in state.your_cards:
            print(f"{x} is not a valid card")
        return x

    def receive(self, result: MissionResult) -> None:
        print(result)


class RandomPlayer(Player):
    """Naive player that just plays cards at random."""
    def pick(self, state: Situation) -> int:
        return choice(state.your_cards)


class SimpleAimingPlayer(Player):
    """Player that tries to aim for a few points above the value of each
    mission.
    """
    def __init__(self, name, variance=2):
        super().__init__(name)
        self.variance = variance

    def pick(self, state: Situation) -> int:
        target = state.current_mission + randint(1, self.variance)
        return aim(state.your_cards, target)


class AmericaPlayer(Player):
    """Player that adjusts its aim if it is defeated in a previous
    round.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diff: int = randint(0, 2)

    def pick(self, state: Situation) -> int:
        target = state.current_mission + self.diff + 1
        return aim(state.your_cards, target)

    def receive(self, result: MissionResult) -> None:
        if result.opp_played >= result.you_played:
            self.diff = result.opp_played - result.you_played


class RussiaPlayer(Player):
    def __init__(self):
        self.diff = randint(0, 2)


china = RandomPlayer("China")
france = SimpleAimingPlayer("France", 2)
britain = SimpleAimingPlayer("Britain", 4)
america = AmericaPlayer("America")
# russia = RussiaPlayer()
