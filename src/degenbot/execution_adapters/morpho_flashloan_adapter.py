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

import structlog

from degenbot.execution_adapters.adapter_base import validate_executor_strategy

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
            raise ValueError(f"Morpho flash-loan amount must be > 0, got {amount}")
        if not token or int(token, 16) == 0:
            raise ValueError("Morpho flash-loan token must be non-zero address")
        return MorphoFlashLoanRequest(
            token=token,
            amount=amount,
            callback_data=callback_data,
        )

    def encode_executor_calldata(
        self,
        req: MorphoFlashLoanRequest,
        strategy: str = "native_arb",
    ) -> bytes:
        """Encode the Executor function call that triggers Morpho.flashLoan.

        Maps `strategy` → one of `executeNativeArb` / `matchInternal` /
        `composeFourLeg`. The selected function packs the FlashProtocol
        kind = 1 (Morpho) plus `req.token` / `req.amount` / `req.callback_data`
        into the strategy-specific param struct.

        TODO(scaffold): wire `eth_abi` to encode the chosen Executor
        function's calldata once the final ABI lands. The on-chain Morpho
        callback signature DOES NOT include the borrowed token, so
        `req.token` must be packed into the callback params struct that
        ends up as `data` on the wire.
        """
        validate_executor_strategy(strategy)
        _ = req
        raise NotImplementedError(
            "TODO(scaffold): wire eth_abi to encode Executor calldata once final "
            "ABI lands. Note: pack `token` into callback params — Morpho's on-chain "
            "callback signature does not pass it.",
        )
