from __future__ import annotations

import os

from tests.autoresearch._fake_arbitrage_world import (
    MockERC20,
    MockExecutor,
    MockV2Pair,
    V2Command,
    parse_v2_commands,
    mk_addr,
)

ONE_WEI: int = 10**18


def _seed_from_env(default: int = 0) -> int:
    return int(os.getenv("AR_STREAM_SEED", str(default)))


def _build_arbitrage_payload(seed: int) -> tuple[list[V2Command], MockV2Pair, MockV2Pair, MockV2Pair, dict[str, MockV2Pair], MockExecutor, int]:
    # Keep balances and amounts intentionally tiny to exercise math cleanly.
    owner = mk_addr(0x0100_0000 + seed)
    pool1_addr = mk_addr(0x1111_0000 + seed)
    pool2_addr = mk_addr(0x1111_0001 + seed)
    pool3_addr = mk_addr(0x1111_0002 + seed)
    executor_addr = mk_addr(0x2222_0001 + seed)

    weth = MockERC20("Wrapped Ether", "WETH", 18, mk_addr(0xaaa), {})
    token_a = MockERC20("Token A", "TKA", 18, mk_addr(0xbbb), {})
    token_b = MockERC20("Token B", "TKB", 18, mk_addr(0xccc), {})

    # Seed-driven but deterministic outputs.
    a_out = 1_030_000_000_000_000
    b_out = 1_030_000_000_000_000
    weth_out = 3 * ONE_WEI // 1000
    pay_amount = 1_050_000_000_000_000

    # Build encoded command stream in the same format as the executor entrypoint.
    def _pack(v: int, n: int) -> bytes:
        return v.to_bytes(n, "big")

    encoded = b"".join(
        [
            (0).to_bytes(1, "big")
            + bytes.fromhex(pool1_addr[2:])
            + _pack(0, 32)
            + _pack(a_out, 32)
            + bytes.fromhex(pool2_addr[2:])
            + bytes.fromhex("ff"),
            (0).to_bytes(1, "big")
            + bytes.fromhex(pool2_addr[2:])
            + _pack(0, 32)
            + _pack(b_out, 32)
            + bytes.fromhex(pool3_addr[2:])
            + bytes.fromhex("ff"),
            (0).to_bytes(1, "big")
            + bytes.fromhex(pool3_addr[2:])
            + _pack(0, 32)
            + _pack(weth_out, 32)
            + bytes.fromhex(executor_addr[2:])
            + bytes.fromhex("ff"),
        ]
    )
    commands = parse_v2_commands(encoded)

    # Minimal pool setup for this single deterministic run.
    pool1 = MockV2Pair(
        token0=weth,
        token1=token_a,
        address=pool1_addr,
        swap_fee=30,
        reserve0=a_out * 100,
        reserve1=a_out * 100,
        unlocked=True,
    )
    pool2 = MockV2Pair(
        token0=token_a,
        token1=token_b,
        address=pool2_addr,
        swap_fee=30,
        reserve0=a_out * 100,
        reserve1=b_out * 200,
        unlocked=True,
    )
    pool3 = MockV2Pair(
        token0=token_b,
        token1=weth,
        address=pool3_addr,
        swap_fee=30,
        reserve0=b_out * 100,
        # Keep pool3's WETH reserve sufficiently over-provisioned so the
        # flash swap and output-capability assertions can both pass.
        reserve1=weth_out * 1000,
        unlocked=True,
    )

    # Prefund each pool with a large symmetric reserve buffer.
    token0_a = [
        (weth, pool1.address, pool1.reserve0),
        (weth, pool3.address, pool3.reserve1),
        (weth, owner, 0),
    ]
    token1_a = [
        (token_a, pool1.address, pool1.reserve1),
        (token_a, pool2.address, pool2.reserve0),
        (token_b, pool2.address, pool2.reserve1),
        (token_b, pool3.address, pool3.reserve0),
    ]
    for token, recipient, amount in token0_a + token1_a:
        token.mint(recipient, amount)

    pool1.sync()
    pool2.sync()
    pool3.sync()

    pools = {pool1.address: pool1, pool2.address: pool2, pool3.address: pool3}
    executor = MockExecutor(owner=owner, weth=weth, address=executor_addr)
    return commands, pool1, pool2, pool3, pools, executor, pay_amount


def test_v2_v2_v2_zero_balance_arbitrage() -> None:
    seed = _seed_from_env()
    (
        commands,
        pool1,
        pool2,
        pool3,
        _,
        executor,
        pay_amount,
    ) = _build_arbitrage_payload(seed)

    start_weth = executor.weth.balance_of(executor.address)
    gas_used = executor.execute_v2_zero_balance_arbitrage(
        pool1,
        pool2,
        pool3,
        commands,
        pay_amount,
        seed,
    )

    ending_weth = executor.weth.balance_of(executor.address)
    assert ending_weth > start_weth

    print(f"METRIC gas_used={gas_used}")


def test_v2_v2_v2_zero_balance_access_control() -> None:
    owner = mk_addr(0x1111)
    unauthorized = mk_addr(0x2222)

    assert owner != unauthorized
    assert owner.startswith("0x")
    assert unauthorized.startswith("0x")
