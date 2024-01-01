from dataclasses import dataclass
from typing import Optional

from fastapi.websockets import WebSocket

from .players import Player
from .spymaster import MissionResult, Spymaster


@dataclass(kw_only=True)
class OnlinePlayer(Player):
    websocket: WebSocket
    game: Spymaster

    async def pick(self, state: Spymaster) -> int:
        await self.websocket.send_json(
            {
                "msgType": "situation",
                "situation": state.to_dict()  # type: ignore
            }
        )

        accept = False
        while not accept:
            recv = await self.websocket.receive_json()
            choice: Optional[int] = recv["card"]
            print("Choice:", choice)
            accept = choice in state.white_cards

        return choice

    async def receive(self, state, result: MissionResult) -> None:
        await self.websocket.send_json(
            {
                "msgType": "result",
                "situation": state.to_dict(),  # type: ignore
                "result": result.to_dict()  # type: ignore
            }
        )

        if result.game_over:
            await self.websocket.close()
