import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect

from spymaster.players import Player
from spymaster.players.computer_players import computer_players, new_computer_player
from spymaster.players.online_player import OnlinePlayer
from spymaster.session import Forfeit, UserSession
from .spymaster import Spymaster


@dataclass
class GameSide:
    """One participant in a game: a live session or a computer."""

    name: str
    player: Player
    session: Optional[UserSession]


class ActiveGame:
    """A live game plus its two participants.

    The game engine coroutine runs as a task; it can also be ended
    early, by resolving ``end_future`` with the name of the player who
    left, or by a ``Forfeit`` bubbling out of the engine (grace
    period expiry).
    """

    def __init__(
        self, server: "GameServer", game: Spymaster, white: GameSide, black: GameSide
    ):
        self.server = server
        self.game = game
        self.white = white
        self.black = black
        self.over = False
        self.end_future: asyncio.Future = asyncio.get_running_loop().create_future()

    def sides(self):
        return (self.white, self.black)

    def opponent_name(self, name: str) -> Optional[str]:
        for side in self.sides():
            if side.name != name:
                return side.name
        return None

    def other_session(self, session: UserSession) -> Optional[UserSession]:
        for side in self.sides():
            if side.session is not session and side.session is not None:
                return side.session
        return None

    def winner_name(self) -> Optional[str]:
        if self.game.white_score > self.game.black_score:
            return self.white.name
        elif self.game.black_score > self.game.white_score:
            return self.black.name
        return None

    async def run(self) -> None:
        play_task = asyncio.create_task(self.game.play())
        done, _ = await asyncio.wait(
            {play_task, self.end_future}, return_when=asyncio.FIRST_COMPLETED
        )
        forfeiter: Optional[str] = None
        reason = "ended"
        if self.end_future in done:
            forfeiter = self.end_future.result()
            reason = "left"
            play_task.cancel()
            try:
                await play_task
            except (asyncio.CancelledError, Forfeit, Exception):
                pass
        else:
            try:
                await play_task
            except Forfeit as exc:
                forfeiter = exc.player_name
                reason = exc.reason
            except asyncio.CancelledError:
                return
            except Exception as exc:
                print("game error:", type(exc).__name__, exc)
        await self.finish(forfeiter, reason)

    async def finish(self, forfeiter: Optional[str], reason: str) -> None:
        if self.over:
            return
        self.over = True
        if forfeiter is None:
            winner = self.winner_name()
        else:
            winner = self.opponent_name(forfeiter)
        msg = {"msgType": "gameOver", "winner": winner, "reason": reason}
        print(f"game over: '{reason}' winner={winner}")
        for side in self.sides():
            session = side.session
            if session is None:
                continue
            session.in_game = False
            session.active_game = None
            session.player = None
            session.last_game_message = msg
            await session.send(msg)
        self.server.remove_game(self)
        await self.server.broadcast_players()


class GameServer:
    def __init__(self):
        self.app = FastAPI()
        self.sessions: Dict[str, UserSession] = {}
        self.games: Dict[int, ActiveGame] = {}
        self._game_id = 0

    # -- session / connection management ----------------------------------

    def get_or_create_session(self, websocket: WebSocket):
        """Return (session, cookies_to_set). A new session gets a
        session-id cookie to persist across reconnects."""
        sid = websocket.cookies.get("session")
        if sid is not None and sid in self.sessions:
            return self.sessions[sid], None
        sid = uuid4().hex
        session = UserSession(session_id=sid)
        self.sessions[sid] = session
        cookie = f"session={sid}; Path=/; HttpOnly; SameSite=Lax"
        return session, [("Set-Cookie", cookie)]

    async def serve(self, session: UserSession) -> None:
        ws = session.websocket
        try:
            while True:
                msg = await ws.receive_json()
                await self.handle(session, msg)
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            print("websocket error:", type(exc).__name__, exc)
        finally:
            await self.disconnect(session)

    async def disconnect(self, session: UserSession) -> None:
        session.detach()
        await self.cancel_pending_challenges(session)
        if session.active_game is not None and not session.active_game.over:
            await self.notify_others(session, "opponentDisconnected")
        await self.broadcast_players()

    # -- receive-loop routing ---------------------------------------------

    async def handle(self, session: UserSession, msg: Dict) -> None:
        mtype = msg.get("msgType")
        try:
            if mtype == "login":
                await self.login(session, msg.get("username"))
            elif mtype == "challenge":
                await self.challenge(session, msg.get("target"))
            elif mtype == "accept":
                await self.accept_from(session, msg.get("from"))
            elif mtype == "decline":
                await self.decline_from(session, msg.get("from"))
            elif mtype == "card":
                session.set_card(msg.get("card"))
            elif mtype == "leaveGame":
                await self.leave_game(session)
        except Exception as exc:
            print("handle error:", type(exc).__name__, exc)

    # -- lobby / matchmaking ----------------------------------------------

    async def login(self, session: UserSession, username) -> None:
        if not username or not str(username).strip():
            await session.send(
                {"msgType": "loginFailed", "reason": "Please choose a username"}
            )
            return
        username = str(username).strip()
        if session.username is not None:
            # Existing identity wins (reconnect); ignore renames.
            username = session.username
        elif any(
            other is not session and other.username == username
            for other in self.sessions.values()
        ):
            await session.send(
                {"msgType": "loginFailed", "reason": f"{username} is already in use"}
            )
            return
        session.username = username
        print("login:", username)
        await session.send({"msgType": "loginOk", "username": username})
        active = session.active_game
        if active is not None and not active.over:
            await self.notify_others(session, "opponentReconnected")
        if session.last_game_message is not None:
            await session.send(session.last_game_message)
        await self.broadcast_players()

    async def challenge(self, session: UserSession, target) -> None:
        me = session.username
        if me is None or not target:
            return
        if session.in_game or target == me:
            await session.send(
                {
                    "msgType": "challengeRefused",
                    "from": target,
                    "reason": "You cannot challenge right now",
                }
            )
            return
        if session.pending_challenge_to is not None:
            await session.send(
                {
                    "msgType": "challengeRefused",
                    "from": target,
                    "reason": "You already have a pending challenge",
                }
            )
            return
        if target in computer_players:
            # Computer players always accept.
            await self._start(session, computer_name=target)
            return
        target_session = self.find_session(target)
        if target_session is None or not target_session.connected:
            await session.send(
                {
                    "msgType": "challengeRefused",
                    "from": target,
                    "reason": f"{target} is not online",
                }
            )
            return
        if target_session.in_game:
            await session.send(
                {
                    "msgType": "challengeRefused",
                    "from": target,
                    "reason": f"{target} is already in a game",
                }
            )
            return
        if target_session.pending_challenge_from is not None:
            await session.send(
                {
                    "msgType": "challengeRefused",
                    "from": target,
                    "reason": f"{target} already has a pending challenge",
                }
            )
            return
        session.pending_challenge_to = target
        target_session.pending_challenge_from = me
        await target_session.send({"msgType": "challenge", "from": me})

    async def accept_from(self, session_b: UserSession, from_name) -> None:
        if not from_name or session_b.pending_challenge_from != from_name:
            return
        if session_b.in_game:
            return
        session_b.pending_challenge_from = None
        challenger = self.find_session(from_name)
        if challenger is None or not challenger.connected:
            return
        if challenger.pending_challenge_to == session_b.username:
            challenger.pending_challenge_to = None
        await self._start(challenger, other_session=session_b)

    async def decline_from(self, session_b: UserSession, from_name) -> None:
        if not from_name or session_b.pending_challenge_from != from_name:
            return
        session_b.pending_challenge_from = None
        challenger = self.find_session(from_name)
        if (
            challenger is not None
            and challenger.pending_challenge_to == session_b.username
        ):
            challenger.pending_challenge_to = None
            await challenger.send(
                {"msgType": "challengeDeclined", "from": session_b.username}
            )

    async def leave_game(self, session: UserSession) -> None:
        active = session.active_game
        if active is None or active.over:
            return
        if not active.end_future.done():
            active.end_future.set_result(session.username)

    # -- game setup -------------------------------------------------------

    def _make_side(self, session: Optional[UserSession], name: str) -> GameSide:
        if session is not None:
            player = OnlinePlayer(name=name, session=session)
            session.player = player
            return GameSide(name=name, player=player, session=session)
        return GameSide(name=name, player=new_computer_player(name), session=None)

    async def _start(
        self,
        session_a: UserSession,
        other_session: Optional[UserSession] = None,
        computer_name: Optional[str] = None,
    ) -> None:
        side_a = self._make_side(session_a, session_a.username)
        if computer_name is not None:
            side_b = self._make_side(None, computer_name)
        else:
            side_b = self._make_side(other_session, other_session.username)
        await self._launch(side_a, side_b)

    async def _launch(self, white: GameSide, black: GameSide) -> None:
        game = Spymaster(white=white.player, black=black.player)
        active = ActiveGame(self, game, white, black)
        self.games[self._game_id] = active
        self._game_id += 1
        for side in (white, black):
            session = side.session
            if session is None:
                continue
            session.in_game = True
            session.active_game = active
            opponent = black.name if side is white else white.name
            await session.send({"msgType": "gameStart", "opponent": opponent})
        asyncio.create_task(active.run())
        print("game started:", white.name, "vs", black.name)
        await self.broadcast_players()

    def remove_game(self, active: ActiveGame) -> None:
        for gid, game in list(self.games.items()):
            if game is active:
                del self.games[gid]
                return

    # -- helpers ----------------------------------------------------------

    def find_session(self, username: str) -> Optional[UserSession]:
        for session in self.sessions.values():
            if session.username == username:
                return session
        return None

    def online_players(self):
        players = []
        for session in self.sessions.values():
            if session.username is None:
                continue
            if session.connected or session.in_game:
                players.append(
                    {
                        "name": session.username,
                        "online": session.connected,
                        "inGame": session.in_game,
                        "isComputer": False,
                    }
                )
        for name in computer_players:
            players.append(
                {
                    "name": name,
                    "online": True,
                    "inGame": False,
                    "isComputer": True,
                }
            )
        return players

    async def broadcast_players(self) -> None:
        msg = {"msgType": "players", "players": self.online_players()}
        for session in self.sessions.values():
            if session.connected:
                await session.send(msg)

    async def notify_others(self, session: UserSession, msgType: str) -> None:
        active = session.active_game
        if active is None or active.over:
            return
        other = active.other_session(session)
        if other is not None and other.connected:
            await other.send({"msgType": msgType, "name": session.username or ""})

    async def cancel_pending_challenges(self, session: UserSession) -> None:
        if session.pending_challenge_to is not None:
            target = self.find_session(session.pending_challenge_to)
            if target is not None and target.pending_challenge_from == session.username:
                target.pending_challenge_from = None
                if target.connected:
                    await target.send(
                        {"msgType": "challengeDeclined", "from": session.username}
                    )
        if session.pending_challenge_from is not None:
            challenger = self.find_session(session.pending_challenge_from)
            if (
                challenger is not None
                and challenger.pending_challenge_to == session.username
            ):
                challenger.pending_challenge_to = None
                if challenger.connected:
                    await challenger.send(
                        {"msgType": "challengeDeclined", "from": session.username}
                    )
        session.pending_challenge_to = None
        session.pending_challenge_from = None


gs = GameServer()
app = gs.app

frontend_dir = Path(__file__).parent / "../../dist/frontend"
app.frontend("/", directory=frontend_dir)


@app.get("/")
async def index_view(request: Request):
    return FileResponse(frontend_dir / "main.html")


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    session, cookie_headers = gs.get_or_create_session(websocket)
    await websocket.accept(headers=cookie_headers)
    session.attach(websocket)
    await gs.serve(session)


@app.get("/help")
async def help_view(request: Request):
    return FileResponse(frontend_dir / "help.html")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
