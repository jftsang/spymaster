from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi.websockets import WebSocket

from spymaster.logger import logger
from spymaster.players import Player

if TYPE_CHECKING:
    from spymaster.webserver import ActiveGame

GRACE_PERIOD = timedelta(minutes=5)
GRACE_REPOLL_SECONDS = 1.0


class Forfeit(Exception):
    """Raised when a player's game comes to an end through forfeiting.

    reason is one of "grace" (connection dropped for the grace period)
    or "left" (the player explicitly left the game).
    """

    def __init__(self, player_name: str, reason: str):
        super().__init__(f"{player_name} forfeited ({reason})")
        self.player_name = player_name
        self.reason = reason


class UserSession:
    """The server-side identity of one browser tab connection.

    A session survives websocket reconnects; it is the unit of the
    lobby (username, challenge state) and of gameplay (via its
    OnlinePlayer).
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.username: str | None = None
        self.websocket: WebSocket | None = None
        self.connected = False
        self.disconnected_at: datetime | None = None

        self.player: Player | None = None
        self.active_game: ActiveGame | None = None
        self.in_game = False
        self.pending_challenge_to: str | None = None
        self.pending_challenge_from: str | None = None
        self.last_game_message: dict[str, Any] | None = None

        self._send_lock = asyncio.Lock()
        self._card_future: asyncio.Future | None = None
        self.awaiting_card = False

    # -- wiring -----------------------------------------------------------

    def attach(self, ws: WebSocket) -> None:
        """Attach a (re)connected websocket to this session."""
        self.websocket = ws
        self.connected = True
        self.disconnected_at = None
        logger.debug("attached websocket to session %s", self.session_id)

    def detach(self) -> None:
        """Mark the session as disconnected. The grace period for any
        game the session is in runs from this moment."""
        self.connected = False
        self.disconnected_at = datetime.now(UTC)
        self.websocket = None
        logger.debug("detached session %s", self.session_id)

    # -- sending ----------------------------------------------------------

    async def send(self, msg: dict[str, Any]) -> None:
        """Send a JSON message. May be safely called from any task.

        Messages sent while the session is disconnected are dropped;
        important game messages are also captured separately in
        ``last_game_message`` and replayed on reconnect.
        """
        if not self.connected or self.websocket is None:
            return
        async with self._send_lock:
            await self.websocket.send_json(msg)

    # -- card picking / grace period --------------------------------------

    def set_card(self, card) -> None:
        """Deliver a card choice from the receive loop to a pending
        pick."""
        if self._card_future is not None and not self._card_future.done():
            self._card_future.set_result(card)

    def forfeit(self, reason: str) -> None:
        """Abort a pending pick (does nothing if no pick is pending)."""
        if self._card_future is not None and not self._card_future.done():
            self._card_future.set_exception(
                Forfeit(self.username or self.session_id, reason)
            )

    async def await_card(self) -> int:
        """Wait for the player to play a card.

        If the session is disconnected, poll and raise ``Forfeit`` once
        the grace period has elapsed since disconnection. A reconnect
        resets the clock (the poll re-checks ``connected``).
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._card_future = future
        self.awaiting_card = True
        try:
            while True:
                if future.done():
                    return future.result()
                if self.connected or self.disconnected_at is None:
                    step = GRACE_REPOLL_SECONDS
                else:
                    now = datetime.now(UTC)
                    remaining = (
                        self.disconnected_at + GRACE_PERIOD - now
                    ).total_seconds()
                    if remaining <= 0:
                        logger.warning(
                            "grace period expired: %s forfeits",
                            self.username or self.session_id,
                        )
                        raise Forfeit(self.username or self.session_id, "grace")
                    step = min(GRACE_REPOLL_SECONDS, remaining)
                try:
                    await asyncio.wait_for(asyncio.shield(future), timeout=step)
                except TimeoutError:
                    continue
        finally:
            self.awaiting_card = False
            if self._card_future is future:
                self._card_future = None
