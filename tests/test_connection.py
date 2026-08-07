"""Regression tests for OpenWebNet session negotiation."""

import asyncio
import unittest
from unittest.mock import AsyncMock

from OWNd.connection import OWNGateway, OWNSession


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


if __name__ == "__main__":
    unittest.main()
