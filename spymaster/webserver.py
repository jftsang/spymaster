from pathlib import Path
from typing import Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket, WebSocketDisconnect
from starlette.middleware.sessions import SessionMiddleware

from .online_player import OnlinePlayer
from .players import russia
from .spymaster import Spymaster


class GameServer:
    def __init__(self):
        self.app = FastAPI()
        self.games: Dict[str, Spymaster] = {}
        self.online_players: Dict[str, OnlinePlayer] = {}

    def connect_player(self, websocket: WebSocket) -> OnlinePlayer:
        """If the player is already connected, update her websocket.
        Otherwise create a new player.
        """
        identifier = websocket.query_params["whoami"]
        is_white = "white" in websocket.query_params

        if identifier in self.online_players:
            player = self.online_players[identifier]
            player.websocket = websocket
        else:
            player = OnlinePlayer(name=identifier, websocket=websocket, game=None)
            self.online_players[identifier] = player

            game = Spymaster(white=player if is_white else russia, black=player if not is_white else russia)
            game_code = game.white.name + game.black.name
            self.games[game_code] = game

            player.game = game

        return player


gs = GameServer()
app = gs.app
app.add_middleware(SessionMiddleware, secret_key="some-random-string", max_age=None)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static"
)


@app.get("/")
async def index_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("main.html", {"request": request})


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    player = gs.connect_player(websocket)
    try:
        await player.game.play()
    except WebSocketDisconnect as exc:
        print("disconnected", exc.code, exc.reason)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
