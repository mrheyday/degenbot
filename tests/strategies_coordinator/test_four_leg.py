"""Unit tests for the ported four-leg cross-protocol composition strategy (Pick B)."""

import time
from unittest.mock import MagicMock

import pytest

from degenbot.adapters.config import Settings
from degenbot.decision.types import Hex
from degenbot.strategies_coordinator.four_leg import (
    FourLegPlan,
    FourLegStrategy,
)
from degenbot.strategies_coordinator.types import (
    DEX_KIND,
)
from degenbot.strategies_coordinator.types import (
    SwapStep as ContractSwapStep,
)
from degenbot.types_solver.executor import DexKind, FlashProtocol
from degenbot.types_solver.executor import SwapStep as EngineSwapStep
from degenbot.types_solver.wire import Opportunity

# Mock addresses
_EXECUTOR_ADDR = "0x" + "e" * 40
_ARB_AAVE_POOL = "0x794a61358d6845594f94dc1db02a252b5b4814ad"
_ARB_MORPHO_BLUE = "0x6c247b1f6182318877311737bac0844baa518f5e"
_WETH = "0x" + "1" * 40
_USDC = "0x" + "2" * 40


@pytest.fixture
def fake_settings() -> Settings:
    settings = MagicMock(spec=Settings)
    settings.executor_address = _EXECUTOR_ADDR
    settings.aave_v3_pool = _ARB_AAVE_POOL
    settings.morpho_blue = _ARB_MORPHO_BLUE
    return settings


@pytest.fixture
def sample_swap() -> ContractSwapStep:
    return ContractSwapStep(
        dex_kind=DEX_KIND.V2,
        router=_EXECUTOR_ADDR,
        call_data=Hex("0xdeadbeef"),
        token_in=_WETH,
        token_out=_USDC,
        amount_in=10**18,
        amount_out_min=3500 * 10**6,
    )


@pytest.fixture
def sample_plan(sample_swap) -> FourLegPlan:
    return FourLegPlan(
        opportunity_id="01HZK_TEST",
        across_fill_calldata=Hex("0xa1a1"),
        arb_swaps=[sample_swap],
        cow_fill_calldata=Hex("0xc2c2"),
        uniswapx_rebalance_calldata=Hex("0xc3c3"),
        flash_token=_WETH,
        flash_amount=10**18,
        expected_profit_wei=10**15,
    )


@pytest.fixture
def sample_opp() -> Opportunity:
    return Opportunity(
        id="01HZK_TEST",
        kind="NativeArb",
        tokenIn=_WETH,
        tokenOut=_USDC,
        amountIn=10**18,
        estimatedProfitWei=10**15,
        flashToken=_WETH,
        flashAmount=10**18,
        path=[],
        poolAddresses=[],
        detectedAtNs=1700000000000000000,
    )


def test_four_leg_preflight_none(fake_settings, sample_opp):
    strategy = FourLegStrategy(fake_settings)
    out = strategy.preflight(sample_opp)
    assert out is None


def test_four_leg_preflight_with_hint(fake_settings, sample_opp, sample_swap):
    # Attach hint to opp
    opp = Opportunity(
        **{
            **sample_opp.model_dump(),
            "enrichment": {
                "four_leg_hint": {
                    "across_fill_calldata": "0xa1a1",
                    "cow_fill_calldata": "0xc2c2",
                    "uniswapx_rebalance_calldata": "0xc3c3",
                    "arb_swaps": [sample_swap],
                }
            },
        }
    )

    strategy = FourLegStrategy(fake_settings)
    out = strategy.preflight(opp)

    assert out is not None
    assert out.opportunity_id == "01HZK_TEST"
    assert out.across_fill_calldata == "0xa1a1"
    assert len(out.arb_swaps) == 1


def test_four_leg_build_params(fake_settings, sample_plan):
    strategy = FourLegStrategy(fake_settings)
    params = strategy.build_params(sample_plan)

    assert params.flash_protocol == FlashProtocol.AAVE_V3
    assert params.flash_lender.lower() == _ARB_AAVE_POOL.lower()
    assert params.min_profit == int(sample_plan.expected_profit_wei * 0.95)
    assert params.deadline > int(time.time())


def test_four_leg_build_params_morpho(fake_settings, sample_plan):
    strategy = FourLegStrategy(fake_settings)
    plan = sample_plan
    # Manually set flash_protocol for test
    from dataclasses import replace

    plan = replace(plan, flash_protocol=FlashProtocol.MORPHO)

    params = strategy.build_params(plan)
    assert params.flash_protocol == FlashProtocol.MORPHO
    assert params.flash_lender.lower() == _ARB_MORPHO_BLUE.lower()


def test_four_leg_preflight_dynamic_mapping(fake_settings, sample_opp):
    opp = Opportunity(
        **{
            **sample_opp.model_dump(),
            "enrichment": {
                "four_leg_hint": {
                    "across_fill_calldata": "0xa1a1",
                    "cow_fill_calldata": "0xc2c2",
                    "uniswapx_rebalance_calldata": "0xc3c3",
                }
            },
            "path": [
                EngineSwapStep(
                    dex_kind=DexKind.UNI_V3_POOL,
                    router=_EXECUTOR_ADDR,
                    call_data=Hex("0x"),
                    token_in=_WETH,
                    token_out=_USDC,
                    amount_in=10**18,
                    amount_out_min=3500 * 10**6,
                )
            ],
        }
    )

    strategy = FourLegStrategy(fake_settings)
    out = strategy.preflight(opp)

    assert out is not None
    assert out.arb_swaps[0].dex_kind == DEX_KIND.V3


def test_four_leg_validation_gates(fake_settings, sample_plan):
    strategy = FourLegStrategy(fake_settings)
    from dataclasses import replace

    with pytest.raises(ValueError, match="across_fill_calldata must be non-empty"):
        strategy.build_params(replace(sample_plan, across_fill_calldata=Hex("0x")))

    with pytest.raises(ValueError, match="arb_swaps must contain at least one bridge swap"):
        strategy.build_params(replace(sample_plan, arb_swaps=[]))

    with pytest.raises(ValueError, match="flash_amount must be > 0"):
        strategy.build_params(replace(sample_plan, flash_amount=0))

    with pytest.raises(ValueError, match="expected_profit_wei must be > 0"):
        strategy.build_params(replace(sample_plan, expected_profit_wei=0))
