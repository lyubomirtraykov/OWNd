"""Regression tests for OpenWebNet session negotiation."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from OWNd.connection import (
    OWNCommandSession,
    OWNEventSession,
    OWNGateway,
    OWNSession,
)


class FakeWriter:
    """Minimal asyncio writer used by negotiation tests."""

    def __init__(self) -> None:
        self.written: list[bytes] = []
        self.closed = False

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


def make_session(password: str | None = "12345") -> tuple[OWNSession, FakeWriter]:
    """Create a session with in-memory stream doubles."""
    gateway = OWNGateway(
        {
            "address": "192.0.2.1",
            "port": 20000,
            "password": password,
            "modelName": "Test",
        }
    )
    session = OWNSession(gateway=gateway)
    session._stream_reader = asyncio.StreamReader()  # noqa: SLF001
    writer = FakeWriter()
    session._stream_writer = writer  # type: ignore[assignment]  # noqa: SLF001
    return session, writer


class NegotiationTest(unittest.IsolatedAsyncioTestCase):
    """Authentication must never succeed on an unexpected frame."""

    async def test_legacy_ack_still_succeeds(self) -> None:
        session, _ = make_session()
        session._read_frame = AsyncMock(  # type: ignore[method-assign]  # noqa: SLF001
            side_effect=["*#*1##", "*#123456789##", "*#*1##"]
        )

        result = await session._negotiate()  # noqa: SLF001

        self.assertEqual(result, {"Success": True, "Message": None})

    async def test_legacy_unexpected_password_response_fails_closed(self) -> None:
        session, _ = make_session()
        session._read_frame = AsyncMock(  # type: ignore[method-assign]  # noqa: SLF001
            side_effect=["*#*1##", "*#123456789##", "*99*0##"]
        )

        result = await session._negotiate()  # noqa: SLF001

        self.assertEqual(
            result, {"Success": False, "Message": "negotiation_error"}
        )

    async def test_hmac_unexpected_challenge_response_fails_closed(self) -> None:
        session, _ = make_session()
        session._read_frame = AsyncMock(  # type: ignore[method-assign]  # noqa: SLF001
            side_effect=["*#*1##", "*98*1##", "*#*1##"]
        )

        result = await session._negotiate()  # noqa: SLF001

        self.assertEqual(
            result, {"Success": False, "Message": "negotiation_error"}
        )

    async def test_hmac_unexpected_server_response_fails_closed(self) -> None:
        session, _ = make_session()
        session._read_frame = AsyncMock(  # type: ignore[method-assign]  # noqa: SLF001
            side_effect=["*#*1##", "*98*1##", "*#123456789##", "*#*1##"]
        )

        result = await session._negotiate()  # noqa: SLF001

        self.assertEqual(
            result, {"Success": False, "Message": "negotiation_error"}
        )

    async def test_non_numeric_password_returns_controlled_error(self) -> None:
        session, writer = make_session("not-a-number")

        result = await session._negotiate()  # noqa: SLF001

        self.assertEqual(result, {"Success": False, "Message": "password_error"})
        self.assertEqual(writer.written, [])

    async def test_negotiation_has_an_absolute_deadline(self) -> None:
        session, _ = make_session()

        async def stalled_exchange() -> dict:
            await asyncio.sleep(1)
            return {"Success": True, "Message": None}

        session._negotiate_exchange = stalled_exchange  # type: ignore[method-assign]  # noqa: SLF001
        with patch("OWNd.connection.NEGOTIATION_TOTAL_TIMEOUT", 0.01):
            result = await session._negotiate()  # noqa: SLF001

        self.assertEqual(
            result, {"Success": False, "Message": "negotiation_timeout"}
        )

    async def test_negotiation_enforces_frame_budget(self) -> None:
        session, _ = make_session()
        session._read_frame = AsyncMock(  # type: ignore[method-assign]  # noqa: SLF001
            side_effect=["*#*1##", "*#123456789##"]
        )

        with patch("OWNd.connection.NEGOTIATION_MAX_FRAMES", 2):
            result = await session._negotiate()  # noqa: SLF001

        self.assertEqual(
            result, {"Success": False, "Message": "negotiation_timeout"}
        )


class SessionCleanupTest(unittest.IsolatedAsyncioTestCase):
    """Temporary sessions release their stream on every exit path."""

    async def test_test_connection_closes_after_negotiation_error(self) -> None:
        session, writer = make_session()
        reader = asyncio.StreamReader()
        session._negotiate = AsyncMock(  # type: ignore[method-assign]  # noqa: SLF001
            side_effect=asyncio.IncompleteReadError(partial=b"", expected=1)
        )

        with patch(
            "OWNd.connection.asyncio.open_connection",
            new=AsyncMock(return_value=(reader, writer)),
        ):
            result = await session.test_connection()

        self.assertEqual(result, {"Success": False, "Message": "connection_error"})
        self.assertTrue(writer.closed)
        self.assertIsNone(session._stream_writer)  # noqa: SLF001

    async def test_event_helper_closes_temporary_session(self) -> None:
        session, _ = make_session()
        assert session.gateway is not None

        with (
            patch.object(
                OWNEventSession,
                "connect",
                new=AsyncMock(return_value={"Success": True, "Message": None}),
            ),
            patch.object(OWNEventSession, "close", new=AsyncMock()) as close,
        ):
            result = await OWNEventSession.connect_to_gateway(session.gateway)

        self.assertEqual(result, {"Success": True, "Message": None})
        close.assert_awaited_once()

    async def test_command_send_helper_closes_temporary_session(self) -> None:
        session, _ = make_session()
        assert session.gateway is not None

        with (
            patch.object(
                OWNCommandSession,
                "connect",
                new=AsyncMock(return_value={"Success": True, "Message": None}),
            ),
            patch.object(OWNCommandSession, "send", new=AsyncMock()) as send,
            patch.object(OWNCommandSession, "close", new=AsyncMock()) as close,
        ):
            await OWNCommandSession.send_to_gateway("*#13**0##", session.gateway)

        send.assert_awaited_once_with("*#13**0##")
        close.assert_awaited_once()


class CommandResponseTest(unittest.IsolatedAsyncioTestCase):
    """Command acknowledgement reads are bounded globally and by frame count."""

    async def test_non_signaling_frames_hit_the_frame_budget(self) -> None:
        gateway = OWNGateway(
            {
                "address": "192.0.2.1",
                "port": 20000,
                "password": "12345",
                "modelName": "Test",
            }
        )
        session = OWNCommandSession(gateway=gateway)
        session._stream_reader = asyncio.StreamReader()  # noqa: SLF001
        session._stream_writer = FakeWriter()  # type: ignore[assignment]  # noqa: SLF001
        session._read_frame = AsyncMock(  # type: ignore[method-assign]  # noqa: SLF001
            return_value="*1*1*1##"
        )

        with (
            patch("OWNd.connection.COMMAND_RESPONSE_MAX_FRAMES", 3),
            self.assertRaises(TimeoutError),
        ):
            await session._read_signaling_response()  # noqa: SLF001

        self.assertEqual(session._read_frame.await_count, 3)  # type: ignore[attr-defined]  # noqa: SLF001

    async def test_signaling_response_has_an_absolute_deadline(self) -> None:
        gateway = OWNGateway(
            {
                "address": "192.0.2.1",
                "port": 20000,
                "password": "12345",
                "modelName": "Test",
            }
        )
        session = OWNCommandSession(gateway=gateway)
        session._stream_reader = asyncio.StreamReader()  # noqa: SLF001
        session._stream_writer = FakeWriter()  # type: ignore[assignment]  # noqa: SLF001

        async def stalled_frame(_timeout: float) -> str:
            await asyncio.sleep(1)
            return "*#*1##"

        session._read_frame = stalled_frame  # type: ignore[method-assign]  # noqa: SLF001
        with (
            patch("OWNd.connection.COMMAND_TIMEOUT", 0.01),
            self.assertRaises(TimeoutError),
        ):
            await session._read_signaling_response()  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
