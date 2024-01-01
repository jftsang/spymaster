from dataclasses import dataclass
from typing import Optional

from fastapi.websockets import WebSocket

from .players import Player
from .spymaster import MissionResult, Situation, Spymaster


@dataclass(kw_only=True)
class OnlinePlayer(Player):
    websocket: WebSocket
    game: Spymaster

    async def pick(self, state: Situation) -> int:
        await self.websocket.send_json(
            {
                "msgType": "situation",
                "situation": state.to_dict()
            }
        )

        accept = False
        while not accept:
            recv = await self.websocket.receive_json()
            try:
                choice: Optional[int] = recv["card"]
            except KeyError:
                continue

            print("Choice:", choice)
            accept = choice in state.your_cards

        return choice

    async def receive(self, result: MissionResult) -> None:
        await self.websocket.send_json(
            {
                "msgType": "result",
                "result": result.to_dict()
            }
        )

        if result.game_over:
            await self.websocket.close()
