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
from typing import TYPE_CHECKING, Final

import structlog

from degenbot.execution_adapters.adapter_base import validate_executor_strategy

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any

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
            msg = "Aave V3 flash-loan request requires ≥1 asset"
            raise ValueError(msg)
        if len(self.amounts) != n:
            msg = f"Aave V3 array length mismatch: assets={n} amounts={len(self.amounts)}"
            raise ValueError(
                msg,
            )
        if len(self.modes) != n:
            msg = f"Aave V3 array length mismatch: assets={n} modes={len(self.modes)}"
            raise ValueError(
                msg,
            )
        for a in self.amounts:
            if a <= 0:
                msg = f"Aave V3 flash-loan amounts must all be > 0, got {a}"
                raise ValueError(msg)
        for m in self.modes:
            if m != 0:
                # §07 §1.1 gotcha: non-zero modes open a debt position.
                msg = f"Aave V3 interestRateModes must be all-zeros (got {m}); non-zero opens a debt position."
                raise ValueError(
                    msg,
                )
        if not 0 <= self.referral_code <= _UINT16_MAX:
            msg = (
                f"Aave V3 referralCode must be uint16 [0, {_UINT16_MAX}], got {self.referral_code}"
            )
            raise ValueError(
                msg,
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
        """Encode the Executor function call that triggers Pool.flashLoan.

        Maps `strategy` → one of `executeNativeArb` / `matchInternal` /
        `composeFour_leg`.

        Note: Executor.sol currently supports single-asset flash loans for
        all strategy entry points.
        """
        from degenbot.execution import (
            encode_compose_four_leg_calldata,
            encode_match_internal_calldata,
            encode_native_arb_calldata,
        )

        validate_executor_strategy(strategy)

        if len(req.assets) != 1:
            msg = f"Aave V3 Executor integration currently requires exactly 1 asset, got {len(req.assets)}"
            raise ValueError(msg)

        if strategy == "native_arb":
            return encode_native_arb_calldata(
                flash_lender=self._aave_pool_address,
                flash_protocol="Aave",
                flash_token=req.assets[0],
                flash_amount=req.amounts[0],
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
                msg = "Aave V3 match_internal encoding requires both calldata legs and expected inflows"
                raise ValueError(msg)
            return encode_match_internal_calldata(
                cow_settlement_calldata=cow_settlement_calldata,
                uniswapx_batch_calldata=uniswapx_batch_calldata,
                expected_token_inflows=list(expected_token_inflows),
                expected_token_inflow_min=list(expected_token_inflow_min),
                flash_lender=self._aave_pool_address,
                flash_protocol="Aave",
                flash_token=req.assets[0],
                flash_amount=req.amounts[0],
                min_profit=min_profit,
                deadline=deadline,
            )

        if strategy == "compose_four_leg":
            if (
                across_fill_calldata is None
                or cow_fill_calldata is None
                or uniswapx_rebalance_calldata is None
            ):
                msg = (
                    "Aave V3 compose_four_leg encoding requires Across, CoW, and UniswapX calldata"
                )
                raise ValueError(msg)
            return encode_compose_four_leg_calldata(
                across_fill_calldata=across_fill_calldata,
                arb_swaps=[dict(swap) for swap in arb_swaps] if arb_swaps is not None else [],
                cow_fill_calldata=cow_fill_calldata,
                uniswapx_rebalance_calldata=uniswapx_rebalance_calldata,
                flash_lender=self._aave_pool_address,
                flash_protocol="Aave",
                flash_token=req.assets[0],
                flash_amount=req.amounts[0],
                min_profit=min_profit,
                deadline=deadline,
            )

        msg = f"Aave V3 adapter: unsupported strategy {strategy!r}"
        raise ValueError(msg)

    @classmethod
    def compute_premium(cls, amount: int) -> int:
        """Pure math: amount * fee_bps // 10_000.

        Aave V3 rounds DOWN (integer division). The on-chain Pool computes
        the same value; this helper lets the off-chain solver pre-size the
        repayment allowance.
        """
        return amount * cls.fee_bps // 10_000
