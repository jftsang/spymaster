# Live matchmaking and lobby

Add a matchmaking lobby on top of the existing game engine, all over
websockets. Connecting users pick a username, see all online players
(including the five computer players), and challenge each other to
games.

## Decisions

- The frontend becomes the first of "many views". Multiple game views
  will eventually exist, so it should be structured ready for that.
- Use **Preact + @preact/signals** for the frontend (component
  composition is important for the coming multi-view app).
- One fresh AI player instance per game, so many players can all play
  against the AIs at once.
- A user who is in a game is shown as "In game" and cannot be
  challenged.
- A login with a username already in use is rejected (socket stays
  open so the user can pick another name).
- Game end does NOT auto-return to the lobby: the user stays on the
  final board so they can look at the final score/round. A "Back to
  lobby" button returns them and the socket stays open. No round log
  yet (no data model for it).
- Leaving a game is explicit (a "Leave game" button with a
  confirmation dialog), which forfeits immediately.
- A dropped connection gives **5 minutes of grace** before forfeiting.
  The connection carries its session id as a cookie.
- No user registration and no score persistence.

### Session cookie

The session id is read from the `session` cookie in the websocket
handshake. If absent, a new id is generated and set via
`Set-Cookie` on `websocket.accept()` (Starlette supports headers on
accept). The browser resends the cookie automatically on reconnect.

## Message contract

Client -> server:

| message     | payload                 | meaning                         |
| ----------- | ----------------------- | ------------------------------- |
| `login`     | `{username}`            | identify / re-identify session  |
| `challenge` | `{target}`              | challenge another player        |
| `accept`    | `{from}`                | accept the pending challenge    |
| `decline`   | `{from}`                | decline the pending challenge   |
| `card`      | `{card}`                | play a card (in game)           |
| `leaveGame` | -                       | forfeit immediately (confirm)   |

Server -> client:

| message               | payload                                                |
| --------------------- | ------------------------------------------------------ |
| `loginOk`             | `{username}`                                           |
| `loginFailed`         | `{reason}`                                             |
| `players`             | `{players: [{name, online, inGame, isComputer}]}`      |
| `challenge`           | `{from}` (to the target)                               |
| `challengeDeclined`   | `{from}` (to the challenger)                           |
| `challengeRefused`    | `{from, reason}` (to the challenger)                   |
| `gameStart`           | `{opponent}` (to both players)                         |
| `situation`           | `{situation, message}` (existing shape)                |
| `result`              | `{situation, result}` (existing shape)                 |
| `gameOver`            | `{winner, reason}` (`ended`/`forfeit`/`left`)          |
| `opponentDisconnected`| `{name}`                                              |
| `opponentReconnected` | `{name}`                                              |

The server normalises each player's perspective: in both players'
`situation`, their own hand is `whiteCards`/`whiteScore` and the
opponent is the `black` name. (This is how the existing game works via
`Spymaster.flipped()`.)

## Backend

### `src/spymaster/players/computer_players.py`

Add `new_computer_player(name) -> Player`, a factory producing a
**fresh** instance per name (China RandomPlayer, France/Britain
SimpleAimingPlayer, America AmericaPlayer, Russia RussiaPlayer with
the existing parameters). Keep the module-level singletons for the CLI
and tests.

### New `src/spymaster/session.py` — `UserSession`

One per session id. Fields:

- `session_id`, `username`, `websocket` (mutable), `connected`,
  `disconnected_at`, `active_game` ref, `in_game`,
  `pending_challenge_to` / `pending_challenge_from`,
  `last_game_message` (replayed on reconnect).
- `send(msg)` — no-op when disconnected (message captured separately
  for replay); locked to keep concurrent Starlette sends safe.
- `attach(ws)` — link a (re)connected socket, reset `disconnected_at`.
- `detach()` — mark disconnected, stamp `disconnected_at`.
- `set_card(card)` — resolve the pending pick future.
- `forfeit(reason)` — set an exception on the pending pick future.
- `await_card()` — await the pick future; while the session is
  disconnected, poll (sub-second) and raise `Forfeit` once 5 minutes
  has elapsed since `disconnected_at`. Reconnection resets the clock
  (the poll re-checks `connected`).

`Forfeit(Exception)` carries `player_name` and `reason`
(`grace`/`left`).

### `src/spymaster/players/online_player.py`

- `OnlinePlayer` is now bound to a `UserSession` instead of a raw
  websocket.
- `pick()` — sends the situation via `session.send` (also stored as
  `last_game_message`), then `await session.await_card()`, validating
  in a loop (illegal cards re-send the situation + a warning).
- `receive()` — sends the result; **no longer closes the socket**
  (game end is handled by the game runner).

### `src/spymaster/webserver.py` — `GameServer`

- Registries: `sessions: dict[session_id, UserSession]`, active
  games, pending challenges. The five AI names are always-present
  lobby entries.
- `/ws` handler: read/create the session cookie, `accept(headers=...)`
  to set it, attach, then the **single receive loop**
  `recv_json -> handle(session, msg)`. On disconnect: `detach()`,
  cancel pending challenges involving the session, notify the game
  mate (`opponentDisconnected`), broadcast players.
- `handle()` routes: `login` (duplicate username -> `loginFailed`; on
  reconnect send `loginOk`, replay `last_game_message`,
  `opponentReconnected` to mate), `challenge` (validate: not self,
  not in game, target online, one pending challenge per target; AI
  targets auto-accept), `accept`/`decline`, `card` ->
  `session.set_card`, `leaveGame` -> `session.forfeit("left")` and
  signal the game runner.
- `start_game(a, b)`: fresh AI instance if a side is a computer;
  build `Spymaster`; send `gameStart` to both; set `in_game`;
  `asyncio.create_task(run_game(...))`.
- `run_game`: `await game.play()`, catching `Forfeit`; on any end
  compute the winner (score comparison, or the opponent of a
  forfeiter) and send `gameOver {winner, reason}` to both; clear
  `in_game`/refs, remove the game, broadcast players. **Sockets stay
  open.**
- `broadcast_players()` to all connected sessions.
- Other AI-vs-user plumbing: leave/grace expiry handled via `Forfeit`
  propagating out of `game.play()`.

## Frontend (Preact)

### Tooling

- `npm install preact @preact/signals`.
- `tsconfig.json`: `"jsx": "react-jsx"`, `"jsxImportSource": "preact"`.
- `main.html` becomes a mount point: Bootstrap + `spymaster.css` +
  `<div id="app">` + `<script type="module" src="static/index.tsx">`.
- The old `static/spymaster.ts` is replaced.

### Files

```
src/frontend/static/index.tsx           entry: render(<App/>, #app), connect ws
src/frontend/static/state.ts            signals + types + small helpers
src/frontend/static/ws.ts               connect / auto-reconnect / JSON send
src/frontend/static/messages.ts         ws message -> signal dispatcher
src/frontend/static/components/
  App.tsx               view switch (lobby / game) + overlays + how-to link
  Lobby.tsx             LoginForm, PlayerList, PlayerRow, Toast
  ChallengeModal.tsx    incoming challenge accept/decline
  Game.tsx              header (opponent, Leave-game confirm, status banner) + board wiring
  Board.tsx             Side, MissionTray, ResultRow, NextMissionButton
  GameOverOverlay.tsx   winner + final score + Back to lobby
  ReconnectOverlay.tsx  shown while ws down
```

### State (signals)

```
username (from localStorage)            view: "lobby" | "game"
players: PlayerInfo[]                   pendingChallengeTo
incomingChallenge                       toast
wsConnected                             game: { opponent, situation,
                                            result, over, opponentStatus } | null
```

Ephemeral interaction (which card is selected, whether the
Next-Mission gate is open) is component-local `useState`; server game
state lives in the `game` signal so any `situation`/`result`/
`gameOver` message fully re-renders — which is what makes a mid-game
reconnect resume correctly.

### Behaviour notes

- Login: username persisted in `localStorage`, auto-sent on load;
  `loginFailed` clears it and re-prompts with the error inline.
- Player rows: name + badge (`Computer` / `In game`); Challenge button
  hidden for self, disabled for in-game players, "Challenging…" while
  pending.
- Challenge modal: single modal, one pending challenge per target.
- Game view: reuse the existing board logic (16 agent cards, mission
  tray, score columns, result row, Next Mission / Start Game gate).
  Card click sends `{card}`. Opponent name from `situation.black`.
  Leave game -> `window.confirm` -> `leaveGame`.
- Game over overlay: winner + final score from final board state; no
  round log. "Back to lobby" switches the view only — the socket stays
  open and the `players` list is already refreshed.
- Reconnect overlay while `!wsConnected`; `ws.ts` reconnects with
  exponential backoff (500ms -> 5s cap); cookie flows automatically.
- Opponent disconnect banner in the game view ("lost connection — 5
  minute grace") cleared on reconnect / game over.

## Verification

- `npm run typecheck` and `npm run build` (serves `dist/frontend`).
- `python -m spymaster.webserver`, `pytest` (game engine untouched).
- Manual: two-browser challenge; challenge an AI; duplicate username
  rejection; mid-game disconnect + reconnect within grace; forfeit
  after grace (verify with temporarily shortened grace, then restore);
  explicit Leave-game; game end -> overlay -> Back to lobby.