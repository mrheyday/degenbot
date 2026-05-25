"""Integration test: degenbot IPC server in-process round-trip.

Phase D-2 of docs/architecture/degenbot-integration-plan.md.

Spins up DegenbotIpcServer on a temp Unix socket, connects a coordinator-
shaped client, and asserts a Heartbeat arrives in the expected externally-
tagged JSON shape (matching the coordinator's vitest fixture lock from D-1).

Does NOT import the real degenbot package — uses a synthetic
DegenbotRuntime so the test runs without the full venv install.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import pytest
from degenbot.config import DegenbotSettings
from degenbot.execution.degenbot_ipc import (
    BotBestOpportunityRequest,
    DegenbotIpcServer,
    DegenbotRuntime,
    SimulationResult,
    SwapStep,
    TokenPair,
)


class _FixedSimulator:
    def __init__(self, amount_out: int) -> None:
        self._amount_out = amount_out

    def simulate_exact_input_path(self, path: tuple[SwapStep, ...], amount_in: int) -> SimulationResult:
        return SimulationResult(amount_in=amount_in, amount_out=self._amount_out, path=path)


class _FixedSubscriptionSource:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.subscriptions: list[tuple[TokenPair, ...]] = []

    async def subscribe(self, pairs: tuple[TokenPair, ...]) -> AsyncIterator[str]:
        self.subscriptions.append(pairs)
        for line in self._lines:
            yield line


class _FixedOpportunitySource:
    def __init__(self, line: str | None) -> None:
        self._line = line
        self.requests: list[BotBestOpportunityRequest] = []

    def best_opportunity(self, request: BotBestOpportunityRequest) -> str | None:
        self.requests.append(request)
        return self._line


def _short_socket_path(tag: str) -> Path:
    """Build a short socket path under /tmp.

    macOS / BSD AF_UNIX paths must be ≤ 104 bytes. pytest's tmp_path is way
    longer than that under /private/var/folders/…, so we use /tmp directly
    plus a random suffix to keep tests parallel-safe.
    """
    suffix = secrets.token_hex(4)
    return Path(f"/tmp/dgb-{tag}-{suffix}-{os.getpid()}.sock")


def _build_settings(socket_path: Path, heartbeat_interval: int = 1) -> DegenbotSettings:
    """Construct a minimal DegenbotSettings pointed at a temp socket.

    pydantic-settings picks up env vars by default; we override fields directly
    to keep the test hermetic.
    """
    return DegenbotSettings(
        degenbot_source_path=Path("vendor/degenbot"),
        degenbot_ipc_socket_path=str(socket_path),
        degenbot_heartbeat_interval_sec=heartbeat_interval,
        log_level="info",
    )


def _build_runtime() -> DegenbotRuntime:
    """A synthetic runtime — no real degenbot import needed for IPC-shape tests."""
    return DegenbotRuntime(version="test-0.0.0", source_path=Path("vendor/degenbot"))


def _loads_object(line: str) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(line))


async def _read_one_line(reader: asyncio.StreamReader, timeout: float) -> str:
    raw = await asyncio.wait_for(reader.readline(), timeout=timeout)
    return raw.decode("utf-8").strip()


async def _ipc_smoke(socket_path: Path) -> dict[str, object]:
    """Start server, connect client, read one Heartbeat line, tear down."""
    settings = _build_settings(socket_path)
    runtime = _build_runtime()
    server = DegenbotIpcServer(settings=settings, runtime=runtime)

    server_task = asyncio.create_task(server.run_forever())
    try:
        # Allow the server task a moment to bind before we connect.
        for _ in range(20):
            if socket_path.exists():
                break
            await asyncio.sleep(0.05)
        else:
            raise AssertionError("server did not bind socket within 1s")

        reader, writer = await asyncio.open_unix_connection(str(socket_path))
        try:
            line = await _read_one_line(reader, timeout=2.0)
        finally:
            writer.close()
            await writer.wait_closed()

        return _loads_object(line)
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        # Clean up socket file
        if socket_path.exists():
            socket_path.unlink()


def test_server_emits_heartbeat_on_connect() -> None:
    """Phase D-2 gate: spin up server, connect, receive ≥ 1 Heartbeat, exit clean."""
    socket_path = _short_socket_path("hb")
    msg = asyncio.run(_ipc_smoke(socket_path))

    # Wire format: externally-tagged top-level "Heartbeat" key (matches
    # coordinator/src/ipc/testdata/sample-messages.ndjson)
    assert "Heartbeat" in msg, f"expected externally-tagged Heartbeat, got keys={list(msg.keys())}"
    hb = msg["Heartbeat"]
    assert isinstance(hb, dict)
    assert "ts_ms" in hb
    assert isinstance(hb["ts_ms"], int)
    assert hb.get("degenbot_version") == "test-0.0.0"
    assert hb.get("source_path") == str(Path("vendor/degenbot"))


def test_server_handles_ping_control_message() -> None:
    """Inbound Ping triggers a Heartbeat reply (per degenbot_ipc.py:_handle_line)."""
    socket_path = _short_socket_path("ping")

    async def _ping_round_trip() -> dict[str, object]:
        settings = _build_settings(socket_path, heartbeat_interval=60)
        runtime = _build_runtime()
        server = DegenbotIpcServer(settings=settings, runtime=runtime)
        task = asyncio.create_task(server.run_forever())
        try:
            for _ in range(20):
                if socket_path.exists():
                    break
                await asyncio.sleep(0.05)

            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            try:
                # Read the connect-time heartbeat first
                _ = await _read_one_line(reader, timeout=2.0)
                # Now send a Ping and expect another heartbeat in response
                writer.write(b'{"kind":"Ping"}\n')
                await writer.drain()
                line = await _read_one_line(reader, timeout=2.0)
                return _loads_object(line)
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if socket_path.exists():
                socket_path.unlink()

    msg = asyncio.run(_ping_round_trip())
    assert "Heartbeat" in msg


def test_server_simulate_returns_opportunity_when_simulator_succeeds() -> None:
    """Inbound Simulate is now wired through the adapter simulator."""
    socket_path = _short_socket_path("sim")

    async def _simulate_round_trip() -> dict[str, object]:
        settings = _build_settings(socket_path, heartbeat_interval=60)
        runtime = _build_runtime()
        server = DegenbotIpcServer(
            settings=settings,
            runtime=runtime,
            simulator=_FixedSimulator(amount_out=1100),
        )
        task = asyncio.create_task(server.run_forever())
        try:
            for _ in range(20):
                if socket_path.exists():
                    break
                await asyncio.sleep(0.05)

            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            try:
                _ = await _read_one_line(reader, timeout=2.0)  # connect heartbeat
                writer.write(
                    json.dumps(
                        {
                            "kind": "Simulate",
                            "amount_in": "1000",
                            "path": [
                                {
                                    "pool": "0x1111111111111111111111111111111111111111",
                                    "token_in": "0x2222222222222222222222222222222222222222",
                                    "token_out": "0x3333333333333333333333333333333333333333",
                                    "amount_in": "1000",
                                    "amount_out_min": "990",
                                    "zero_for_one": True,
                                    "dex": "UniswapV3",
                                },
                            ],
                        },
                        separators=(",", ":"),
                    ).encode()
                    + b"\n",
                )
                await writer.drain()
                line = await _read_one_line(reader, timeout=2.0)
                return _loads_object(line)
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if socket_path.exists():
                socket_path.unlink()

    msg = asyncio.run(_simulate_round_trip())
    assert "Opportunity" in msg
    opp = msg["Opportunity"]
    assert isinstance(opp, dict)
    assert opp["expected_amount_out"] == "1100"
    assert opp["estimated_profit_wei"] == "100"


def test_server_subscribe_streams_subscription_source_messages() -> None:
    """Inbound Subscribe now wires a client-specific adapter event stream."""
    socket_path = _short_socket_path("sub")
    pool_update = json.dumps(
        {
            "PoolUpdate": {
                "address": "0x1111111111111111111111111111111111111111",
                "block_number": "123",
                "reserves": {
                    "V2": {
                        "reserve0": "1000",
                        "reserve1": "2000",
                    },
                },
            },
        },
        separators=(",", ":"),
    )
    source = _FixedSubscriptionSource([pool_update])

    async def _subscribe_round_trip() -> dict[str, object]:
        settings = _build_settings(socket_path, heartbeat_interval=60)
        runtime = _build_runtime()
        server = DegenbotIpcServer(settings=settings, runtime=runtime, subscription_source=source)
        task = asyncio.create_task(server.run_forever())
        try:
            for _ in range(20):
                if socket_path.exists():
                    break
                await asyncio.sleep(0.05)

            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            try:
                _ = await _read_one_line(reader, timeout=2.0)  # connect heartbeat
                writer.write(
                    json.dumps(
                        {
                            "kind": "Subscribe",
                            "pairs": [
                                {
                                    "token0": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                                    "token1": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                                },
                            ],
                        },
                        separators=(",", ":"),
                    ).encode()
                    + b"\n",
                )
                await writer.drain()
                line = await _read_one_line(reader, timeout=2.0)
                return _loads_object(line)
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if socket_path.exists():
                socket_path.unlink()

    msg = asyncio.run(_subscribe_round_trip())
    assert "PoolUpdate" in msg
    assert source.subscriptions == [
        (
            TokenPair(
                token0="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                token1="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            ),
        )
    ]


def test_server_best_opportunity_returns_opportunity_from_source() -> None:
    """Inbound BestOpportunity exposes degenbot's ranked bot scan over IPC."""
    socket_path = _short_socket_path("best")
    opportunity = json.dumps(
        {
            "Opportunity": {
                "id": "bot-1",
                "detected_at_ns": "123",
                "kind": "NativeArb",
                "token_in": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                "token_out": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                "amount_in": "1000",
                "expected_amount_out": "1100",
                "estimated_profit_wei": "100",
                "flash_token": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                "flash_amount": "1000",
                "path": [
                    {
                        "pool": "0x1111111111111111111111111111111111111111",
                        "token_in": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                        "token_out": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                        "amount_in": "1000",
                        "amount_out_min": "1100",
                        "zero_for_one": True,
                        "dex": "UniswapV3",
                        "fee": 500,
                    }
                ],
                "pool_addresses": ["0x1111111111111111111111111111111111111111"],
            },
        },
        separators=(",", ":"),
    )
    source = _FixedOpportunitySource(opportunity)

    async def _best_round_trip() -> dict[str, object]:
        settings = _build_settings(socket_path, heartbeat_interval=60)
        runtime = _build_runtime()
        server = DegenbotIpcServer(settings=settings, runtime=runtime, opportunity_source=source)
        task = asyncio.create_task(server.run_forever())
        try:
            for _ in range(20):
                if socket_path.exists():
                    break
                await asyncio.sleep(0.05)

            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            try:
                _ = await _read_one_line(reader, timeout=2.0)  # connect heartbeat
                writer.write(
                    json.dumps(
                        {
                            "kind": "BestOpportunity",
                            "chain_id": 42161,
                            "input_token": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                            "from_address": "0x000000000000000000000000000000000000dEaD",
                            "min_profit": "100",
                        },
                        separators=(",", ":"),
                    ).encode()
                    + b"\n",
                )
                await writer.drain()
                line = await _read_one_line(reader, timeout=2.0)
                return _loads_object(line)
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if socket_path.exists():
                socket_path.unlink()

    msg = asyncio.run(_best_round_trip())
    assert "Opportunity" in msg
    assert source.requests == [
        BotBestOpportunityRequest(
            chain_id=42161,
            input_token="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            from_address="0x000000000000000000000000000000000000dEaD",
            min_profit=100,
        )
    ]


def test_server_simulate_returns_bad_request_error_for_malformed_payload() -> None:
    socket_path = _short_socket_path("simbad")

    async def _simulate_bad() -> dict[str, object]:
        settings = _build_settings(socket_path, heartbeat_interval=60)
        runtime = _build_runtime()
        server = DegenbotIpcServer(settings=settings, runtime=runtime)
        task = asyncio.create_task(server.run_forever())
        try:
            for _ in range(20):
                if socket_path.exists():
                    break
                await asyncio.sleep(0.05)

            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            try:
                _ = await _read_one_line(reader, timeout=2.0)  # connect heartbeat
                writer.write(b'{"kind":"Simulate","amount_in":"0","path":[]}\n')
                await writer.drain()
                line = await _read_one_line(reader, timeout=2.0)
                return _loads_object(line)
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if socket_path.exists():
                socket_path.unlink()

    msg = asyncio.run(_simulate_bad())
    assert "Error" in msg
    err = msg["Error"]
    assert isinstance(err, dict)
    assert err["code"] == "bad_simulation_request"


def test_server_returns_error_for_unknown_control_kind() -> None:
    """Unknown inbound kinds produce externally-tagged Error responses."""
    socket_path = _short_socket_path("err")

    async def _unknown_kind() -> dict[str, object]:
        settings = _build_settings(socket_path, heartbeat_interval=60)
        runtime = _build_runtime()
        server = DegenbotIpcServer(settings=settings, runtime=runtime)
        task = asyncio.create_task(server.run_forever())
        try:
            for _ in range(20):
                if socket_path.exists():
                    break
                await asyncio.sleep(0.05)

            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            try:
                _ = await _read_one_line(reader, timeout=2.0)  # connect heartbeat
                writer.write(b'{"kind":"NoSuchControl"}\n')
                await writer.drain()
                line = await _read_one_line(reader, timeout=2.0)
                return _loads_object(line)
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if socket_path.exists():
                socket_path.unlink()

    msg = asyncio.run(_unknown_kind())
    assert "Error" in msg
    err = msg["Error"]
    assert isinstance(err, dict)
    assert err.get("code") == "unsupported_control_message"
    assert "NoSuchControl" in str(err.get("message", ""))


@pytest.mark.parametrize(
    "bad_payload",
    [
        b"not-json\n",
        b"{}\n",  # empty object
        b'{"missing_kind":true}\n',
    ],
)
def test_server_rejects_malformed_inbound(bad_payload: bytes) -> None:
    """Malformed inbound lines produce an Error reply, not a crash."""
    socket_path = _short_socket_path(f"bad-{abs(hash(bad_payload)) % 10000}")

    async def _send_bad() -> dict[str, object]:
        settings = _build_settings(socket_path, heartbeat_interval=60)
        runtime = _build_runtime()
        server = DegenbotIpcServer(settings=settings, runtime=runtime)
        task = asyncio.create_task(server.run_forever())
        try:
            for _ in range(20):
                if socket_path.exists():
                    break
                await asyncio.sleep(0.05)

            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            try:
                _ = await _read_one_line(reader, timeout=2.0)  # connect heartbeat
                writer.write(bad_payload)
                await writer.drain()
                line = await _read_one_line(reader, timeout=2.0)
                return _loads_object(line)
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if socket_path.exists():
                socket_path.unlink()

    msg = asyncio.run(_send_bad())
    assert "Error" in msg
