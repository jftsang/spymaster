from pathlib import Path
from typing import Dict

from commonmark import commonmark
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket, WebSocketDisconnect

from spymaster.players import russia
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
        # if code in self.online_players:
        #     player = self.online_players[code]
        #     player.websocket = websocket
        # else:
        player = OnlinePlayer(name=code, websocket=websocket, game=None)
        game = Spymaster(white=player, black=russia)
        player.game = game
        self.games[code] = game

        return player


gs = GameServer()
app = gs.app
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.filters["markdown"] = commonmark

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
    player = gs.connect_player("QWERTY", websocket)
    try:
        await player.game.play()
    except WebSocketDisconnect as exc:
        print("disconnected", exc.code, exc.reason)


@app.get("/help")
async def help_view(request: Request) -> HTMLResponse:
    content =    (Path(__file__).parent.parent / "HowToPlay.md").read_text()
    return templates.TemplateResponse("help.html", {"request": request, "content": content})


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
