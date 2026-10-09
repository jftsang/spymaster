from pathlib import Path
from typing import Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect

from spymaster.players.computer_players import russia
from spymaster.players.online_player import OnlinePlayer
from .spymaster import Spymaster


class GameServer:
    def __init__(self):
        self.app = FastAPI()
        self.games: Dict[str, Spymaster] = {}
        self.online_players: Dict[str, OnlinePlayer] = {}

    def connect_player(self, code: str, websocket: WebSocket) -> OnlinePlayer:
        """If the player is already connected, update her websocket.
        Otherwise create a new player.
        """
        game = Spymaster(white=None, black=russia)  # type: ignore[call-arg]
        player = OnlinePlayer(name=code, websocket=websocket, game=game)
        game.white = player
        self.games[code] = game

        return player


gs = GameServer()
app = gs.app

frontend_dir = Path(__file__).parent / "../../dist/frontend"
app.frontend("/", directory=frontend_dir)


@app.get("/")
async def index_view(request: Request):
    return FileResponse(frontend_dir / "main.html")


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    player = gs.connect_player("QWERTY", websocket)
    try:
        await player.game.play()
    except WebSocketDisconnect as exc:
        print("disconnected", exc.code, exc.reason)


@app.get("/help")
async def help_view(request: Request):
    return FileResponse(frontend_dir / "help.html")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
