from dataclasses import dataclass
from typing import Optional

from fastapi.websockets import WebSocket

from spymaster.players import Player
from spymaster.spymaster import MissionResult, Spymaster


class WsComm:
    def __init__(self, ws: WebSocket):
        self.ws = ws

    async def send_situation(self, state: Spymaster, message: Optional[str]):
        await self.ws.send_json(
            {
                "msgType": "situation",
                "situation": state.to_dict(),  # type: ignore
                "message": message,
            }
        )

    async def receive_choice(self) -> Optional[int]:
        recv = await self.ws.receive_json()
        return recv.get("card")

    async def send_result(self, state: Spymaster, result: MissionResult):
        await self.ws.send_json(
            {
                "msgType": "result",
                "situation": state.to_dict(),  # type: ignore
                "result": result.to_dict()  # type: ignore
            }
        )


@dataclass(kw_only=True)
class OnlinePlayer(Player):
    websocket: WebSocket
    game: Spymaster

    def __post_init__(self):
        self.wscomm = WsComm(self.websocket)

    async def pick(self, state: Spymaster) -> int:
        await self.wscomm.send_situation(state, "Pick a card")
        choice = None
        while True:
            choice = await self.wscomm.receive_choice()
            print("Choice:", choice)
            if choice in state.white_cards:
                return choice
            else:
                await self.wscomm.send_situation(state, f"{choice} is not a valid card")

    async def receive(self, state, result: MissionResult) -> None:
        await self.wscomm.send_result(state, result)
        if result.game_over:
            await self.websocket.close()
