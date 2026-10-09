from abc import ABC, abstractmethod
from dataclasses import dataclass

from spymaster.spymaster import MissionResult, Spymaster


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


def tryint(x: str) -> int | None:
    try:
        return int(x)
    except ValueError:
        return None


class HumanPlayer(Player):
    @staticmethod
    def display_situation(situation: Spymaster):
        s = [
            f"Your cards: {situation.white_cards}",
            f"Opponent's cards: {situation.black_cards}",
            f"Score: {situation.white_score} - {situation.black_score}",
            f"Mission: {situation.current_mission}",
            f"Remaining missions: {situation.remaining_missions}",
        ]
        print("\n".join(s))

    async def pick(self, state: Spymaster) -> int:
        self.display_situation(state)
        while (x := tryint(input("Choose a card: "))) not in state.white_cards:
            print(f"{x} is not a valid card")
        return x

    async def receive(self, state, result: MissionResult) -> None:
        print(result)
        input("Press enter to continue...")
