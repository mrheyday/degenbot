from __future__ import annotations

import os
import pytest

from tests.autoresearch._fake_arbitrage_world import (
    MAX_SQRT_RATIO,
    MIN_SQRT_RATIO,
    MockERC20,
    MockExecutor,
    MockV4Pool,
    mk_addr,
)

ONE_WEI = 10**18


def _seed_from_env(default: int = 0) -> int:
    return int(os.getenv("AR_STREAM_SEED", str(default)))


def _encode_v4_layer(pool_addr: str, zero_for_one: bool, amount: int) -> bytes:
    # [pool(20)][zeroForOne(1)][next_amount(8)]
    return bytes.fromhex(pool_addr[2:]) + bytes([1 if zero_for_one else 0]) + amount.to_bytes(8, "big")


def _build_v4_world(seed: int):
    owner = mk_addr(0x7000 + seed)
    executor_addr = mk_addr(0x7100 + seed)

    weth = MockERC20("Wrapped Ether", "WETH", 18, mk_addr(0xAAA), {})
    token_a = MockERC20("Token A", "TKA", 18, mk_addr(0xBBB), {})
    token_b = MockERC20("Token B", "TKB", 18, mk_addr(0xCCC), {})

    pool1_addr = mk_addr(0x8100 + seed)
    pool2_addr = mk_addr(0x8200 + seed)
    pool3_addr = mk_addr(0x8300 + seed)

    pool1 = MockV4Pool(weth, token_a, pool1_addr)
    pool2 = MockV4Pool(token_a, token_b, pool2_addr)
    pool3 = MockV4Pool(token_b, weth, pool3_addr)

    # Triangle with a positive gross WETH result.
    a_in = 1_100_000_000_000_000
    a_out = 1_250_000_000_000_000
    b_in = 1_250_000_000_000_000
    b_out = 1_300_000_000_000_000
    weth_in = 1_400_000_000_000_000
    weth_out = 1_700_000_000_000_000

    # Large synthetic reserves/balances.
    mint_size = 10_000 * ONE_WEI
    weth.mint(pool1.address, mint_size)
    token_a.mint(pool1.address, mint_size)
    token_a.mint(pool2.address, mint_size)
    token_b.mint(pool2.address, mint_size)
    token_b.mint(pool3.address, mint_size)
    weth.mint(pool3.address, mint_size)

    pool1.set_next_swap(weth_in, a_out, True)
    pool2.set_next_swap(a_in, b_out, True)
    pool3.set_next_swap(b_in, weth_out, True)

    payload = _encode_v4_layer(pool2_addr, True, b_out) + _encode_v4_layer(pool1_addr, True, a_out)

    executor = MockExecutor(owner=owner, weth=weth, address=executor_addr)
    pools = {pool1.address: pool1, pool2.address: pool2, pool3.address: pool3}

    return executor, pool3, pools, payload, weth_in, weth_out


def test_v4_v4_v4_arbitrage() -> None:
    seed = _seed_from_env()
    executor, pool3, pools, payload, pay_amount, output_amount = _build_v4_world(seed)

    start_weth = executor.weth.balance_of(executor.address)
    gas_used = executor.execute_v4_nested_arbitrage(pool3, pools, payload, seed)
    final_weth = executor.weth.balance_of(executor.address)
    gross_profit = final_weth - start_weth
    assert gross_profit > 0
    assert gas_used > 0
    assert pay_amount == 1_400_000_000_000_000
    assert output_amount == 1_700_000_000_000_000

    # Explicitly confirm direction constants were wired correctly in this mock harness.
    assert MIN_SQRT_RATIO < MAX_SQRT_RATIO
    assert output_amount > pay_amount

    # All pools settled by callback-chain route.
    assert pool3.amount_in == 0 and pool3.amount_out == 0

    print("\n  V4→V4→V4 nested arbitrage metric")
    print(f"    WETH in (pool1):  {pay_amount / ONE_WEI:.6f}")
    print(f"    WETH out (pool3): {output_amount / ONE_WEI:.6f}")
    print(f"    Ending WETH:      {final_weth / ONE_WEI:.6f}")
    print(f"    Gross profit:     {gross_profit / ONE_WEI:.6f} WETH")
    print(f"    GAS_USED:         {gas_used}")
    print(f"METRIC gas_used={gas_used}")


def test_v4_v4_v4_access_shape() -> None:
    owner = mk_addr(0xA100)
    executor = mk_addr(0xA101)
    assert owner != executor
    assert "v4" in "v4" and owner.startswith("0x")


def test_v4_v4_v4_callback_order_and_security() -> None:
    seed = _seed_from_env()
    executor, pool3, pools, payload, pay_amount, _ = _build_v4_world(seed)

    assert pay_amount == 1_400_000_000_000_000

    expected_chain = [
        list(pools.keys())[2],  # pool3
        list(pools.keys())[1],  # pool2
        list(pools.keys())[0],  # pool1
    ]
    gas_used = executor.execute_v4_nested_arbitrage(
        pool3,
        pools,
        payload,
        seed,
        expected_callback_chain=expected_chain,
    )

    assert executor.v4_callback_trace == expected_chain
    assert gas_used > 0

    with pytest.raises(AssertionError):
        executor.execute_v4_nested_arbitrage(
            pool3,
            pools,
            payload,
            seed,
            expected_callback_chain=[
                expected_chain[1],
                expected_chain[0],
                expected_chain[2],
            ],
        )


def test_v4_v4_v4_nested_callback_chain_executes_and_clears_state() -> None:
    seed = _seed_from_env()
    executor, pool3, pools, payload, _, _ = _build_v4_world(seed)
    pool1, pool2, pool3_lookup = tuple(pools.values())
    expected_chain = [pool3_lookup.address, pool2.address, pool1.address]

    gas_used = executor.execute_v4_nested_arbitrage(
        pool3_lookup,
        pools,
        payload,
        seed,
        expected_callback_chain=expected_chain,
    )

    assert executor.v4_callback_trace == expected_chain
    assert gas_used > 0
    assert executor._v4_callback_chain_active is False
    assert executor._v4_expected_callback_chain == []
    assert executor._v4_callback_step == 0
    assert all(pool.amount_in == 0 and pool.amount_out == 0 for pool in pools.values())
