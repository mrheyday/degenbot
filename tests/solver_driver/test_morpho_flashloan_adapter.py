"""Unit tests for MorphoFlashLoanBuilder + MorphoFlashLoanRequest.

Pure off-chain calldata builder; no httpx, no I/O. Validation tests cover
the input checks; encode_executor_calldata is stub until eth_abi wiring.
"""

from __future__ import annotations

import pytest
from degenbot.execution.morpho_flashloan_adapter import (
    MorphoFlashLoanBuilder,
    MorphoFlashLoanRequest,
)

_MORPHO_BLUE = "0x6c247b1F6182318877311737BaC0844bAa518F5e"  # placeholder
_EXECUTOR = "0x0000000000000000000000000000000000000123"
_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_ZERO = "0x0000000000000000000000000000000000000000"


class TestMorphoFlashLoanRequest:
    def test_request_holds_payload_unchanged(self) -> None:
        req = MorphoFlashLoanRequest(token=_USDC, amount=1_000_000, callback_data=b"\x01\x02")
        assert req.token == _USDC
        assert req.amount == 1_000_000
        assert req.callback_data == b"\x01\x02"


class TestMorphoFlashLoanBuilderConstants:
    def test_morpho_fee_bps_is_zero(self) -> None:
        # §07 §1.2: Morpho Blue flash loans are free.
        assert MorphoFlashLoanBuilder.fee_bps == 0

    def test_morpho_flash_protocol_kind_is_one(self) -> None:
        # Mirrors Executor.sol::FlashProtocol unwrap (0=Aave, 1=Morpho, 2=ERC-3156, 3=UniV3)
        assert MorphoFlashLoanBuilder.FLASH_PROTOCOL_KIND == 1


class TestMorphoFlashLoanBuilderValidation:
    def test_build_valid_request_passes(self) -> None:
        b = MorphoFlashLoanBuilder(_MORPHO_BLUE, _EXECUTOR)
        req = b.build_request(token=_USDC, amount=10_000_000, callback_data=b"\xab")
        assert isinstance(req, MorphoFlashLoanRequest)
        assert req.amount == 10_000_000

    def test_build_zero_amount_rejected(self) -> None:
        b = MorphoFlashLoanBuilder(_MORPHO_BLUE, _EXECUTOR)
        with pytest.raises(ValueError, match="must be > 0"):
            b.build_request(token=_USDC, amount=0, callback_data=b"")

    def test_build_negative_amount_rejected(self) -> None:
        b = MorphoFlashLoanBuilder(_MORPHO_BLUE, _EXECUTOR)
        with pytest.raises(ValueError, match="must be > 0"):
            b.build_request(token=_USDC, amount=-1, callback_data=b"")

    def test_build_zero_address_rejected(self) -> None:
        b = MorphoFlashLoanBuilder(_MORPHO_BLUE, _EXECUTOR)
        with pytest.raises(ValueError, match="non-zero address"):
            b.build_request(token=_ZERO, amount=1_000, callback_data=b"")

    def test_empty_callback_data_allowed(self) -> None:
        b = MorphoFlashLoanBuilder(_MORPHO_BLUE, _EXECUTOR)
        req = b.build_request(token=_USDC, amount=1_000, callback_data=b"")
        assert req.callback_data == b""


class TestMorphoFlashLoanBuilderEncode:
    def test_encode_default_strategy_raises_not_implemented(self) -> None:
        b = MorphoFlashLoanBuilder(_MORPHO_BLUE, _EXECUTOR)
        req = b.build_request(token=_USDC, amount=1_000_000, callback_data=b"\x00")
        with pytest.raises(NotImplementedError, match="eth_abi"):
            b.encode_executor_calldata(req)

    def test_encode_match_internal_strategy_raises_not_implemented(self) -> None:
        b = MorphoFlashLoanBuilder(_MORPHO_BLUE, _EXECUTOR)
        req = b.build_request(token=_USDC, amount=1_000_000, callback_data=b"\x00")
        with pytest.raises(NotImplementedError):
            b.encode_executor_calldata(req, strategy="match_internal")

    def test_encode_compose_four_leg_strategy_raises_not_implemented(self) -> None:
        b = MorphoFlashLoanBuilder(_MORPHO_BLUE, _EXECUTOR)
        req = b.build_request(token=_USDC, amount=1_000_000, callback_data=b"\x00")
        with pytest.raises(NotImplementedError):
            b.encode_executor_calldata(req, strategy="compose_four_leg")

    def test_encode_unknown_strategy_rejected(self) -> None:
        b = MorphoFlashLoanBuilder(_MORPHO_BLUE, _EXECUTOR)
        req = b.build_request(token=_USDC, amount=1_000_000, callback_data=b"\x00")
        with pytest.raises(ValueError, match="Unsupported strategy"):
            b.encode_executor_calldata(req, strategy="not_a_real_strategy")
