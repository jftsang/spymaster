from pathlib import Path
from typing import Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket, WebSocketDisconnect

from .online_player import OnlinePlayer
from .players import russia
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
        player = OnlinePlayer(code, websocket=websocket)

        return player


gs = GameServer()
app = gs.app
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
    player = gs.connect_player("1234", websocket)
    game = gs.games.setdefault("1234", Spymaster(white=player, black=russia))
    await game.play()
    # situation = Situation.for_white(game)
    # situation.your_cards = [1, 5, 7, 9]
    # situation.opponents_cards = [0, 4, 7, 15]
    # await websocket.send_json(
    #     {"msgType": "situation", "situation": situation.to_dict()}  # type: ignore
    # )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
