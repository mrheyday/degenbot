"""Off-chain Aave V3 flash-loan transaction builder.

Constructs the calldata that the submitter feeds to `Executor.sol` to
trigger an Aave V3 multi-asset flash loan. **Does NOT submit txs** —
submission lives in the submitter; this module is a pure off-chain
calldata builder.

On-chain receiver: `Executor.sol::executeOperation(assets, amounts, premiums,
initiator, params) → bool` per `docs/architecture/05` §5.5.

Per ADR-007 H2 — **always emit array form** even for single-asset flash
loans. `flashLoanSimple` is intentionally not used to keep the on-chain
callback shape uniform.

Fee model (per `docs/architecture/07` §1.1): Aave V3 charges **5 bps**
(0.05%) of the borrowed amount; the Executor must approve `amount + premium`
before the callback returns.

Critical gotcha (§07 §1.1): the `interestRateModes` array MUST be all-zeros
to avoid opening a debt position. Non-zero modes are rejected at build time.

FlashProtocol enum (per `Executor.sol::_triggerFlashLoan`):
  **0 = Aave V3**, 1 = Morpho, 2 = ERC-3156, 3 = UniV3.

Aave V3 `referralCode` is a `uint16` (range [0, 65535]). The on-chain
Executor pins it to 0 in `_triggerFlashLoan`; the off-chain builder
preserves the field for API parity but defaults to 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

import structlog

from degenbot.execution_adapters.adapter_base import validate_executor_strategy

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.aave_v3_flashloan_adapter",
)

# Aave V3 `referralCode` is a `uint16` per the on-chain ABI; bound the
# off-chain builder to the same range to fail fast on overflow.
_UINT16_MAX: Final[int] = 65535


# ---------------------------------------------------------------------------
# Wire types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AaveV3FlashLoanRequest:
    """A pure-data Aave V3 multi-asset flash-loan request.

    Per ADR-007 H2 + §07 §1.1 gotcha:
      - Always array form (single-asset uses 1-element arrays).
      - `modes` MUST be all-zeros — non-zero opens a debt position.
      - Lengths of `assets`, `amounts`, `modes` must agree.
    """

    assets: list[str]
    amounts: list[int]
    modes: list[int] = field(default_factory=list)
    callback_data: bytes = b""
    referral_code: int = 0

    def __post_init__(self) -> None:
        n = len(self.assets)
        if n == 0:
            raise ValueError("Aave V3 flash-loan request requires ≥1 asset")
        if len(self.amounts) != n:
            raise ValueError(
                f"Aave V3 array length mismatch: assets={n} amounts={len(self.amounts)}",
            )
        if len(self.modes) != n:
            raise ValueError(
                f"Aave V3 array length mismatch: assets={n} modes={len(self.modes)}",
            )
        for a in self.amounts:
            if a <= 0:
                raise ValueError(f"Aave V3 flash-loan amounts must all be > 0, got {a}")
        for m in self.modes:
            if m != 0:
                # §07 §1.1 gotcha: non-zero modes open a debt position.
                raise ValueError(
                    f"Aave V3 interestRateModes must be all-zeros (got {m}); non-zero opens a debt position.",
                )
        if not 0 <= self.referral_code <= _UINT16_MAX:
            raise ValueError(
                f"Aave V3 referralCode must be uint16 [0, {_UINT16_MAX}], got {self.referral_code}",
            )


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class AaveV3FlashLoanBuilder:
    """Pure off-chain builder for Aave V3 flash-loan transactions.

    Args:
        aave_pool_address: Aave V3 Pool on Arbitrum
            (`0x794a61358D6845594F94dc1DB02A252b5b4814aD`, verify per §07 §1.1).
            The on-chain Executor pins `lender == AAVE_V3_POOL` immutable;
            this builder reflects that for clarity.
        executor_address: our hardened `Executor.sol`. Calldata produced by
            this builder targets one of `executeNativeArb` / `matchInternal`
            / `composeFourLeg` on this address.
    """

    # Aave V3 charges 5 bps (0.05%) per §07 §1.1.
    fee_bps: int = 5

    # Mirrors `Executor.sol::FlashProtocol` enum unwrap.
    FLASH_PROTOCOL_KIND: int = 0  # Aave V3

    def __init__(self, aave_pool_address: str, executor_address: str) -> None:
        self._aave_pool_address = aave_pool_address
        self._executor_address = executor_address
        self._log = logger.bind(
            aave_pool_address=aave_pool_address,
            executor_address=executor_address,
        )

    def build_request(
        self,
        assets: list[str],
        amounts: list[int],
        callback_data: bytes,
        modes: list[int] | None = None,
        referral_code: int = 0,
    ) -> AaveV3FlashLoanRequest:
        """Validate and construct a multi-asset flash-loan request.

        Defaults `modes` to `[0] * len(assets)` per §07 §1.1 gotcha.
        Validation happens in `AaveV3FlashLoanRequest.__post_init__`.
        """
        if modes is None:
            modes = [0] * len(assets)
        return AaveV3FlashLoanRequest(
            assets=list(assets),
            amounts=list(amounts),
            modes=list(modes),
            callback_data=callback_data,
            referral_code=referral_code,
        )

    def encode_executor_calldata(
        self,
        req: AaveV3FlashLoanRequest,
        strategy: str = "native_arb",
    ) -> bytes:
        """Encode the Executor function call that triggers Pool.flashLoan.

        Maps `strategy` → one of `executeNativeArb` / `matchInternal` /
        `composeFourLeg`. The selected function packs the FlashProtocol
        kind = 0 (Aave V3) plus `req.assets` / `req.amounts` / `req.modes`
        / `req.callback_data` / `req.referral_code` into the strategy-
        specific param struct.

        TODO(scaffold): wire `eth_abi` to encode the chosen Executor
        function's calldata once the final ABI lands.
        """
        validate_executor_strategy(strategy)
        _ = req
        raise NotImplementedError(
            "TODO(scaffold): wire eth_abi to encode Executor calldata once final ABI lands.",
        )

    @classmethod
    def compute_premium(cls, amount: int) -> int:
        """Pure math: amount * fee_bps // 10_000.

        Aave V3 rounds DOWN (integer division). The on-chain Pool computes
        the same value; this helper lets the off-chain solver pre-size the
        repayment allowance.
        """
        return amount * cls.fee_bps // 10_000
