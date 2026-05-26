"""Unit tests for the ported native arbitrage strategy."""

import time
from unittest.mock import MagicMock

import pytest

from degenbot.adapters.config import Settings
from degenbot.decision.types import Hex
from degenbot.strategies_coordinator.native_arb import NativeArbStrategy
from degenbot.strategies_coordinator.types import (
    DEX_KIND,
)
from degenbot.types_solver.executor import DexKind, FlashProtocol
from degenbot.types_solver.executor import SwapStep as EngineSwapStep
from degenbot.types_solver.wire import Opportunity

# Mock addresses
_EXECUTOR_ADDR = "0x" + "e" * 40
_FLASH_TOKEN = "0x" + "1" * 40
_TOKEN_OUT = "0x" + "2" * 40
_ARB_AAVE_POOL = "0x794a61358d6845594f94dc1db02a252b5b4814ad"


@pytest.fixture
def fake_settings() -> Settings:
    settings = MagicMock(spec=Settings)
    settings.executor_address = _EXECUTOR_ADDR
    settings.aave_v3_pool = _ARB_AAVE_POOL
    settings.morpho_blue = None
    return settings


@pytest.fixture
def sample_opp() -> Opportunity:
    return Opportunity(
        id="01HZK_TEST",
        kind="NativeArb",
        tokenIn=_FLASH_TOKEN,
        tokenOut=_TOKEN_OUT,
        amountIn=10**18,
        estimatedProfitWei=10**16,
        flashToken=_FLASH_TOKEN,
        flashAmount=10**18,
        path=[],
        poolAddresses=[],
        detectedAtNs=1700000000000000000,
    )


def test_native_arb_build_params_default(fake_settings, sample_opp):
    strategy = NativeArbStrategy(fake_settings)
    params = strategy.build_params(sample_opp)

    assert params.flash_protocol == FlashProtocol.AAVE_V3
    assert params.flash_lender.lower() == _ARB_AAVE_POOL.lower()
    assert params.flash_token.lower() == _FLASH_TOKEN.lower()
    assert params.flash_amount == 10**18
    assert params.min_profit == int(sample_opp.estimated_profit_wei * 0.95)
    assert params.deadline > int(time.time())


def test_native_arb_rejects_zero_flash(fake_settings, sample_opp):
    strategy = NativeArbStrategy(fake_settings)

    opp = sample_opp.model_copy(update={"flash_amount": 0})
    with pytest.raises(ValueError, match="flashAmount must be > 0"):
        strategy.build_params(opp)


def test_native_arb_mapping_steps(fake_settings, sample_opp):
    opp = Opportunity(
        **{
            **sample_opp.model_dump(),
            "path": [
                EngineSwapStep(
                    dex_kind=DexKind.UNI_V3_POOL,
                    router="0x" + "3" * 40,
                    call_data=Hex("0x"),
                    token_in=_FLASH_TOKEN,
                    token_out=_TOKEN_OUT,
                    amount_in=10**18,
                    amount_out_min=0,
                )
            ],
        }
    )

    strategy = NativeArbStrategy(fake_settings)
    params = strategy.build_params(opp)

    assert len(params.swaps) == 1
    assert params.swaps[0].dex_kind == DEX_KIND.V3
    assert params.swaps[0].router == "0x" + "3" * 40
