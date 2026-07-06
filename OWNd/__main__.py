"""OWNd entry point when running it directly from CLI
(as opposed to imported into another project)
"""

import argparse
import asyncio
import contextlib
import logging
import signal
import sys

from .connection import OWNEventSession, OWNGateway
from .message import OWNMessage


async def main(arguments: dict, connection: OWNEventSession) -> None:
    """Package entry point!"""

    address = (
        arguments["address"]
        if "address" in arguments and isinstance(arguments["address"], str)
        else None
    )
    port = (
        arguments["port"]
        if "port" in arguments and isinstance(arguments["port"], int)
        else None
    )
    password = (
        arguments["password"]
        if "password" in arguments and isinstance(arguments["password"], str)
        else None
    )
    serial_number = (
        arguments["serialNumber"]
        if "serialNumber" in arguments and isinstance(arguments["serialNumber"], str)
        else None
    )
    logger = (
        arguments["logger"]
        if "logger" in arguments and isinstance(arguments["logger"], logging.Logger)
        else logging.getLogger("OWNd")
    )

    logger.info("Starting discovery of a supported gateway via SSDP")
    gateway = await OWNGateway.build_from_discovery_info(
        {
            "address": address,
            "port": port,
            "password": password,
            "serialNumber": serial_number,
        }
    )
    connection.gateway = gateway
    connection.logger = logger

    logger.info("Starting connection to the discovered gateway")
    await connection.connect()

    logger.info("Now waiting for events from the gateway (e.g. BUS frames)")
    while True:
        message = await connection.get_next()
        if message:
            logger.debug("Received: %s", message)
            if isinstance(message, OWNMessage) and message.is_event:
                logger.info(message.human_readable_log)


# ---------------------------
# Modern, Python 3.13-safe CLI
# ---------------------------


def _build_logger(verbosity: int) -> logging.Logger:
    # Use a consistent, propagate-able logger name
    logger = logging.getLogger("ownd")
    logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if module is re-imported
    if not logger.handlers:
        stream = logging.StreamHandler(sys.stdout)
        if verbosity == 2:
            stream.setLevel(logging.DEBUG)
        elif verbosity == 0:
            stream.setLevel(logging.WARNING)
        else:
            stream.setLevel(logging.INFO)

        stream.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(stream)

    # Let messages also propagate to HA's root logger when imported there
    logger.propagate = True
    return logger


async def _async_entry(_arguments: dict, event_session: OWNEventSession) -> None:
    logger: logging.Logger = _arguments["logger"]

    # Graceful shutdown support where signals are available
    stop_event = asyncio.Event()
    try:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, stop_event.set)
        loop.add_signal_handler(signal.SIGINT, stop_event.set)
    except (NotImplementedError, RuntimeError):
        # Windows or restricted env: signals may be unavailable
        pass

    logger.info("Starting OWNd.")
    runner = asyncio.create_task(main(_arguments, event_session), name="ownd-main")

    try:
        # Wait for either main task to finish (error) or a stop signal
        done, pending = await asyncio.wait(
            {runner, asyncio.create_task(stop_event.wait(), name="ownd-stop")},
            return_when=asyncio.FIRST_COMPLETED,
        )

        # If main task raised, surface the exception
        if runner in done:
            exc = runner.exception()
            if exc:
                logger.exception("OWNd crashed", exc_info=exc)
                raise exc
    finally:
        logger.info("Stopping OWNd.")
        # Cancel background tasks if still running
        if not runner.done():
            runner.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await runner

        # Close the event session cleanly
        try:
            await event_session.close()
        finally:
            logger.info("OWNd stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--address", type=str, help="IP address of the OpenWebNet gateway"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="TCP port to connect the gateway, default is 20000",
    )
    parser.add_argument(
        "-P",
        "--password",
        type=str,
        help="Numeric password for the OpenWebNet connection, default is 12345",
    )
    parser.add_argument(
        "-m",
        "--mac",
        type=str,
        help="MAC address of the gateway (to be used as ID, if not found via SSDP)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        type=int,
        help="Change output verbosity [0 = WARNING; 1 = INFO (default); 2 = DEBUG]",
    )
    args = parser.parse_args()

    _logger = _build_logger(args.verbose if args.verbose is not None else 1)

    event_session = OWNEventSession(gateway=None, logger=_logger)
    _arguments = {
        "address": args.address,
        "port": args.port,
        "password": args.password,
        "serialNumber": args.mac,
        "logger": _logger,
    }

    try:
        asyncio.run(_async_entry(_arguments, event_session))
    except KeyboardInterrupt:
        _logger.info("OWNd interrupted by user.")
