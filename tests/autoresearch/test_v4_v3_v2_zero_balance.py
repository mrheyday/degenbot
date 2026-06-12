from __future__ import annotations

import os
import pytest

from tests.autoresearch._fake_arbitrage_world import (
    MockERC20,
    MockExecutor,
    MockV2Pair,
    MockV3Pool,
    MockV4Pool,
    mk_addr,
)

ONE_WEI = 10**18


def _seed_from_env(default: int = 0) -> int:
    return int(os.getenv("AR_STREAM_SEED", str(default)))


def _encode_v4_layer(pool_addr: str, zero_for_one: bool, amount: int) -> bytes:
    return bytes.fromhex(pool_addr[2:]) + bytes([1 if zero_for_one else 0]) + amount.to_bytes(8, "big")


def _build_v4_v3_v2_zero_balance_world(seed: int):
    # Chain: V4(pool3) -> V3(pool2) -> V2(pool1), all in a zero-balance executor mode.
    owner = mk_addr(0xD300 + seed)
    executor_addr = mk_addr(0xD400 + seed)

    weth = MockERC20("Wrapped Ether", "WETH", 18, mk_addr(0xAAA), {})
    token_a = MockERC20("Token A", "TKA", 18, mk_addr(0xBBB), {})
    token_b = MockERC20("Token B", "TKB", 18, mk_addr(0xCCC), {})

    pool1_addr = mk_addr(0xD500 + seed)
    pool2_addr = mk_addr(0xD600 + seed)
    pool3_addr = mk_addr(0xD700 + seed)

    pool1 = MockV2Pair(weth, token_a, pool1_addr, swap_fee=30)
    pool2 = MockV3Pool(token_a, token_b, pool2_addr)
    pool3 = MockV4Pool(token_b, weth, pool3_addr)

    # WETH in -> Token A out -> Token B out -> WETH out
    token_a_out = 900_000_000_000_000
    token_b_out = 1_000_000_000_000_000
    weth_out = 2_100_000_000_000_000
    pay_amount = 1_000_000_000_000_000

    assert weth_out > pay_amount, "v4->v3->v2 should be profitable in gross terms"

    mint_size = 10_000 * ONE_WEI
    weth.mint(pool1.address, mint_size)
    token_a.mint(pool1.address, mint_size)
    token_a.mint(pool2.address, mint_size)
    token_b.mint(pool2.address, mint_size)
    token_b.mint(pool3.address, mint_size)
    weth.mint(pool3.address, weth_out)

    pool1.sync()

    pool2.set_next_swap(token_a_out, token_b_out, True)
    pool3.set_next_swap(token_b_out, weth_out, True)

    payload = _encode_v4_layer(pool2.address, True, token_b_out) + _encode_v4_layer(pool1.address, True, token_a_out)
    pools = {pool1.address: pool1, pool2.address: pool2, pool3.address: pool3}

    executor = MockExecutor(owner=owner, weth=weth, address=executor_addr)
    return executor, pool3, pools, payload, pay_amount, weth_out


def test_v4_v3_v2_zero_balance_arbitrage() -> None:
    seed = _seed_from_env()
    executor, pool3, pools, payload, pay_amount, output_amount = _build_v4_v3_v2_zero_balance_world(seed)
    pool1, pool2, _ = tuple(pools.values())

    expected_chain = [pool3.address, pool2.address, pool1.address]
    start_weth = executor.weth.balance_of(executor.address)
    assert start_weth == 0

    gas_used = executor.execute_v4_v3_v2_nested_arbitrage(
        pool3,
        pools,
        payload,
        seed,
        output_amounts=(0, output_amount),
        final_pay_amount=pay_amount,
        expected_callback_chain=expected_chain,
    )

    end_weth = executor.weth.balance_of(executor.address)
    gross_profit = end_weth - start_weth
    assert gross_profit > 0
    assert output_amount > pay_amount
    assert gas_used > 0
    assert executor._v4_callback_chain_active is False
    assert executor._v4_expected_callback_chain == []
    assert executor._v4_callback_step == 0
    assert executor.v4_callback_trace == expected_chain


def test_v4_v3_v2_zero_balance_metric() -> None:
    seed = _seed_from_env()
    executor, pool3, pools, payload, pay_amount, output_amount = _build_v4_v3_v2_zero_balance_world(seed)
    pool1, pool2, _ = tuple(pools.values())

    expected_chain = [pool3.address, pool2.address, pool1.address]
    start_weth = executor.weth.balance_of(executor.address)
    gas_used = executor.execute_v4_v3_v2_nested_arbitrage(
        pool3,
        pools,
        payload,
        seed,
        output_amounts=(0, output_amount),
        final_pay_amount=pay_amount,
        expected_callback_chain=expected_chain,
    )
    end_weth = executor.weth.balance_of(executor.address)

    gross_profit = end_weth - start_weth
    print("\n  V4→V3→V2 zero-balance nested arbitrage metric")
    print(f"    WETH in (pool1):   {pay_amount / ONE_WEI:.6f}")
    print(f"    WETH out (pool3):  {output_amount / ONE_WEI:.6f}")
    print(f"    Ending WETH:       {end_weth / ONE_WEI:.6f}")
    print(f"    Gross profit:      {gross_profit / ONE_WEI:.6f} WETH")
    print(f"    Gas used:          {gas_used}")
    print(f"METRIC gas_used={gas_used}")


def test_v4_v3_v2_zero_balance_access_control() -> None:
    seed = _seed_from_env()
    executor, pool3, pools, payload, pay_amount, output_amount = _build_v4_v3_v2_zero_balance_world(seed)
    pool1, pool2, _ = tuple(pools.values())

    expected_chain = [pool3.address, pool2.address, pool1.address]
    wrong_chain = [expected_chain[1], expected_chain[0], expected_chain[2]]

    assert executor.address != pool1.address
    gas_used = executor.execute_v4_v3_v2_nested_arbitrage(
        pool3,
        pools,
        payload,
        seed,
        output_amounts=(0, output_amount),
        final_pay_amount=pay_amount,
        expected_callback_chain=expected_chain,
    )
    assert gas_used > 0
    assert executor.v4_callback_trace == expected_chain

    with pytest.raises(AssertionError):
        executor.execute_v4_v3_v2_nested_arbitrage(
            pool3,
            pools,
            payload,
            seed,
            output_amounts=(0, output_amount),
            final_pay_amount=pay_amount,
            expected_callback_chain=wrong_chain,
        )
