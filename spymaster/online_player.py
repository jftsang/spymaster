from dataclasses import dataclass

from fastapi.websockets import WebSocket

from .players import Player
from .spymaster import MissionResult, Situation


@dataclass(kw_only=True)
class OnlinePlayer(Player):
    websocket: WebSocket

    async def pick(self, state: Situation) -> int:
        pass

    async def receive(self, result: MissionResult) -> None:
        pass
