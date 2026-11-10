import asyncio
import unittest
from datetime import timedelta
from typing import cast
from unittest import mock

from starlette.websockets import WebSocket

import spymaster.session as session_module
from spymaster.session import Forfeit, UserSession


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_json(self, msg):
        self.sent.append(msg)


class TestSessionGrace(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        for p in (
            mock.patch.object(session_module, "GRACE_PERIOD", timedelta(seconds=0.5)),
            mock.patch.object(session_module, "GRACE_REPOLL_SECONDS", 0.05),
        ):
            p.start()
            self.addCleanup(p.stop)

    async def test_forfeit_after_grace(self):
        session = UserSession("s1")
        session.username = "Alice"
        session.attach(FakeWebSocket())  # ty: ignore[invalid-argument-type]
        task = asyncio.create_task(session.await_card())
        await asyncio.sleep(0.05)
        session.detach()
        with self.assertRaises(Forfeit) as ctx:
            await asyncio.wait_for(task, timeout=5)
        self.assertEqual(ctx.exception.player_name, "Alice")
        self.assertEqual(ctx.exception.reason, "grace")

    async def test_reconnect_within_grace_resumes(self):
        session = UserSession("s2")
        session.username = "Bob"
        session.attach(FakeWebSocket())  # ty: ignore[invalid-argument-type]
        task = asyncio.create_task(session.await_card())
        await asyncio.sleep(0.05)
        session.detach()
        await asyncio.sleep(0.1)
        session.attach(FakeWebSocket())  # ty: ignore[invalid-argument-type]
        session.set_card(7)
        self.assertEqual(await asyncio.wait_for(task, timeout=2), 7)

    async def test_explicit_forfeit(self):
        session = UserSession("s3")
        session.username = "Carol"
        session.attach(FakeWebSocket())  # ty: ignore[invalid-argument-type]
        task = asyncio.create_task(session.await_card())
        await asyncio.sleep(0.05)
        session.forfeit("left")
        with self.assertRaises(Forfeit) as ctx:
            await asyncio.wait_for(task, timeout=2)
        self.assertEqual(ctx.exception.reason, "left")

    async def test_set_card_resolves(self):
        session = UserSession("s4")
        session.username = "Dave"
        session.attach(FakeWebSocket())  # ty: ignore[invalid-argument-type]
        task = asyncio.create_task(session.await_card())
        await asyncio.sleep(0.05)
        session.set_card(9)
        self.assertEqual(await asyncio.wait_for(task, timeout=2), 9)

    async def test_disconnect_after_pick_still_forfeits(self):
        # The pick starts while connected, then the connection drops.
        session = UserSession("s5")
        session.username = "Erin"
        session.attach(FakeWebSocket())  # ty: ignore[invalid-argument-type]
        task = asyncio.create_task(session.await_card())
        await asyncio.sleep(0.2)  # allow the poll loop to start
        session.detach()
        with self.assertRaises(Forfeit):
            await asyncio.wait_for(task, timeout=5)


if __name__ == "__main__":
    unittest.main()
