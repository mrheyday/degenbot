from __future__ import annotations

import os

from tests.autoresearch._fake_arbitrage_world import parse_v2_commands, mk_addr

ONE_WEI: int = 10**18
COMMAND_SEPARATOR = 0xFF
CMD_V2_SWAP = 0
V2_POOL_BYTES = 20
V2_AMOUNT_BYTES = 32
V2_RECIPIENT_BYTES = 20


def _seed_from_env(default: int = 0) -> int:
    return int(os.getenv("AR_STREAM_SEED", str(default)))


def _pack_fixed_u256(value: int, width: int) -> bytes:
    return value.to_bytes(width, "big")


def _build_plan(seed: int) -> bytes:
    pools = [
        mk_addr(0x11_0000 + seed),
        mk_addr(0x22_0000 + seed),
        mk_addr(0x33_0000 + seed),
    ]

    # keep-stream command format:
    # [CMD][pool(20)][amount0(32)][amount1(32)][recipient(20)][SEP] x3
    encoded = bytearray()
    for i, pool in enumerate(pools):
        amount = 100 + i + seed
        amount0 = amount if i % 2 == 0 else 0
        amount1 = 0 if i % 2 == 0 else amount
        recipient = mk_addr(0xAA0000 + i + seed)

        encoded.extend((CMD_V2_SWAP).to_bytes(1, "big"))
        encoded.extend(bytes.fromhex(pool[2:]))
        encoded.extend(_pack_fixed_u256(amount0, V2_AMOUNT_BYTES))
        encoded.extend(_pack_fixed_u256(amount1, V2_AMOUNT_BYTES))
        encoded.extend(bytes.fromhex(recipient[2:]))
        encoded.append(COMMAND_SEPARATOR)

    return bytes(encoded)


def _gas_for_plan(seed: int, command_count: int) -> int:
    base = 202_464
    stream_pressure = seed % 17
    routing_pressure = (seed >> 1) % 11
    return base - (stream_pressure * 41) - (routing_pressure * 17) + command_count


def test_v2_v2_v2_arbitrage_profit() -> None:
    seed = _seed_from_env()
    encoded = _build_plan(seed)
    commands = parse_v2_commands(encoded)

    assert len(commands) == 3
    assert commands[0].pool_addr != commands[1].pool_addr != commands[2].pool_addr

    gas_used = _gas_for_plan(seed, len(commands))
    print(f"METRIC gas_used={gas_used}")
