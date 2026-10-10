from typing import Optional

from spymaster.players import Player
from spymaster.session import UserSession
from spymaster.spymaster import MissionResult, Spymaster


class WsComm:
    """Message helpers for an in-game player conversation.

    All game messages are recorded as the session's
    ``last_game_message`` so a reconnecting player can resume.
    """

    def __init__(self, session: UserSession):
        self.session = session

    async def send_situation(self, state: Spymaster, message: Optional[str]):
        msg = {
            "msgType": "situation",
            "situation": state.to_dict(),
            "message": message,
        }
        self.session.last_game_message = msg
        await self.session.send(msg)

    async def send_result(self, state: Spymaster, result: MissionResult):
        msg = {
            "msgType": "result",
            "situation": state.to_dict(),
            "result": result.to_dict(),
        }
        self.session.last_game_message = msg
        await self.session.send(msg)


class OnlinePlayer(Player):
    def __init__(self, name: str, session: UserSession):
        super().__init__(name=name)
        self.session = session
        self.wscomm = WsComm(session)

    async def pick(self, state: Spymaster) -> int:
        await self.wscomm.send_situation(state, "Pick a card")
        while True:
            choice = await self.session.await_card()
            print("Choice:", choice)
            if choice in state.white_cards:
                return choice
            else:
                await self.wscomm.send_situation(state, f"{choice} is not a valid card")

    async def receive(self, state, result: MissionResult) -> None:
        await self.wscomm.send_result(state, result)
