import asyncio
import unittest

from fastapi.testclient import TestClient

from spymaster.players.computer_players import computer_players
from spymaster.webserver import GameServer, app

AI = next(iter(computer_players))


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
        session, _ = self.gs.get_or_create_session(ws)
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
        _, a = await self.make_user("Alice")
        b = FakeWebSocket()
        session_b, _ = self.gs.get_or_create_session(b)
        session_b.attach(b)
        await self.gs.login(session_b, "Alice")
        failed = last(b.sent, "loginFailed")
        self.assertIsNotNone(failed)
        self.assertIn("already in use", failed["reason"])

    async def test_blank_username_rejected(self):
        ws = FakeWebSocket()
        session, _ = self.gs.get_or_create_session(ws)
        session.attach(ws)
        await self.gs.login(session, "   ")
        self.assertIsNotNone(last(ws.sent, "loginFailed"))

    async def test_cookie_reuses_session(self):
        ws = FakeWebSocket()
        first, cookies = self.gs.get_or_create_session(ws)
        self.assertIsNotNone(cookies)
        self.assertEqual(cookies[0][0], b"Set-Cookie")

        ws2 = FakeWebSocket(cookies={"session": first.session_id})
        second, cookies2 = self.gs.get_or_create_session(ws2)
        self.assertIs(first, second)
        self.assertIsNone(cookies2)

    async def test_play_against_ai(self):
        session, ws = await self.make_user("Alice")
        await self.gs.challenge(session, AI)
        self.assertIsNotNone(last(ws.sent, "gameStart"))
        self.assertTrue(any(p["name"] == AI for p in self.gs.online_players()))

        await self.drive(session, ws)
        over = last(ws.sent, "gameOver")
        self.assertIsNotNone(over)
        self.assertEqual(over["reason"], "ended")
        self.assertFalse(session.in_game)

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

        await asyncio.gather(
            self.drive(alice, aws),
            self.drive(bob, bws),
        )
        a_over = last(aws.sent, "gameOver")
        b_over = last(bws.sent, "gameOver")
        self.assertEqual(a_over["winner"], b_over["winner"])

    async def test_decline(self):
        alice, aws = await self.make_user("Alice")
        bob, bws = await self.make_user("Bob")
        await self.gs.challenge(alice, "Bob")
        await self.gs.decline_from(bob, "Alice")
        self.assertEqual(last(aws.sent, "challengeDeclined")["from"], "Bob")

    async def test_reconnect_replays_game(self):
        alice, aws = await self.make_user("Alice")
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


class TestHelpPage(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_help_renders_markdown(self):
        response = self.client.get("/help")
        self.assertEqual(response.status_code, 200)
        self.assertIn("<h1", response.text)
        self.assertIn("Goofspiel", response.text)
        self.assertNotIn("<!--HELP_CONTENT-->", response.text)


if __name__ == "__main__":
    unittest.main()