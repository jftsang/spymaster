from typing import cast

from spymaster import AgentCard, MissionResult, Spymaster
from spymaster.players import Player


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

    async def pick(self, state: Spymaster) -> AgentCard:
        self.display_situation(state)
        while (
            x := cast(AgentCard, tryint(input("Choose a card: ")))
        ) not in state.white_cards:
            print(f"{x} is not a valid card")
        return x

    async def receive(self, state, result: MissionResult) -> None:
        print(result)
        input("Press enter to continue...")

def tryint(x: str) -> int | None:
    try:
        return int(x)
    except ValueError:
        return None
