import asyncio
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

import spymaster.webserver.session as session_module
from spymaster.players.computer_players import FACTORIES
from spymaster.players.minimax.nash_players import ADAPTIVE_ANALYSER
from spymaster.tournament import TournamentResults
from spymaster.webserver import GameServer, app, gs

AI = next(iter(FACTORIES))


class FakeWebSocket:
    def __init__(self, cookies=None):
        self.cookies = cookies or {}
        self.sent = []

    async def send_json(self, msg):
        self.sent.append(msg)

    async def receive_json(self):
        raise RuntimeError("receive_json is not used in these tests")


def last(sent, mtype):
    for msg in reversed(sent):
        if msg.get("msgType") == mtype:
            return msg
    return None


class TestGameServer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.gs = GameServer()

    async def make_user(self, username):
        ws = FakeWebSocket()
        session, _ = self.gs.get_or_create_session(ws)  # ty: ignore[invalid-argument-type]
        session.attach(ws)
        await self.gs.login(session, username)
        return session, ws

    async def drive(self, session, ws, timeout=20):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while last(ws.sent, "gameOver") is None:
            if loop.time() > deadline:
                self.fail("game did not finish in time")
            fut = session._card_future
            if fut is not None and not fut.done():
                situation = last(ws.sent, "situation")
                if situation is not None:
                    session.set_card(situation["situation"]["whiteCards"][0])
            await asyncio.sleep(0.005)
        await asyncio.sleep(0.05)

    async def test_duplicate_username_rejected(self):
        _, a = await self.make_user("Alice")  # noqa: RUF059
        b = FakeWebSocket()
        session_b, _ = self.gs.get_or_create_session(b)  # ty: ignore[invalid-argument-type]
        session_b.attach(b)
        await self.gs.login(session_b, "Alice")
        failed = last(b.sent, "loginFailed")
        self.assertIsNotNone(failed)
        self.assertIn("already in use", failed["reason"])

    async def test_blank_username_rejected(self):
        ws = FakeWebSocket()
        session, _ = self.gs.get_or_create_session(ws)  # ty: ignore[invalid-argument-type]
        session.attach(ws)
        await self.gs.login(session, "   ")
        self.assertIsNotNone(last(ws.sent, "loginFailed"))

    async def test_cookie_reuses_session(self):
        ws = FakeWebSocket()
        first, cookies = self.gs.get_or_create_session(ws)  # ty: ignore[invalid-argument-type]
        self.assertIsNotNone(cookies)
        self.assertEqual(cookies[0][0], b"Set-Cookie")

        ws2 = FakeWebSocket(cookies={"session": first.session_id})
        second, cookies2 = self.gs.get_or_create_session(ws2)  # ty: ignore[invalid-argument-type]
        self.assertIs(first, second)
        self.assertIsNone(cookies2)

    async def test_play_against_ai(self):
        session, ws = await self.make_user("Alice")
        await self.gs.challenge(session, AI)
        start = last(ws.sent, "gameStart")
        self.assertIsNotNone(start)
        self.assertTrue(start["opponentIsComputer"])
        self.assertTrue(any(p["name"] == AI for p in self.gs.online_players()))

        await self.drive(session, ws)
        over = last(ws.sent, "gameOver")
        self.assertIsNotNone(over)
        self.assertEqual(over["reason"], "ended")
        self.assertFalse(session.in_game)

    async def test_ai_game_waits_while_disconnected(self):
        with (
            patch.object(session_module, "GRACE_PERIOD", timedelta(seconds=0.2)),
            patch.object(session_module, "GRACE_REPOLL_SECONDS", 0.02),
        ):
            session, ws = await self.make_user("Alice")
            await self.gs.challenge(session, AI)
            self.assertTrue(last(ws.sent, "gameStart")["opponentIsComputer"])

            loop = asyncio.get_running_loop()
            deadline = loop.time() + 5
            while not session.awaiting_card:
                self.assertLess(loop.time(), deadline, "no card was requested")
                await asyncio.sleep(0.005)

            await self.gs.disconnect(session)
            await asyncio.sleep(0.5)  # longer than the grace period
            self.assertTrue(session.in_game)
            self.assertIsNone(last(ws.sent, "gameOver"))

            ws2 = FakeWebSocket()
            session.attach(ws2)
            await self.gs.login(session, "Alice")
            self.assertTrue(session.in_game)
            await self.drive(session, ws2)
            over = last(ws2.sent, "gameOver")
            self.assertIsNotNone(over)
            self.assertEqual(over["reason"], "ended")

    async def test_busy_player_challenge_refused(self):
        alice, aws = await self.make_user("Alice")
        await self.gs.challenge(alice, AI)
        self.assertTrue(alice.in_game)

        carol, cws = await self.make_user("Carol")
        await self.gs.challenge(carol, "Alice")
        refused = last(cws.sent, "challengeRefused")
        self.assertIsNotNone(refused)
        self.assertIn("game", refused["reason"].lower())

        await self.drive(alice, aws)

    async def test_explicit_leave(self):
        session, ws = await self.make_user("Alice")
        await self.gs.challenge(session, AI)
        await self.gs.leave_game(session)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + 5
        while last(ws.sent, "gameOver") is None:
            self.assertLess(loop.time(), deadline, "leave did not end the game")
            await asyncio.sleep(0.005)
        over = last(ws.sent, "gameOver")
        self.assertEqual(over["reason"], "left")
        self.assertEqual(over["winner"], AI)

    async def test_human_vs_human(self):
        alice, aws = await self.make_user("Alice")
        bob, bws = await self.make_user("Bob")

        await self.gs.challenge(alice, "Bob")
        invite = last(bws.sent, "challenge")
        self.assertEqual(invite["from"], "Alice")

        await self.gs.accept_from(bob, "Alice")
        self.assertEqual(last(aws.sent, "gameStart")["opponent"], "Bob")
        self.assertEqual(last(bws.sent, "gameStart")["opponent"], "Alice")
        self.assertFalse(last(aws.sent, "gameStart")["opponentIsComputer"])
        self.assertFalse(last(bws.sent, "gameStart")["opponentIsComputer"])

        await asyncio.gather(
            self.drive(alice, aws),
            self.drive(bob, bws),
        )
        a_over = last(aws.sent, "gameOver")
        b_over = last(bws.sent, "gameOver")
        self.assertEqual(a_over["winner"], b_over["winner"])

    async def test_human_game_forfeits_after_grace(self):
        with (
            patch.object(session_module, "GRACE_PERIOD", timedelta(seconds=0.2)),
            patch.object(session_module, "GRACE_REPOLL_SECONDS", 0.02),
        ):
            alice, _ = await self.make_user("Alice")
            bob, bws = await self.make_user("Bob")
            await self.gs.challenge(alice, "Bob")
            await self.gs.accept_from(bob, "Alice")

            loop = asyncio.get_running_loop()
            deadline = loop.time() + 5
            while not alice.awaiting_card:
                self.assertLess(loop.time(), deadline, "no card was requested")
                await asyncio.sleep(0.005)

            await self.gs.disconnect(alice)
            await asyncio.sleep(0.5)  # longer than the grace period
            over = last(bws.sent, "gameOver")
            self.assertIsNotNone(over)
            self.assertEqual(over["reason"], "grace")
            self.assertEqual(over["winner"], "Bob")
            self.assertFalse(alice.in_game)
            self.assertFalse(bob.in_game)

    async def test_black_player_sees_flipped_state(self):
        alice, aws = await self.make_user("Alice")
        bob, bws = await self.make_user("Bob")

        await self.gs.challenge(alice, "Bob")
        await self.gs.accept_from(bob, "Alice")

        await asyncio.gather(
            self.drive(alice, aws),
            self.drive(bob, bws),
        )

        # Alice sits in the white seat, Bob in the black seat. Each must
        # see the board from their own point of view, especially the
        # final state shown when the game ends.
        a_final = last(aws.sent, "result")["situation"]
        b_final = last(bws.sent, "result")["situation"]
        self.assertEqual(a_final["white"], "Alice")
        self.assertEqual(a_final["black"], "Bob")
        self.assertEqual(b_final["white"], "Bob")
        self.assertEqual(b_final["black"], "Alice")
        self.assertEqual(b_final["whiteScore"], a_final["blackScore"])
        self.assertEqual(b_final["blackScore"], a_final["whiteScore"])
        self.assertEqual(b_final["whiteCards"], a_final["blackCards"])
        self.assertEqual(b_final["blackCards"], a_final["whiteCards"])

        # The history must also be complete and mirrored for Black.
        self.assertEqual(len(b_final["history"]), 16)
        for a_step, b_step in zip(a_final["history"], b_final["history"], strict=True):
            self.assertEqual(b_step["mission"], a_step["mission"])
            self.assertEqual(b_step["whitePlayed"], a_step["blackPlayed"])
            self.assertEqual(b_step["blackPlayed"], a_step["whitePlayed"])
            self.assertEqual(b_step["whiteScore"], a_step["blackScore"])
            self.assertEqual(b_step["blackScore"], a_step["whiteScore"])

    async def test_decline(self):
        alice, aws = await self.make_user("Alice")
        bob, bws = await self.make_user("Bob")  # noqa: RUF059
        await self.gs.challenge(alice, "Bob")
        await self.gs.decline_from(bob, "Alice")
        self.assertEqual(last(aws.sent, "challengeDeclined")["from"], "Bob")

    async def test_withdraw_challenge(self):
        alice, aws = await self.make_user("Alice")  # noqa: RUF059
        bob, bws = await self.make_user("Bob")
        await self.gs.challenge(alice, "Bob")
        self.assertEqual(alice.pending_challenge_to, "Bob")
        self.assertEqual(bob.pending_challenge_from, "Alice")

        await self.gs.handle(alice, {"msgType": "cancelChallenge"})
        self.assertIsNone(alice.pending_challenge_to)
        self.assertIsNone(bob.pending_challenge_from)
        self.assertEqual(last(bws.sent, "challengeWithdrawn")["from"], "Alice")

        # Accepting a withdrawn challenge does nothing.
        await self.gs.accept_from(bob, "Alice")
        self.assertIsNone(last(bws.sent, "gameStart"))

    async def test_reconnect_replays_game(self):
        alice, aws = await self.make_user("Alice")  # noqa: RUF059
        await self.gs.challenge(alice, AI)
        await asyncio.sleep(0.05)
        saved = alice.last_game_message
        self.assertIsNotNone(saved)

        alice.detach()
        aws2 = FakeWebSocket()
        alice.attach(aws2)
        await self.gs.login(alice, "Alice")

        self.assertIsNotNone(last(aws2.sent, "loginOk"))
        self.assertTrue(any(m["msgType"] == saved["msgType"] for m in aws2.sent))
        await self.drive(alice, aws2)

    async def test_ack_game_over_stops_replay(self):
        alice, aws = await self.make_user("Alice")
        await self.gs.challenge(alice, AI)
        await self.drive(alice, aws)
        self.assertIsNotNone(alice.last_game_message)

        await self.gs.handle(alice, {"msgType": "ackGameOver"})
        self.assertIsNone(alice.last_game_message)

        alice.detach()
        aws2 = FakeWebSocket()
        alice.attach(aws2)
        await self.gs.login(alice, "Alice")
        self.assertIsNone(last(aws2.sent, "gameOver"))


class TestHelpPage(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_help_renders_markdown(self):
        response = self.client.get("/help")
        self.assertEqual(response.status_code, 200)
        self.assertIn("<h1", response.text)
        self.assertIn("Goofspiel", response.text)
        self.assertIn("<title>Spymaster (Remake) - How to play</title>", response.text)
        self.assertNotIn("<div id=content></div>", response.text)


class TestStaticPages(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.frontend_dir = Path(__file__).resolve().parents[1] / "src" / "frontend"

    def test_privacy_describes_remote_service_and_no_cdn(self):
        response = self.client.get("/privacy")
        self.assertEqual(response.status_code, 200)
        self.assertIn("internet connection is required", response.text)
        self.assertNotIn("cdn.jsdelivr", response.text)
        self.assertIn("rel=stylesheet", response.text)

    def test_privacy_markdown_is_rendered(self):
        response = self.client.get("/privacy")
        self.assertIn("<h1>Privacy policy</h1>", response.text)
        self.assertIn(
            "<title>Spymaster (Remake) - Privacy policy</title>", response.text
        )
        self.assertNotIn("<div id=content></div>", response.text)
        self.assertTrue(
            (self.frontend_dir.parents[1] / "Privacy.md").is_file()
        )

    def test_help_and_privacy_share_one_template(self):
        self.assertTrue((self.frontend_dir / "content.html").is_file())
        self.assertFalse((self.frontend_dir / "help.html").exists())
        self.assertFalse((self.frontend_dir / "privacy.html").exists())
        template = (self.frontend_dir / "content.html").read_text(encoding="utf-8")
        self.assertIn("PAGE_TITLE", template)
        self.assertIn('<div id="content"></div>', template)
        self.assertIn('src="static/content.ts"', template)

    def test_navigation_stays_inside_the_app(self):
        for name in ("main.html", "content.html"):
            with self.subTest(page=name):
                html = (self.frontend_dir / name).read_text(encoding="utf-8")
                self.assertIn('<nav class="navbar', html)
                self.assertIn('href="/help"', html)
                self.assertIn('href="/privacy"', html)
                self.assertNotIn('href="/help" target="_blank"', html)
                self.assertNotIn('href="/privacy" target="_blank"', html)
        lobby = self.frontend_dir / "static" / "components" / "Lobby.tsx"
        self.assertNotIn(
            'href="/help" target="_blank"', lobby.read_text(encoding="utf-8")
        )

    def test_tournaments_link_is_removed(self):
        main = (self.frontend_dir / "main.html").read_text(encoding="utf-8")
        self.assertNotIn("/tournaments", main)
        built = self.frontend_dir.parents[1] / "dist" / "frontend" / "main.html"
        if built.is_file():
            self.assertNotIn("/tournaments", built.read_text(encoding="utf-8"))

    def test_pages_do_not_reference_a_cdn_or_vendored_copy(self):
        pages = sorted(self.frontend_dir.glob("*.html"))
        self.assertTrue(pages)
        for page in pages:
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                self.assertNotIn("cdn.jsdelivr", html)
                self.assertNotIn("vendor/bootstrap", html)

    def test_bootstrap_is_imported_from_npm(self):
        entries = [
            self.frontend_dir / "static" / "index.tsx",
            self.frontend_dir / "static" / "content.ts",
            self.frontend_dir / "static" / "weights" / "index.tsx",
            self.frontend_dir / "static" / "tournaments" / "index.tsx",
        ]
        for entry in entries:
            with self.subTest(entry=entry.name):
                self.assertIn(
                    'import "bootstrap/dist/css/bootstrap.min.css";',
                    entry.read_text(encoding="utf-8"),
                )


class TestWeightsApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_weights_matrices_exposed(self):
        response = self.client.get("/api/weights")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["inputs"], 51)
        self.assertTrue(data["players"])
        for player in data["players"]:
            self.assertEqual(len(player["weights"]), 16)
            self.assertEqual(len(player["weights"][0]), 51)


class TestAnalysisApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.position: dict[str, object] = {
            "ours": [10, 5],
            "theirs": [6, 3],
            "missions": [7, 2],
            "currentMission": 7,
            "whiteScore": 0,
            "blackScore": 5,
        }

    def test_strategies_are_exposed_for_both_players(self):
        response = self.client.post("/analysis", json=self.position)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data),
            {
                "equity",
                "ourCards",
                "ourStrategy",
                "theirCards",
                "theirStrategy",
            },
        )
        self.assertEqual(len(data["ourCards"]), len(data["ourStrategy"]))
        self.assertEqual(len(data["theirCards"]), len(data["theirStrategy"]))
        self.assertAlmostEqual(sum(data["ourStrategy"]), 1.0)
        self.assertAlmostEqual(sum(data["theirStrategy"]), 1.0)
        self.assertGreaterEqual(data["equity"], -1.0)
        self.assertLessEqual(data["equity"], 1.0)

    def test_position_without_current_mission_is_rejected(self):
        position = dict(self.position)
        position["currentMission"] = None

        response = self.client.post("/analysis", json=position)

        self.assertEqual(response.status_code, 400)
        self.assertIn("current mission", response.json()["detail"])

    def test_analysis_is_cached_on_the_shared_analyser(self):
        self.assertIs(gs.analyser, ADAPTIVE_ANALYSER)

        ADAPTIVE_ANALYSER.clear_cache()

        self.client.post("/analysis", json=self.position)
        cached = ADAPTIVE_ANALYSER.cache_size()

        self.client.post("/analysis", json=self.position)

        self.assertEqual(ADAPTIVE_ANALYSER.cache_size(), cached)


class TestTournamentsApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_missing_results_returns_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.npz"
            with patch("spymaster.webserver.TOURNAMENT_RESULTS_PATH", path):
                response = self.client.get("/api/tournaments")
        self.assertEqual(response.status_code, 404)
        self.assertIn("No tournament results", response.json()["detail"])

    def test_results_exposed(self):
        results = TournamentResults(
            scores=np.array([[0, 3], [-3, 0]], dtype=np.int16),
            player_names=["Alice", "Bob"],
            evaluator_names=["Alice", "Bob"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tournament_results.npz"
            results.save(path)
            with patch("spymaster.webserver.TOURNAMENT_RESULTS_PATH", path):
                response = self.client.get("/api/tournaments")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "players": ["Alice", "Bob"],
                "evaluators": ["Alice", "Bob"],
                "scores": [[0, 3], [-3, 0]],
            },
        )


if __name__ == "__main__":
    unittest.main()
