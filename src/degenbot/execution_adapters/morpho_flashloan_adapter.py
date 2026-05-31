"""Off-chain Morpho Blue flash-loan transaction builder.

Constructs the calldata that the submitter feeds to `Executor.sol` to
trigger a Morpho Blue flash loan internally. **Does NOT submit txs** —
submission lives in the submitter; this module is a pure off-chain
calldata builder.

On-chain receiver: `Executor.sol::onMorphoFlashLoan(uint256 assets, bytes data)`
per `docs/architecture/05` §5.5. Note that the Morpho callback signature
omits the borrowed token — the on-chain Executor decodes it from `data`.
This is a non-obvious shape constraint: the off-chain builder MUST pack
`token` into the `callback_data` it hands to the Executor function so
that the in-flight callback can recover it.

Fee model (per `docs/architecture/07` §1.2): Morpho Blue flash loans are
**FREE** (`fee_bps = 0`). The Morpho repayment pull is a `transferFrom` for
exactly the borrowed `assets`; the Executor must approve the Morpho
singleton for `assets` (no premium).

FlashProtocol enum (per `Executor.sol::_triggerFlashLoan`):
  0 = Aave V3, **1 = Morpho**, 2 = ERC-3156, 3 = UniV3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from degenbot.execution_adapters.adapter_base import validate_executor_strategy

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.morpho_flashloan_adapter",
)


# ---------------------------------------------------------------------------
# Wire types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MorphoFlashLoanRequest:
    """A pure-data Morpho Blue flash-loan request.

    `callback_data` is the abi-encoded payload the Executor callback decodes;
    it must include enough information for the on-chain side to recover
    `token` (which is NOT part of the Morpho callback signature).
    """

    token: str
    amount: int  # native units (wei for ETH, base units for ERC-20)
    callback_data: bytes


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class MorphoFlashLoanBuilder:
    """Pure off-chain builder for Morpho Blue flash-loan transactions.

    Args:
        morpho_blue_address: Morpho Blue singleton on Arbitrum. The Executor
            verifies `lender == MORPHO_BLUE` immutable; this builder reflects
            that for clarity (the lender field is implicit on Morpho — only
            one Morpho singleton).
        executor_address: our hardened `Executor.sol`. Calldata produced by
            this builder targets one of `executeNativeArb` / `matchInternal`
            / `composeFourLeg` on this address.
    """

    # Morpho Blue flash loans are free.
    fee_bps: int = 0

    # Mirrors `Executor.sol::FlashProtocol` enum unwrap.
    FLASH_PROTOCOL_KIND: int = 1  # Morpho

    def __init__(self, morpho_blue_address: str, executor_address: str) -> None:
        self._morpho_blue_address = morpho_blue_address
        self._executor_address = executor_address
        self._log = logger.bind(
            morpho_blue_address=morpho_blue_address,
            executor_address=executor_address,
        )

    def build_request(
        self,
        token: str,
        amount: int,
        callback_data: bytes,
    ) -> MorphoFlashLoanRequest:
        """Validate and construct a flash-loan request.

        Raises:
            ValueError: `amount <= 0`, or `token` is the zero address.
        """
        if amount <= 0:
            msg = f"Morpho flash-loan amount must be > 0, got {amount}"
            raise ValueError(msg)
        if not token or int(token, 16) == 0:
            msg = "Morpho flash-loan token must be non-zero address"
            raise ValueError(msg)
        return MorphoFlashLoanRequest(
            token=token,
            amount=amount,
            callback_data=callback_data,
        )

    def encode_executor_calldata(
        self,
        req: MorphoFlashLoanRequest,
        strategy: str = "native_arb",
        *,
        swaps: Sequence[Mapping[str, Any]] | None = None,
        cow_settlement_calldata: bytes | str | None = None,
        uniswapx_batch_calldata: bytes | str | None = None,
        expected_token_inflows: Sequence[str | bytes] | None = None,
        expected_token_inflow_min: Sequence[int | bytes] | None = None,
        across_fill_calldata: bytes | str | None = None,
        arb_swaps: Sequence[Mapping[str, Any]] | None = None,
        cow_fill_calldata: bytes | str | None = None,
        uniswapx_rebalance_calldata: bytes | str | None = None,
        min_profit: int = 0,
        deadline: int = 0,
    ) -> bytes:
        """Encode the Executor function call that triggers Morpho.flashLoan.

        Maps `strategy` → one of `executeNativeArb` / `matchInternal` /
        `composeFourLeg`.

        The on-chain Morpho callback signature DOES NOT include the borrowed
        token, so the `Executor` implementation handles the single-token
        case by reusing the `flashToken` field.
        """
        from degenbot.execution import (
            encode_compose_four_leg_calldata,
            encode_match_internal_calldata,
            encode_native_arb_calldata,
        )

        validate_executor_strategy(strategy)

        if strategy == "native_arb":
            return encode_native_arb_calldata(
                flash_lender=self._morpho_blue_address,
                flash_protocol="Morpho",
                flash_token=req.token,
                flash_amount=req.amount,
                swaps=[dict(swap) for swap in swaps] if swaps is not None else [],
                min_profit=min_profit,
                deadline=deadline,
            )

        if strategy == "match_internal":
            if (
                cow_settlement_calldata is None
                or uniswapx_batch_calldata is None
                or expected_token_inflows is None
                or expected_token_inflow_min is None
            ):
                msg = "Morpho match_internal encoding requires both calldata legs and expected inflows"
                raise ValueError(msg)
            return encode_match_internal_calldata(
                cow_settlement_calldata=cow_settlement_calldata,
                uniswapx_batch_calldata=uniswapx_batch_calldata,
                expected_token_inflows=list(expected_token_inflows),
                expected_token_inflow_min=list(expected_token_inflow_min),
                flash_lender=self._morpho_blue_address,
                flash_protocol="Morpho",
                flash_token=req.token,
                flash_amount=req.amount,
                min_profit=min_profit,
                deadline=deadline,
            )

        if strategy == "compose_four_leg":
            if (
                across_fill_calldata is None
                or cow_fill_calldata is None
                or uniswapx_rebalance_calldata is None
            ):
                msg = "Morpho compose_four_leg encoding requires Across, CoW, and UniswapX calldata"
                raise ValueError(msg)
            return encode_compose_four_leg_calldata(
                across_fill_calldata=across_fill_calldata,
                arb_swaps=[dict(swap) for swap in arb_swaps] if arb_swaps is not None else [],
                cow_fill_calldata=cow_fill_calldata,
                uniswapx_rebalance_calldata=uniswapx_rebalance_calldata,
                flash_lender=self._morpho_blue_address,
                flash_protocol="Morpho",
                flash_token=req.token,
                flash_amount=req.amount,
                min_profit=min_profit,
                deadline=deadline,
            )

        msg = f"Morpho adapter: unsupported strategy {strategy!r}"
        raise ValueError(msg)
