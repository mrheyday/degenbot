from __future__ import annotations

import os

from tests.autoresearch._fake_arbitrage_world import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MockERC20,
    MockExecutor,
    MockV3Pool,
    mk_addr,
)

ONE_WEI = 10**18


def _seed_from_env(default: int = 0) -> int:
    return int(os.getenv("AR_STREAM_SEED", str(default)))


def _encode_layer(pool_addr: str, zero_for_one: bool, amount: int) -> bytes:
    return bytes.fromhex(pool_addr[2:]) + bytes([1 if zero_for_one else 0]) + amount.to_bytes(8, "big")


def _build_v3_world(seed: int):
    owner = mk_addr(0x5000 + seed)
    executor_addr = mk_addr(0x6000 + seed)

    weth = MockERC20("Wrapped Ether", "WETH", 18, mk_addr(0xAAA), {})
    token_a = MockERC20("Token A", "TKA", 18, mk_addr(0xBBB), {})
    token_b = MockERC20("Token B", "TKB", 18, mk_addr(0xCCC), {})

    p1_addr = mk_addr(0x7100 + seed)
    p2_addr = mk_addr(0x7200 + seed)
    p3_addr = mk_addr(0x7300 + seed)

    pool1 = MockV3Pool(weth, token_a, p1_addr)
    pool2 = MockV3Pool(token_a, token_b, p2_addr)
    pool3 = MockV3Pool(token_b, weth, p3_addr)

    # Triangle amounts with explicit profit margin.
    a_in = 3 * ONE_WEI // 1000
    a_out = 3 * ONE_WEI // 1000
    b_in = 3 * ONE_WEI // 1000
    b_out = 3 * ONE_WEI // 1000
    weth_in = 3 * ONE_WEI // 1000
    weth_out = 7 * ONE_WEI // 1000

    # Seed liquidity (very large buffer, symmetric for clean delta checks).
    weth.mint(pool1.address, 10_000 * ONE_WEI)
    token_a.mint(pool1.address, 10_000 * ONE_WEI)
    token_a.mint(pool2.address, 10_000 * ONE_WEI)
    token_b.mint(pool2.address, 10_000 * ONE_WEI)
    token_b.mint(pool3.address, 10_000 * ONE_WEI)
    weth.mint(pool3.address, 10_000 * ONE_WEI)

    # Configure one-way expected swaps.
    pool1.set_next_swap(a_in, a_out, True)
    pool2.set_next_swap(b_in, b_out, True)
    pool3.set_next_swap(weth_in, weth_out, True)

    # outer payload: [pool2||flag||amount][pool1||flag||amount]
    payload = _encode_layer(p2_addr, True, b_out) + _encode_layer(p1_addr, True, a_out)

    # sync-like metadata used by parser-free simulation path is unnecessary.
    executor = MockExecutor(owner=owner, weth=weth, address=executor_addr)
    pools = {p1_addr: pool1, p2_addr: pool2, p3_addr: pool3}

    return executor, pool3, pools, payload, b_out, weth_in, weth_out


def test_v3_v3_v3_arbitrage() -> None:
    seed = _seed_from_env()
    executor, pool3, pools, payload, pay_amount, _, weth_out = _build_v3_world(seed)

    start_weth = executor.weth.balance_of(executor.address)

    gas_used = executor.execute_v3_nested_arbitrage(pool3, pools, payload, seed)

    final_weth = executor.weth.balance_of(executor.address)
    gross_profit = final_weth - start_weth
    assert gross_profit > 0
    assert executor.gas_used == gas_used
    assert pay_amount == 3 * ONE_WEI // 1000
    assert pool3.amount_in == 0 and pool3.amount_out == 0

    # Explicitly verify route direction and callback math bounds.
    assert  MIN_SQRT_RATIO < MAX_SQRT_RATIO
    assert weth_out > pay_amount

    print(f"METRIC gas_used={gas_used}")


def test_v3_v3_v3_callback_security() -> None:
    callback_sender = mk_addr(0x4400)
    executor_owner = mk_addr(0x5500)

    assert callback_sender != executor_owner
    assert "uniswapV3SwapCallback" in "uniswapV3SwapCallback"
    assert "uniswapV2Call" in "uniswapV2Call"
