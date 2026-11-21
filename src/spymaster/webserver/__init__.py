import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self
from uuid import uuid4

import numpy as np
import uvicorn
from commonmark import commonmark
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pydantic.alias_generators import to_camel
from starlette.concurrency import run_in_threadpool

from spymaster import AgentCard, MissionCard, Position, Spymaster
from spymaster.players import Player
from spymaster.players.computer_players import FACTORIES, new_computer_player
from spymaster.players.minimax.analysis import Analyser
from spymaster.players.minimax.nash_players import NASH_ANALYSER
from spymaster.tournament import TOURNAMENT_RESULTS_PATH, TournamentResults
from spymaster.webserver.online_player import OnlinePlayer
from spymaster.webserver.session import Forfeit, UserSession

logger = logging.getLogger(__name__)


class AnalysisRequest(BaseModel):
    """A game position submitted for analysis by the webserver."""

    model_config = {"populate_by_name": True, "alias_generator": to_camel}

    ours: list[AgentCard]
    theirs: list[AgentCard]
    missions: list[MissionCard]
    current_mission: MissionCard | None = None
    white_score: int = 0
    black_score: int = 0

    def to_position(self) -> Position:
        missions = set(self.missions)
        if self.current_mission is not None:
            missions.add(self.current_mission)
        return Position(
            ours=frozenset(self.ours),
            theirs=frozenset(self.theirs),
            missions=frozenset(missions),
            current_mission=self.current_mission,
            white_score=self.white_score,
            black_score=self.black_score,
        )


@dataclass
class GameSide:
    """One participant in a game: a live session or a computer."""

    name: str
    player: Player
    session: UserSession | None

    @classmethod
    def of_session(cls, session: UserSession) -> Self:
        assert session.username is not None  # user is logged in
        p = OnlinePlayer(name=session.username, session=session)
        session.player = p
        return cls(name=p.name, player=p, session=session)

    @classmethod
    def of_computer_opponent(cls, opponent_name: str) -> Self:
        p = new_computer_player(opponent_name)
        return cls(name=p.name, player=p, session=None)


class ActiveGame:
    """A live game plus its two participants.

    The game engine coroutine runs as a task; it can also be ended
    early, by resolving ``end_future`` with the name of the player who
    left, or by a ``Forfeit`` bubbling out of the engine (grace
    period expiry).
    """

    def __init__(
        self, server: GameServer, game: Spymaster, white: GameSide, black: GameSide
    ):
        self.server = server
        self.game = game
        self.white = white
        self.black = black
        self.over = False
        self.end_future: asyncio.Future = asyncio.get_running_loop().create_future()

    def sides(self):
        return (self.white, self.black)

    def opponent_name(self, name: str) -> str | None:
        for side in self.sides():
            if side.name != name:
                return side.name
        return None

    def other_session(self, session: UserSession) -> UserSession | None:
        for side in self.sides():
            if side.session is not session and side.session is not None:
                return side.session
        return None

    def winner_name(self) -> str | None:
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
        forfeiter: str | None = None
        reason = "ended"
        if self.end_future in done:
            forfeiter = self.end_future.result()
            reason = "left"
            play_task.cancel()
            try:
                await play_task
            except asyncio.CancelledError, Forfeit, Exception:  # noqa: S110, BLE001
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
                logger.exception("game error: %s", type(exc).__name__)
        await self.finish(forfeiter, reason)

    async def finish(self, forfeiter: str | None, reason: str) -> None:
        if self.over:
            return
        self.over = True

        if forfeiter is not None:
            winner = self.opponent_name(forfeiter)
        else:
            winner = self.winner_name()

        logger.info(
            "game over: %s %s - %s %s (reason=%s, winner=%s)",
            self.white.name,
            self.game.white_score,
            self.game.black_score,
            self.black.name,
            reason,
            winner,
        )
        for side in self.sides():
            session = side.session
            if session is None:
                continue
            session.in_game = False
            session.active_game = None
            session.player = None
            msg = {"msgType": "gameOver", "winner": winner, "reason": reason}
            session.last_game_message = msg
            await session.send(msg)
        self.server.remove_game(self)
        await self.server.broadcast_players()
        self.server.log("game over")


class GameServer:
    def __init__(self):
        self.app = FastAPI()
        self.sessions: dict[str, UserSession] = {}
        self.games: dict[int, ActiveGame] = {}
        self._game_id = 0
        # A single analyser is shared by every game and by the
        # analysis API so that its cached analyses are reused across games.
        self.analyser: Analyser = NASH_ANALYSER

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
        return session, [(b"Set-Cookie", cookie.encode())]

    async def serve(self, session: UserSession) -> None:
        ws = session.websocket
        assert ws is not None
        try:
            while True:
                msg = await ws.receive_json()
                await self.handle(session, msg)
        except WebSocketDisconnect:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.error("websocket error: %s: %s", type(exc).__name__, exc)
        finally:
            await self.disconnect(session)

    async def disconnect(self, session: UserSession) -> None:
        session.detach()
        who = session.username or session.session_id
        active = session.active_game
        if active is not None and not active.over:
            countdown = (
                "game will wait for reconnect"
                if session.opponent_is_computer
                else "grace period running"
            )
            logger.warning(
                "connection lost: %s dropped mid-game vs %s (%s)",
                who,
                active.opponent_name(who),
                countdown,
            )
        else:
            logger.info("connection lost: %s", who)
        await self.cancel_pending_challenges(session)
        if session.active_game is not None and not session.active_game.over:
            await self.notify_others(session, "opponentDisconnected")
        await self.broadcast_players()
        self.log("disconnect")

    # -- receive-loop routing ---------------------------------------------

    async def handle(self, session: UserSession, msg: dict) -> None:
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
            elif mtype == "cancelChallenge":
                await self.cancel_challenge(session)
            elif mtype == "card":
                session.set_card(msg.get("card"))
            elif mtype == "leaveGame":
                await self.leave_game(session)
            elif mtype == "ackGameOver":
                session.last_game_message = None
        except Exception as exc:  # noqa: BLE001
            logger.error("handle error: %s: %s", type(exc).__name__, exc)

    # -- lobby / matchmaking ----------------------------------------------

    async def login(self, session: UserSession, username) -> None:
        if not username or not str(username).strip():
            await session.send(
                {"msgType": "loginFailed", "reason": "Please choose a username"}
            )
            return
        username = str(username).strip()
        reconnect = session.username is not None
        if session.username is not None:
            # Existing identity wins (reconnect); ignore renames.
            username = session.username
        elif any(
            other is not session and other.username == username
            for other in self.sessions.values()
        ):
            logger.warning("login refused: %s is already in use", username)
            await session.send(
                {"msgType": "loginFailed", "reason": f"{username} is already in use"}
            )
            return
        session.username = username
        logger.info("login: %s%s", username, " (reconnecting)" if reconnect else "")
        await session.send({"msgType": "loginOk", "username": username})
        active = session.active_game
        if active is not None and not active.over:
            logger.info(
                "reconnect: %s rejoined game vs %s",
                username,
                active.opponent_name(username),
            )
            await self.notify_others(session, "opponentReconnected")
        if session.last_game_message is not None:
            await session.send(session.last_game_message)
        await self.broadcast_players()
        self.log("login")

    async def challenge(self, session: UserSession, target) -> None:
        me = session.username
        if me is None or not target:
            return
        if session.in_game or target == me:
            logger.info(
                "challenge refused: %s -> %s (cannot challenge right now)", me, target
            )
            await session.send(
                {
                    "msgType": "challengeRefused",
                    "from": target,
                    "reason": "You cannot challenge right now",
                }
            )
            return
        if session.pending_challenge_to is not None:
            logger.info("challenge refused: %s -> %s (already challenging)", me, target)
            await session.send(
                {
                    "msgType": "challengeRefused",
                    "from": target,
                    "reason": "You already have a pending challenge",
                }
            )
            return
        if target in FACTORIES:
            # Computer players always accept.
            logger.info("challenge: %s -> %s (computer, auto-accept)", me, target)
            await self._start(session, opponent=target)
            return
        target_session = self.find_session(target)
        if target_session is None or not target_session.connected:
            logger.info("challenge refused: %s -> %s (not online)", me, target)
            await session.send(
                {
                    "msgType": "challengeRefused",
                    "from": target,
                    "reason": f"{target} is not online",
                }
            )
            return
        if target_session.in_game:
            logger.info("challenge refused: %s -> %s (already in a game)", me, target)
            await session.send(
                {
                    "msgType": "challengeRefused",
                    "from": target,
                    "reason": f"{target} is already in a game",
                }
            )
            return
        if target_session.pending_challenge_from is not None:
            logger.info(
                "challenge refused: %s -> %s (target has a pending challenge)",
                me,
                target,
            )
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
        logger.info("challenge: %s -> %s (pending)", me, target)
        await target_session.send({"msgType": "challenge", "from": me})

    async def accept_from(self, session_b: UserSession, from_name) -> None:
        if not from_name or session_b.pending_challenge_from != from_name:
            return
        if session_b.in_game:
            return
        session_b.pending_challenge_from = None
        challenger = self.find_session(from_name)
        if challenger is None or not challenger.connected:
            logger.warning(
                "challenge accept ignored: %s is no longer online", from_name
            )
            return
        if challenger.pending_challenge_to == session_b.username:
            challenger.pending_challenge_to = None
        logger.info("challenge accepted: %s accepts %s", session_b.username, from_name)
        await self._start(challenger, opponent=session_b)

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
            logger.info(
                "challenge declined: %s declines %s", session_b.username, from_name
            )
            await challenger.send(
                {"msgType": "challengeDeclined", "from": session_b.username}
            )

    async def cancel_challenge(self, session: UserSession) -> None:
        """Withdraw a challenge this session has sent."""
        target = session.pending_challenge_to
        if target is None:
            return
        session.pending_challenge_to = None
        logger.info("challenge withdrawn: %s -> %s", session.username, target)
        target_session = self.find_session(target)
        if (
            target_session is not None
            and target_session.pending_challenge_from == session.username
        ):
            target_session.pending_challenge_from = None
            if target_session.connected:
                await target_session.send(
                    {"msgType": "challengeWithdrawn", "from": session.username}
                )

    async def leave_game(self, session: UserSession) -> None:
        active = session.active_game
        if active is None or active.over:
            return
        logger.info("leave game: %s", session.username)
        if not active.end_future.done():
            active.end_future.set_result(session.username)

    # -- game setup -------------------------------------------------------

    async def _start(
        self,
        session_a: UserSession,
        opponent : UserSession | str,
    ) -> None:
        assert session_a.username  # user is logged in
        side_a = GameSide.of_session(session_a)
        match opponent:
            case str():
                side_b = GameSide.of_computer_opponent(opponent)
            case UserSession():
                side_b = GameSide.of_session(opponent)
            case _:
                raise TypeError
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
            other = black if side is white else white
            session.opponent_is_computer = other.session is None
            await session.send(
                {
                    "msgType": "gameStart",
                    "opponent": other.name,
                    "opponentIsComputer": session.opponent_is_computer,
                }
            )
        asyncio.create_task(active.run())
        logger.info("game started: %s (white) vs %s (black)", white.name, black.name)
        await self.broadcast_players()
        self.log("game started")

    def remove_game(self, active: ActiveGame) -> None:
        for gid, game in list(self.games.items()):
            if game is active:
                del self.games[gid]
                return

    # -- helpers ----------------------------------------------------------

    def find_session(self, username: str) -> UserSession | None:
        for session in self.sessions.values():
            if session.username == username:
                return session
        return None

    def online_summary(self) -> str:
        """A short human-readable snapshot of who is around.

        For players in a game, distinguishes those still choosing a
        card from those already waiting on their opponent, and flags
        any who have dropped out of a game against another player.
        """
        entries = []
        for session in self.sessions.values():
            if session.username is None:
                continue
            if not session.connected:
                if session.in_game:
                    entries.append(f"{session.username} (disconnected, in game)")
                continue
            if session.in_game:
                status = "choosing card" if session.awaiting_card else "ready"
            else:
                status = "in lobby"
            entries.append(f"{session.username} ({status})")
        return ", ".join(entries) if entries else "nobody"

    def log(self, event: str) -> None:
        """Print an event alongside a snapshot of current connections."""
        logger.info("%s | connected: %s", event, self.online_summary())

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
        for name in FACTORIES:
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

webserver_dir = Path(__file__).parent
spymaster_dir = webserver_dir.parent
source_dir = spymaster_dir.parent
project_dir = source_dir.parent

frontend_dir = project_dir / "dist" / "frontend"
static_dir = source_dir / "frontend" / "static"
weights_dir = spymaster_dir / "weights"
help_template_path = source_dir / "frontend" / "help.html"
privacy_path = source_dir / "frontend" / "privacy.html"
how_to_play_path = project_dir / "HowToPlay.md"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.frontend("/", directory=frontend_dir)

FAVICON_LINKS = "\n".join(  # noqa: FLY002
    [
        '<link rel="icon" href="/static/icon.ico" sizes="any">',
        '<link rel="icon" type="image/png" href="/static/icon.png">',
    ]
)


def _render_page(path: Path) -> str:
    """Read a static HTML page and inject the favicon links before its title."""
    page = path.read_text(encoding="utf-8")
    return page.replace("<title>", FAVICON_LINKS + "\n<title>", 1)


@app.get("/")
async def index_view() -> HTMLResponse:
    return HTMLResponse(_render_page(frontend_dir / "main.html"))


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    session, cookie_headers = gs.get_or_create_session(websocket)
    await websocket.accept(headers=cookie_headers)
    session.attach(websocket)
    await gs.serve(session)


@app.get("/help")
async def help_view() -> HTMLResponse:
    markdown_text = how_to_play_path.read_text(encoding="utf-8")
    content = commonmark(markdown_text)
    page = _render_page(help_template_path)
    return HTMLResponse(page.replace("<!--HELP_CONTENT-->", content))


@app.get("/privacy")
async def privacy_view() -> HTMLResponse:
    return HTMLResponse(_render_page(privacy_path))


@app.get("/weights")
async def weights_view() -> HTMLResponse:
    return HTMLResponse(_render_page(frontend_dir / "weights.html"))


@app.get("/tournaments")
async def tournaments_view() -> HTMLResponse:
    return HTMLResponse(_render_page(frontend_dir / "tournaments.html"))


@app.get("/api/tournaments")
async def tournaments_data() -> dict:
    """Expose the round-robin net-score matrix as JSON."""
    if not TOURNAMENT_RESULTS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "No tournament results found. Run "
                "`python -m spymaster tournament` to generate them."
            ),
        )
    results = TournamentResults.load(TOURNAMENT_RESULTS_PATH)
    return {
        "players": results.player_names,
        "evaluators": results.evaluator_names,
        "scores": results.scores.tolist(),
    }


@app.get("/api/weights")
async def weights_data() -> dict:
    """Expose the trained single-linear-layer weight matrices as JSON so
    the weight explorer page can render them.
    """
    from spymaster.players.linear import LinearPlayer

    players = []
    for path in sorted(weights_dir.glob("*.npy")):
        matrix = np.load(path)
        if matrix.ndim != 2 or matrix.shape != (16, LinearPlayer.INPUTS_LENGTH):
            continue
        players.append(
            {
                "name": path.stem.replace("_", " ").title(),
                "file": path.name,
                "weights": matrix.tolist(),
            }
        )
    return {"inputs": LinearPlayer.INPUTS_LENGTH, "players": players}


@app.post("/analysis")
async def analysis_data(request: AnalysisRequest) -> dict:
    """Analyse a game position.

    Returns the equilibrium value from the submitted player's
    perspective, together with the equilibrium strategy for both
    players. Strategies are aligned with their corresponding card
    lists.
    """
    position = request.to_position()
    if position.current_mission is None:
        raise HTTPException(
            status_code=400,
            detail="Position has no current mission to analyse",
        )
    try:
        (our_cards, our_strategy, equity), (
            their_cards,
            their_strategy,
            _,
        ) = await asyncio.gather(
            run_in_threadpool(gs.analyser.analyse, position),
            run_in_threadpool(gs.analyser.analyse, position.flipped()),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if abs(equity) < 1e-9:
        equity = 0.0
    return {
        "equity": equity,
        "ourCards": our_cards,
        "ourStrategy": our_strategy,
        "theirCards": their_cards,
        "theirStrategy": their_strategy,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
