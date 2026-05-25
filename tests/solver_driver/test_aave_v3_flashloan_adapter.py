"""Unit tests for AaveV3FlashLoanBuilder + AaveV3FlashLoanRequest.

Pure off-chain calldata builder; no httpx, no I/O. Validation tests cover
the array-shape + modes-non-zero invariants per §07 §1.1; pure-math tests
cover the 5-bps premium computation.
"""

from __future__ import annotations

import pytest
from degenbot.execution.aave_v3_flashloan_adapter import (
    AaveV3FlashLoanBuilder,
    AaveV3FlashLoanRequest,
)

_AAVE_POOL = "0x794a61358D6845594F94dc1DB02A252b5b4814aD"  # §07 §1.1
_EXECUTOR = "0x0000000000000000000000000000000000000123"
_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
_DAI = "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1"


class TestAaveV3FlashLoanRequestValidation:
    def test_single_asset_valid(self) -> None:
        req = AaveV3FlashLoanRequest(
            assets=[_USDC],
            amounts=[1_000_000],
            modes=[0],
            callback_data=b"\xab",
            referral_code=0,
        )
        assert req.assets == [_USDC]
        assert req.amounts == [1_000_000]
        assert req.modes == [0]

    def test_multi_asset_valid(self) -> None:
        req = AaveV3FlashLoanRequest(
            assets=[_USDC, _WETH, _DAI],
            amounts=[1_000_000, 500_000_000_000_000, 1_000_000_000_000_000_000],
            modes=[0, 0, 0],
            callback_data=b"",
        )
        assert len(req.assets) == 3
        assert req.referral_code == 0  # default

    def test_empty_assets_rejected(self) -> None:
        with pytest.raises(ValueError, match="≥1 asset"):
            AaveV3FlashLoanRequest(assets=[], amounts=[], modes=[], callback_data=b"")

    def test_assets_amounts_length_mismatch_rejected(self) -> None:
        with pytest.raises(ValueError, match="length mismatch"):
            AaveV3FlashLoanRequest(
                assets=[_USDC, _WETH],
                amounts=[1_000_000],  # only one
                modes=[0, 0],
                callback_data=b"",
            )

    def test_assets_modes_length_mismatch_rejected(self) -> None:
        with pytest.raises(ValueError, match="length mismatch"):
            AaveV3FlashLoanRequest(
                assets=[_USDC, _WETH],
                amounts=[1_000_000, 2_000_000],
                modes=[0],  # only one
                callback_data=b"",
            )

    def test_zero_amount_rejected(self) -> None:
        with pytest.raises(ValueError, match="must all be > 0"):
            AaveV3FlashLoanRequest(
                assets=[_USDC],
                amounts=[0],
                modes=[0],
                callback_data=b"",
            )

    def test_negative_amount_rejected(self) -> None:
        with pytest.raises(ValueError, match="must all be > 0"):
            AaveV3FlashLoanRequest(
                assets=[_USDC],
                amounts=[-1],
                modes=[0],
                callback_data=b"",
            )

    def test_non_zero_mode_rejected_at_index_zero(self) -> None:
        # §07 §1.1 gotcha: non-zero modes open a debt position.
        with pytest.raises(ValueError, match="all-zeros"):
            AaveV3FlashLoanRequest(
                assets=[_USDC],
                amounts=[1_000_000],
                modes=[1],
                callback_data=b"",
            )

    def test_non_zero_mode_rejected_anywhere_in_array(self) -> None:
        # Explicit per advisor guidance: a non-zero mode anywhere triggers reject.
        with pytest.raises(ValueError, match="all-zeros"):
            AaveV3FlashLoanRequest(
                assets=[_USDC, _WETH, _DAI],
                amounts=[1_000_000, 1, 1],
                modes=[0, 0, 1],
                callback_data=b"",
            )

    def test_referral_code_below_range_rejected(self) -> None:
        with pytest.raises(ValueError, match="uint16"):
            AaveV3FlashLoanRequest(
                assets=[_USDC],
                amounts=[1_000_000],
                modes=[0],
                callback_data=b"",
                referral_code=-1,
            )

    def test_referral_code_above_range_rejected(self) -> None:
        with pytest.raises(ValueError, match="uint16"):
            AaveV3FlashLoanRequest(
                assets=[_USDC],
                amounts=[1_000_000],
                modes=[0],
                callback_data=b"",
                referral_code=65536,
            )

    def test_referral_code_at_upper_bound_accepted(self) -> None:
        req = AaveV3FlashLoanRequest(
            assets=[_USDC],
            amounts=[1_000_000],
            modes=[0],
            callback_data=b"",
            referral_code=65535,
        )
        assert req.referral_code == 65535


class TestAaveV3FlashLoanBuilderConstants:
    def test_aave_v3_fee_bps_is_5(self) -> None:
        # §07 §1.1: 0.05% = 5 bps
        assert AaveV3FlashLoanBuilder.fee_bps == 5

    def test_aave_v3_flash_protocol_kind_is_zero(self) -> None:
        # Mirrors Executor.sol::FlashProtocol unwrap (0=Aave, 1=Morpho, 2=ERC-3156, 3=UniV3)
        assert AaveV3FlashLoanBuilder.FLASH_PROTOCOL_KIND == 0


class TestAaveV3FlashLoanBuilderBuild:
    def test_build_defaults_modes_to_zeros(self) -> None:
        b = AaveV3FlashLoanBuilder(_AAVE_POOL, _EXECUTOR)
        req = b.build_request(
            assets=[_USDC, _WETH],
            amounts=[1_000_000, 500_000_000_000_000],
            callback_data=b"",
        )
        assert req.modes == [0, 0]

    def test_build_explicit_modes_passes_through(self) -> None:
        b = AaveV3FlashLoanBuilder(_AAVE_POOL, _EXECUTOR)
        req = b.build_request(
            assets=[_USDC],
            amounts=[1_000_000],
            callback_data=b"",
            modes=[0],
        )
        assert req.modes == [0]

    def test_build_propagates_validation_error(self) -> None:
        # Builder is a thin wrapper; validation runs in __post_init__.
        b = AaveV3FlashLoanBuilder(_AAVE_POOL, _EXECUTOR)
        with pytest.raises(ValueError, match="all-zeros"):
            b.build_request(
                assets=[_USDC],
                amounts=[1_000_000],
                callback_data=b"",
                modes=[1],
            )

    def test_build_propagates_referral_code(self) -> None:
        b = AaveV3FlashLoanBuilder(_AAVE_POOL, _EXECUTOR)
        req = b.build_request(
            assets=[_USDC],
            amounts=[1_000_000],
            callback_data=b"",
            referral_code=42,
        )
        assert req.referral_code == 42


class TestAaveV3FlashLoanBuilderPremiumMath:
    def test_premium_round_million_usdc(self) -> None:
        # 1_000_000 USDC * 5 / 10_000 = 500
        assert AaveV3FlashLoanBuilder.compute_premium(1_000_000) == 500

    def test_premium_one_eth_in_wei(self) -> None:
        # 1e18 wei * 5 / 10_000 = 5e14
        assert AaveV3FlashLoanBuilder.compute_premium(10**18) == 5 * 10**14

    def test_premium_zero_amount_zero_premium(self) -> None:
        assert AaveV3FlashLoanBuilder.compute_premium(0) == 0

    def test_premium_rounds_down_below_resolution(self) -> None:
        # Aave V3 rounds DOWN. 1999 * 5 // 10_000 = 9999 // 10_000 = 0
        assert AaveV3FlashLoanBuilder.compute_premium(1_999) == 0

    def test_premium_rounds_down_just_above_resolution(self) -> None:
        # 2000 * 5 // 10_000 = 10000 // 10_000 = 1
        assert AaveV3FlashLoanBuilder.compute_premium(2_000) == 1

    def test_premium_huge_amount_no_overflow(self) -> None:
        # Python ints are unbounded — sanity check on an absurdly large notional.
        amount = 10**40
        assert AaveV3FlashLoanBuilder.compute_premium(amount) == amount * 5 // 10_000


class TestAaveV3FlashLoanBuilderEncode:
    def test_encode_default_strategy_raises_not_implemented(self) -> None:
        b = AaveV3FlashLoanBuilder(_AAVE_POOL, _EXECUTOR)
        req = b.build_request(assets=[_USDC], amounts=[1_000_000], callback_data=b"")
        with pytest.raises(NotImplementedError, match="eth_abi"):
            b.encode_executor_calldata(req)

    def test_encode_match_internal_strategy_raises_not_implemented(self) -> None:
        b = AaveV3FlashLoanBuilder(_AAVE_POOL, _EXECUTOR)
        req = b.build_request(assets=[_USDC], amounts=[1_000_000], callback_data=b"")
        with pytest.raises(NotImplementedError):
            b.encode_executor_calldata(req, strategy="match_internal")

    def test_encode_compose_four_leg_strategy_raises_not_implemented(self) -> None:
        b = AaveV3FlashLoanBuilder(_AAVE_POOL, _EXECUTOR)
        req = b.build_request(assets=[_USDC], amounts=[1_000_000], callback_data=b"")
        with pytest.raises(NotImplementedError):
            b.encode_executor_calldata(req, strategy="compose_four_leg")

    def test_encode_unknown_strategy_rejected(self) -> None:
        b = AaveV3FlashLoanBuilder(_AAVE_POOL, _EXECUTOR)
        req = b.build_request(assets=[_USDC], amounts=[1_000_000], callback_data=b"")
        with pytest.raises(ValueError, match="Unsupported strategy"):
            b.encode_executor_calldata(req, strategy="not_a_real_strategy")
