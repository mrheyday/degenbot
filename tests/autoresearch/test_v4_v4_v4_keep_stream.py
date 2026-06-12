from __future__ import annotations

import os
import pytest

from tests.autoresearch._fake_arbitrage_world import (
    CMD_V4_SWAP,
    COMMAND_SEPARATOR,
    MockERC20,
    MockExecutor,
    MockV4Pool,
    MAX_INT128,
    V4Command,
    parse_v4_callback_layers,
    mk_addr,
    parse_v4_commands,
)

ONE_WEI = 10**18


def _seed_from_env(default: int = 0) -> int:
    return int(os.getenv("AR_STREAM_SEED", str(default)))


def _pack_fixed_u256(value: int) -> bytes:
    return value.to_bytes(32, "big")


def _build_v4_keep_plan(seed: int) -> tuple[bytes, list[V4Command], dict[str, MockV4Pool], MockExecutor]:
    pool_addrs = [
        mk_addr(0x5100 + seed),
        mk_addr(0x5200 + seed),
        mk_addr(0x5300 + seed),
    ]

    owner = mk_addr(0x5000 + seed)
    executor_addr = mk_addr(0x52000 + seed)

    weth = MockERC20("Wrapped Ether", "WETH", 18, mk_addr(0xaaa), {})
    token_a = MockERC20("Token A", "TKA", 18, mk_addr(0xbbb), {})
    token_b = MockERC20("Token B", "TKB", 18, mk_addr(0xccc), {})

    pool1_addr, pool2_addr, pool3_addr = pool_addrs
    pool1 = MockV4Pool(weth, token_a, pool1_addr)
    pool2 = MockV4Pool(token_a, token_b, pool2_addr)
    pool3 = MockV4Pool(token_b, weth, pool3_addr)

    pools = {
        pool1.address: pool1,
        pool2.address: pool2,
        pool3.address: pool3,
    }

    base_amount = 1 * ONE_WEI // 100
    command_specs = [
        (pool1_addr, True, base_amount + 11),
        (pool2_addr, True, base_amount + 13),
        (pool3_addr, False, base_amount + 17),
    ]

    encoded = bytearray()
    for i, (pool, zfo, amount) in enumerate(command_specs):
        recipient = mk_addr(0x9000 + seed + i)
        encoded.extend(CMD_V4_SWAP.to_bytes(1, "big"))
        encoded.extend(bytes.fromhex(pool[2:]))
        encoded.extend((1).to_bytes(1, "big") if zfo else (0).to_bytes(1, "big"))
        encoded.extend(_pack_fixed_u256(amount))
        encoded.extend(bytes.fromhex(recipient[2:]))
        encoded.append(COMMAND_SEPARATOR)

    commands = parse_v4_commands(bytes(encoded))

    # provide deterministic context for command count and route shape assertions
    weth.mint(owner, 1_000 * ONE_WEI)
    return bytes(encoded), commands, pools, MockExecutor(owner=owner, weth=weth, address=executor_addr)


def _gas_for_v4_keep_stream(seed: int, command_count: int) -> int:
    total = 0
    for index in range(command_count):
        total += 11_500 + index * 17 + (seed % 9)
    return total


def test_v4_v4_v4_keep_stream_profit_profile() -> None:
    seed = _seed_from_env()
    _, commands, pools, executor = _build_v4_keep_plan(seed)

    assert len(commands) == 3
    assert commands[0].pool_addr in pools
    assert all(isinstance(cmd, V4Command) for cmd in commands)

    gas_used = executor.execute_v4_keep_stream(commands, pools, seed)
    assert gas_used == _gas_for_v4_keep_stream(seed, len(commands))

    assert executor.gas_used > 0
    print(f"METRIC gas_used={gas_used}")


def test_v4_v4_v4_keep_stream_benchmark_sweep() -> None:
    """
    Run a small benchmark-style sweep over deterministic seeds and emit gas metrics.
    """
    for seed in (0, 1, 7):
        encoded, commands, pools, executor = _build_v4_keep_plan(seed)
        assert encoded.count(bytes([COMMAND_SEPARATOR])) == len(commands)
        gas_used = executor.execute_v4_keep_stream(commands, pools, seed)
        expected = _gas_for_v4_keep_stream(seed, len(commands))
        assert gas_used == expected
        print(f"METRIC seed={seed} gas_used={gas_used}")


def test_v4_v4_v4_keep_stream_shape() -> None:
    assert CMD_V4_SWAP == 1
    assert COMMAND_SEPARATOR == 0xFF
    seed = _seed_from_env()
    encoded, commands, _pools, _executor = _build_v4_keep_plan(seed)

    assert encoded.count(bytes([COMMAND_SEPARATOR])) == 3
    assert len(commands[0].recipient) == 42
    assert commands[0].recipient.startswith("0x")


def test_v4_v4_v4_keep_stream_malformed_stream_rejects() -> None:
    """
    Malformed V4 stream inputs must fail fast in parsing.
    """
    seed = _seed_from_env()
    encoded, _commands, _pools, _executor = _build_v4_keep_plan(seed)

    malformed_separator = bytearray(encoded)
    malformed_separator[-1] = 0x00
    with pytest.raises(AssertionError):
        parse_v4_commands(bytes(malformed_separator))

    malformed_command = bytearray(encoded)
    malformed_command[0] = 0xEE
    with pytest.raises(AssertionError):
        parse_v4_commands(bytes(malformed_command))


def test_v4_v4_v4_keep_stream_truncated_command_rejects() -> None:
    """
    Truncated command payloads should be rejected.
    """
    seed = _seed_from_env()
    encoded, _commands, _pools, _executor = _build_v4_keep_plan(seed)

    # remove 10 bytes from the tail to truncate the final field and separator.
    with pytest.raises(AssertionError):
        parse_v4_commands(encoded[:-10])

    # remove only the separator.
    with pytest.raises(AssertionError):
        parse_v4_commands(encoded[:-1])


def test_v4_v4_v4_keep_stream_rejects_int128_overflow() -> None:
    seed = _seed_from_env()
    _, _commands, _pools, _executor = _build_v4_keep_plan(seed)
    pool_addr = mk_addr(0xA200 + seed)
    recipient = mk_addr(0xA300 + seed)

    overflow_amount = MAX_INT128 + 1
    malformed = (
        bytes([CMD_V4_SWAP])
        + bytes.fromhex(pool_addr[2:])
        + bytes([1])
        + overflow_amount.to_bytes(32, "big")
        + bytes.fromhex(recipient[2:])
        + bytes([COMMAND_SEPARATOR])
    )

    with pytest.raises(AssertionError):
        parse_v4_commands(malformed)


def test_v4_v4_v4_keep_stream_rejects_invalid_zero_for_one_flag() -> None:
    seed = _seed_from_env()
    _, _commands, _pools, _executor = _build_v4_keep_plan(seed)
    pool_addr = mk_addr(0xD100 + seed)
    recipient = mk_addr(0xD200 + seed)

    malformed = (
        bytes([CMD_V4_SWAP])
        + bytes.fromhex(pool_addr[2:])
        + bytes([2])
        + (1).to_bytes(32, "big")
        + bytes.fromhex(recipient[2:])
        + bytes([COMMAND_SEPARATOR])
    )

    with pytest.raises(AssertionError):
        parse_v4_commands(malformed)


def test_parse_v4_callback_layers_rejects_invalid_zero_for_one_flag() -> None:
    malformed = (
        bytes.fromhex("ab" * 20)
        + bytes([2])
        + (123).to_bytes(8, "big")
    )
    with pytest.raises(AssertionError):
        parse_v4_callback_layers(malformed)


def test_mock_v4_pool_set_next_swap_rejects_int128_overflow() -> None:
    token_a = MockERC20("Token A", "TKA", 18, mk_addr(0xB001), {})
    token_b = MockERC20("Token B", "TKB", 18, mk_addr(0xB002), {})
    pool = MockV4Pool(token_a, token_b, mk_addr(0xB100))

    max_int128 = MAX_INT128
    pool.set_next_swap(max_int128, max_int128, True)

    with pytest.raises(AssertionError):
        pool.set_next_swap(max_int128 + 1, 1, True)

    with pytest.raises(AssertionError):
        pool.set_next_swap(1, max_int128 + 1, True)


def test_mock_v4_pool_swap_rejects_amount_specified_overflow() -> None:
    token_in = MockERC20("Token A", "TKA", 18, mk_addr(0xC100), {})
    token_out = MockERC20("Token B", "TKB", 18, mk_addr(0xC101), {})
    pool = MockV4Pool(token_in, token_out, mk_addr(0xC200))

    token_out.mint(pool.address, 1)
    pool.set_next_swap(1, 1, True)

    with pytest.raises(AssertionError):
        pool.swap(
            pool.address,
            True,
            MAX_INT128 + 1,
            b"",
            lambda *_args: None,
        )

    with pytest.raises(AssertionError):
        pool.swap(
            pool.address,
            True,
            -(MAX_INT128 + 1),
            b"",
            lambda *_args: None,
        )
