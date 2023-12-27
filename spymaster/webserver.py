from pathlib import Path
from typing import Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket

from .players import russia
from .spymaster import Situation, Spymaster


class GameServer:
    def __init__(self):
        self.app = FastAPI()
        self.games: Dict[str, Spymaster]


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
    game = Spymaster(white=russia, black=russia)
    situation = Situation.for_white(game)
    situation.your_cards = [1, 5, 7, 9]
    situation.opponents_cards = [0, 4, 7, 15]
    # while True:
    await websocket.send_json(
        {"msgType": "situation", "situation": situation.to_dict()}  # type: ignore
    )

        # try:
        #     message = await websocket.receive_json()
        #     print(message)
        # except Exception as e:
        #     print(e)
        #     await websocket.send_text(str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
