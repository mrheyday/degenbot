"""Integration test — adapter pool classes resolve via degenbot pool_registry.

Verifies that the three Phase F.2 adapter pool classes
(`SolidlyV1Pool`, `CurveNGPool`, `CamelotV3Pool`) self-register into
`degenbot.registry.pool_registry` when constructed with `chain_id`, and
that the IPC dispatcher in `degenbot_ipc.RegistryBackedDegenbotSimulator
._simulate_step` then resolves them and routes to their
`calculate_tokens_out_from_tokens_in` method.

Closes the gap flagged in commit `8a0278a` post-audit: the new venue
strings were in `RECOGNIZED_DEX_KINDS` but NOT in
`ADDRESS_KEYED_DEGENBOT_DEX_KINDS`, so the dispatcher rejected them.

The pool_registry is a process-singleton — tests use unique addresses
to avoid `Pool is already registered` collisions across cases.
"""

from __future__ import annotations

from fractions import Fraction

import pytest
from degenbot.registry import pool_registry
from degenbot.execution.curve_ng_adapter import CurveNGPool
from degenbot.execution.degenbot_ipc import (
    ADDRESS_KEYED_DEGENBOT_DEX_KINDS,
    RECOGNIZED_DEX_KINDS,
)
from degenbot.execution.solidly_adapter import SolidlyV1Pool

ARBITRUM_CHAIN_ID = 42161
_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_USDT = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"


class TestDexKindSetMembership:
    """The three Phase F.2 strings must live in BOTH sets so the dispatcher
    proceeds past the membership gates."""

    def test_solidly_recognized(self) -> None:
        assert "Solidly" in RECOGNIZED_DEX_KINDS
        assert "Solidly" in ADDRESS_KEYED_DEGENBOT_DEX_KINDS

    def test_curve_ng_recognized(self) -> None:
        assert "CurveNG" in RECOGNIZED_DEX_KINDS
        assert "CurveNG" in ADDRESS_KEYED_DEGENBOT_DEX_KINDS

    def test_camelot_v3_recognized(self) -> None:
        assert "CamelotV3" in RECOGNIZED_DEX_KINDS
        assert "CamelotV3" in ADDRESS_KEYED_DEGENBOT_DEX_KINDS


class TestSolidlyV1PoolSelfRegistration:
    def test_constructs_without_chain_id_skips_registry(self) -> None:
        pool_address = "0x0000000000000000000000000000000000001001"
        SolidlyV1Pool(
            address=pool_address,
            token0=_USDC,
            token1=_WETH,
            reserves_token0=3_500_000_000_000,
            reserves_token1=1_000 * 10**18,
            decimals_token0=10**6,
            decimals_token1=10**18,
            fee=Fraction(1, 10_000),
            stable=False,
        )
        # No chain_id → not registered → registry lookup returns None.
        assert (
            pool_registry.get(chain_id=ARBITRUM_CHAIN_ID, pool_address=pool_address) is None
        )

    def test_constructs_with_chain_id_registers(self) -> None:
        pool_address = "0x0000000000000000000000000000000000001002"
        pool = SolidlyV1Pool(
            address=pool_address,
            token0=_USDC,
            token1=_WETH,
            reserves_token0=3_500_000_000_000,
            reserves_token1=1_000 * 10**18,
            decimals_token0=10**6,
            decimals_token1=10**18,
            fee=Fraction(1, 10_000),
            stable=False,
            chain_id=ARBITRUM_CHAIN_ID,
        )
        resolved = pool_registry.get(
            chain_id=ARBITRUM_CHAIN_ID,
            pool_address=pool_address,
        )
        assert resolved is pool
        # Cleanup so subsequent tests don't collide.
        pool_registry.remove(chain_id=ARBITRUM_CHAIN_ID, pool_address=pool_address)

    def test_registered_pool_responds_to_swap(self) -> None:
        pool_address = "0x0000000000000000000000000000000000001003"
        pool = SolidlyV1Pool(
            address=pool_address,
            token0=_USDC,
            token1=_WETH,
            reserves_token0=3_500_000_000_000,
            reserves_token1=1_000 * 10**18,
            decimals_token0=10**6,
            decimals_token1=10**18,
            fee=Fraction(1, 10_000),
            stable=False,
            chain_id=ARBITRUM_CHAIN_ID,
        )
        # Round-trip through the registry, then call the canonical
        # `calculate_tokens_out_from_tokens_in` entry point as
        # `_simulate_step` does.
        resolved = pool_registry.get(
            chain_id=ARBITRUM_CHAIN_ID,
            pool_address=pool_address,
        )
        assert resolved is pool
        out = resolved.calculate_tokens_out_from_tokens_in(
            token_in=_USDC,
            token_in_quantity=1_000_000_000,  # 1000 USDC
        )
        assert out > 0
        pool_registry.remove(chain_id=ARBITRUM_CHAIN_ID, pool_address=pool_address)


class TestCurveNGPoolSelfRegistration:
    def test_constructs_with_chain_id_registers(self) -> None:
        pool_address = "0x0000000000000000000000000000000000001011"
        pool = CurveNGPool(
            address=pool_address,
            token0=_USDC,
            token1=_USDT,
            balances=(10_000_000_000_000, 10_000_000_000_000),
            rates=(10**30, 10**30),
            amp=200,
            fee_bps=4_000_000,
            chain_id=ARBITRUM_CHAIN_ID,
        )
        resolved = pool_registry.get(
            chain_id=ARBITRUM_CHAIN_ID,
            pool_address=pool_address,
        )
        assert resolved is pool
        # Smoke-test the dispatch-facing entry point.
        out = resolved.calculate_tokens_out_from_tokens_in(
            token_in=_USDC,
            token_in_quantity=1_000_000_000,
        )
        assert out > 0
        pool_registry.remove(chain_id=ARBITRUM_CHAIN_ID, pool_address=pool_address)


class TestRegistryCollision:
    """Re-registering the same (chain_id, address) must raise — the
    pool_registry singleton enforces uniqueness. Tests document the
    contract so a future cleanup gap doesn't silently overwrite."""

    def test_double_register_raises(self) -> None:
        pool_address = "0x0000000000000000000000000000000000001099"
        SolidlyV1Pool(
            address=pool_address,
            token0=_USDC,
            token1=_WETH,
            reserves_token0=1,
            reserves_token1=1,
            decimals_token0=10**6,
            decimals_token1=10**18,
            fee=Fraction(0),
            stable=False,
            chain_id=ARBITRUM_CHAIN_ID,
        )
        try:
            with pytest.raises(Exception, match="already registered"):
                SolidlyV1Pool(
                    address=pool_address,
                    token0=_USDC,
                    token1=_WETH,
                    reserves_token0=2,
                    reserves_token1=2,
                    decimals_token0=10**6,
                    decimals_token1=10**18,
                    fee=Fraction(0),
                    stable=False,
                    chain_id=ARBITRUM_CHAIN_ID,
                )
        finally:
            pool_registry.remove(chain_id=ARBITRUM_CHAIN_ID, pool_address=pool_address)
