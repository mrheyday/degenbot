"""Unit tests for DodoPmmPool (real implementation, replacing forward stub).

Phase F.3 promotion (2026-05-12): DexKind 12 standalone pool class
wrapping audited `dodo_pmm_math` primitives. Inherits PublisherMixin +
AbstractLiquidityPool to drop into degenbot's pool taxonomy.
"""

from __future__ import annotations

import pytest
from degenbot.execution.dodo_pmm_adapter import (
    DodoPmmPool,
    DodoPmmPoolState,
    PmmState,
    RState,
)

from degenbot.registry import pool_registry

ARBITRUM_CHAIN_ID = 42161
ONE = 10**18

# Test tokens — checksum addresses on Arbitrum One.
_BASE = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"  # USDC (base)
_QUOTE = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"  # WETH (quote)
_POOL = "0x0000000000000000000000000000000000002001"


def _balanced_pmm_state() -> PmmState:
    """R=ONE state: B == B0, Q == Q0. Mirrors `_base_state()` from
    `test_dodo_pmm_math.py:25-34` so the audited expected values
    transfer 1:1 (B=100·ONE, Q=200_000·ONE, K=0.1, i=2000·ONE)."""
    return PmmState(
        i=2_000 * ONE,
        K=ONE // 10,  # K = 0.1
        B=100 * ONE,
        Q=200_000 * ONE,
        B0=100 * ONE,
        Q0=200_000 * ONE,
        R=RState.ONE,
    )


def _make_pool(**overrides: object) -> DodoPmmPool:
    defaults: dict[str, object] = {
        "address": _POOL,
        "base_token": _BASE,
        "quote_token": _QUOTE,
        "pmm": _balanced_pmm_state(),
        "lp_fee_bps_wad": 0,
        "maintainer_fee_bps_wad": 0,
        "state_block": 1_000,
    }
    defaults.update(overrides)
    return DodoPmmPool(**defaults)  # type: ignore[arg-type]


class TestDodoPmmPoolConstructor:
    def test_constructs_balanced(self) -> None:
        p = _make_pool()
        assert p.address.lower() == _POOL.lower()
        assert isinstance(p.state, DodoPmmPoolState)
        assert p.state.pmm.R == RState.ONE
        assert "DodoPmmPool" in p.name
        assert "R=ONE" in p.name

    def test_state_cache_seeded(self) -> None:
        p = _make_pool()
        assert len(p._state_cache) == 1

    def test_rejects_lp_fee_at_or_above_100pct(self) -> None:
        with pytest.raises(ValueError, match="lp_fee_bps_wad"):
            _make_pool(lp_fee_bps_wad=10**18)
        with pytest.raises(ValueError, match="lp_fee_bps_wad"):
            _make_pool(lp_fee_bps_wad=-1)

    def test_rejects_combined_fees_over_100pct(self) -> None:
        with pytest.raises(ValueError, match="combined fees"):
            _make_pool(
                lp_fee_bps_wad=6 * 10**17,
                maintainer_fee_bps_wad=5 * 10**17,
            )


class TestDodoPmmPoolSimulation:
    def test_r_one_sell_base_matches_audited_math(self) -> None:
        # Locked by test_dodo_pmm_math.py:
        # sell_base_token(state, ONE) == (1_997_983_889_406_409_944_695, RState.BELOW_ONE)
        p = _make_pool()
        out = p.calculate_tokens_out_from_tokens_in(_BASE, ONE)
        assert out == 1_997_983_889_406_409_944_695

    def test_r_one_sell_quote_matches_audited_math(self) -> None:
        # sell_quote_token(state, 2_000 * ONE) == (998_991_944_703_204_972, RState.ABOVE_ONE)
        p = _make_pool()
        out = p.calculate_tokens_out_from_tokens_in(_QUOTE, 2_000 * ONE)
        assert out == 998_991_944_703_204_972

    def test_lp_fee_deducts_after_curve_math(self) -> None:
        # 0.5% LP fee.
        p = _make_pool(lp_fee_bps_wad=5 * 10**15)
        gross = 1_997_983_889_406_409_944_695
        expected_fee = (gross * 5 * 10**15) // 10**18
        net = p.calculate_tokens_out_from_tokens_in(_BASE, ONE)
        assert net == gross - expected_fee

    def test_combined_lp_and_maintainer_fee(self) -> None:
        p = _make_pool(
            lp_fee_bps_wad=3 * 10**15,
            maintainer_fee_bps_wad=2 * 10**15,
        )
        gross = 1_997_983_889_406_409_944_695
        lp = (gross * 3 * 10**15) // 10**18
        maintainer = (gross * 2 * 10**15) // 10**18
        net = p.calculate_tokens_out_from_tokens_in(_BASE, ONE)
        assert net == gross - lp - maintainer

    def test_rejects_zero_quantity(self) -> None:
        p = _make_pool()
        with pytest.raises(ValueError, match="must be positive"):
            p.calculate_tokens_out_from_tokens_in(_BASE, 0)

    def test_rejects_unknown_token(self) -> None:
        p = _make_pool()
        with pytest.raises(ValueError, match="matches neither"):
            p.calculate_tokens_out_from_tokens_in(
                "0x0000000000000000000000000000000000000001",
                ONE,
            )

    def test_override_state_does_not_mutate_pool(self) -> None:
        p = _make_pool()
        deep_pmm = PmmState(
            i=2_000 * ONE,
            K=ONE // 10,
            B=1_000 * ONE,
            Q=2_000_000 * ONE,
            B0=1_000 * ONE,
            Q0=2_000_000 * ONE,
            R=RState.ONE,
        )
        override = DodoPmmPoolState(
            address=p.address,
            block=p.state.block,
            pmm=deep_pmm,
        )
        out_default = p.calculate_tokens_out_from_tokens_in(_BASE, ONE)
        out_override = p.calculate_tokens_out_from_tokens_in(
            _BASE,
            ONE,
            override_state=override,
        )
        # Deeper pool (10x reserves) ⇒ less slippage ⇒ more out.
        assert out_override > out_default
        # State unchanged.
        assert p.state.pmm.B == 100 * ONE


class TestDodoPmmPoolUpdate:
    def test_update_state_advances_cache(self) -> None:
        p = _make_pool()
        block = p.state.block
        assert block is not None
        new_pmm = PmmState(
            i=2_000 * ONE,
            K=ONE // 10,
            B=110 * ONE,
            Q=220_000 * ONE,
            B0=110 * ONE,
            Q0=220_000 * ONE,
            R=RState.ONE,
        )
        new_state = p.update_state(pmm=new_pmm, block=block + 1)
        assert p.state == new_state
        assert len(p._state_cache) == 2

    def test_past_block_update_rejected(self) -> None:
        p = _make_pool()
        with pytest.raises(ValueError, match="predates"):
            p.update_state(
                pmm=_balanced_pmm_state(),
                block=(p.state.block or 0) - 1,
            )


class TestDodoPmmPoolRegistry:
    def test_self_registers_with_chain_id(self) -> None:
        addr = "0x0000000000000000000000000000000000002099"
        p = _make_pool(address=addr, chain_id=ARBITRUM_CHAIN_ID)
        resolved = pool_registry.get(
            chain_id=ARBITRUM_CHAIN_ID,
            pool_address=addr,
        )
        assert resolved is p
        pool_registry.remove(chain_id=ARBITRUM_CHAIN_ID, pool_address=addr)

    def test_skips_registry_without_chain_id(self) -> None:
        addr = "0x0000000000000000000000000000000000002098"
        _make_pool(address=addr)
        assert pool_registry.get(chain_id=ARBITRUM_CHAIN_ID, pool_address=addr) is None
