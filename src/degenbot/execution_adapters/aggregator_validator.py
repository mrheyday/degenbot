"""Aggregator-pathfinder adapter — second-opinion path validator for the solver.

Sits alongside degenbot's own pathfinder. The solver loop uses BOTH as
independent validators on intent paths:

  - degenbot's pathfinder = native pool-aware route discovery (cycle search,
    golden-section, REVM-grounded simulation)
  - aggregator-validator (this module) = production aggregator quote consensus
    (DeFiLlamaSwap + 1inch / 0x / Paraswap fanout via the coordinator's
    quote engine)

A path is considered "validated" if BOTH validators agree the expected output
is within an acceptable slippage band. Disagreement → coordinator flags the
opportunity for review (queues with reduced priority).

Wire: HTTP to the TS coordinator's quote endpoint (preferred — keeps
aggregator API keys in one place) OR direct DeFiLlamaSwap public endpoint
(no auth) when the coordinator is unreachable.

Per `docs/architecture/degenbot-integration-plan.md` open decision §9.5: this
adapter is part of the Python solver runtime alongside degenbot.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Literal

import httpx
import structlog

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.aggregator_validator",
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class ValidationVerdict(Enum):
    VALIDATED = "validated"  # both validators agree within slippage band
    DEGRADED = "degraded"  # degenbot agrees but aggregator says path unviable
    DISPUTED = "disputed"  # validators disagree on amount_out beyond band
    UNAVAILABLE = "unavailable"  # aggregator endpoint unreachable; degraded coverage


@dataclass(frozen=True)
class AggregatorQuote:
    """Normalized response shape from the coordinator's quote endpoint."""

    source: Literal["llamaswap", "1inch", "0x", "paraswap", "odos", "kyberswap", "openocean"]
    amount_out_str: str
    estimated_gas: int
    fee_bps: int
    timestamp_ms: int

    @property
    def amount_out(self) -> int:
        """Exact integer wei. Aggregator responses are decimal strings on the wire."""
        return int(self.amount_out_str)


@dataclass(frozen=True)
class ValidationResult:
    """Aggregate verdict + supporting data."""

    verdict: ValidationVerdict
    src_asset: str
    dst_asset: str
    src_amount: int
    degenbot_amount_out: int
    aggregator_best_quote: AggregatorQuote | None
    slippage_bps: int  # signed: +ve means aggregator beats degenbot
    rationale: str


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class AggregatorPathValidator:
    """Aggregator-quote-based path validator.

    Pairs with degenbot's own pathfinder — the solver passes a candidate path
    + degenbot's expected_amount_out to `validate()`, which calls the
    aggregator quote engine and returns a verdict.
    """

    # Default acceptable band: aggregator must match degenbot ±50 bps to validate.
    DEFAULT_SLIPPAGE_TOLERANCE_BPS = 50

    def __init__(
        self,
        *,
        coordinator_quote_url: str | None = None,
        llamaswap_url: str = "https://swap-api.defillama.com",
        timeout_sec: float = 1.0,
        slippage_tolerance_bps: int = DEFAULT_SLIPPAGE_TOLERANCE_BPS,
    ) -> None:
        self._coordinator_quote_url = coordinator_quote_url
        self._llamaswap_url = llamaswap_url
        self._timeout = timeout_sec
        self._slippage_tolerance_bps = slippage_tolerance_bps
        self._client = httpx.AsyncClient(timeout=timeout_sec)
        self._log = logger.bind(
            coordinator=coordinator_quote_url is not None,
            llamaswap=llamaswap_url,
            slippage_tolerance_bps=slippage_tolerance_bps,
        )

    async def __aenter__(self) -> AggregatorPathValidator:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self._client.aclose()

    async def close(self) -> None:
        await self._client.aclose()

    async def validate(
        self,
        *,
        src_asset: str,
        dst_asset: str,
        src_amount: int,
        degenbot_amount_out: int,
    ) -> ValidationResult:
        """Compare degenbot's path output against an aggregator quote.

        Returns VALIDATED if aggregator beats or matches degenbot within
        ±slippage_tolerance_bps. Returns DISPUTED if aggregator returns a
        materially worse number (degenbot may be over-optimistic). Returns
        DEGRADED if aggregator says path is unviable but degenbot is positive.
        Returns UNAVAILABLE on transport error.
        """
        agg_quote = await self._best_aggregator_quote(
            src_asset=src_asset,
            dst_asset=dst_asset,
            src_amount=src_amount,
        )

        if agg_quote is None:
            return ValidationResult(
                verdict=ValidationVerdict.UNAVAILABLE,
                src_asset=src_asset,
                dst_asset=dst_asset,
                src_amount=src_amount,
                degenbot_amount_out=degenbot_amount_out,
                aggregator_best_quote=None,
                slippage_bps=0,
                rationale="aggregator endpoint unreachable; cannot validate",
            )

        slippage_bps = self._slippage_bps(degenbot_amount_out, agg_quote.amount_out)
        verdict = self._verdict_from_slippage(slippage_bps, agg_quote.amount_out)

        return ValidationResult(
            verdict=verdict,
            src_asset=src_asset,
            dst_asset=dst_asset,
            src_amount=src_amount,
            degenbot_amount_out=degenbot_amount_out,
            aggregator_best_quote=agg_quote,
            slippage_bps=slippage_bps,
            rationale=self._rationale(verdict, slippage_bps, agg_quote),
        )

    # -- internals ------------------------------------------------------------

    async def _best_aggregator_quote(
        self,
        *,
        src_asset: str,
        dst_asset: str,
        src_amount: int,
    ) -> AggregatorQuote | None:
        """Fetch best aggregator quote.

        Tries the coordinator's `/quote` endpoint first (which fans out across
        DefiLlamaSwap + 1inch/0x/etc). Falls back to direct DeFiLlamaSwap if
        the coordinator is unreachable.
        """
        if self._coordinator_quote_url:
            quote = await self._coordinator_quote(src_asset, dst_asset, src_amount)
            if quote is not None:
                return quote

        return await self._llamaswap_quote(src_asset, dst_asset, src_amount)

    async def _coordinator_quote(
        self,
        src_asset: str,
        dst_asset: str,
        src_amount: int,
    ) -> AggregatorQuote | None:
        """Hit the TS coordinator's /quote endpoint (preferred path)."""
        # TODO(scaffold): wire the actual /quote endpoint contract once it lands
        # in coordinator/src/http/. Currently the coordinator's quote-engine is
        # in-process only; this network surface is on the next-iteration list.
        _ = (src_asset, dst_asset, src_amount)
        return None

    async def _llamaswap_quote(
        self,
        src_asset: str,
        dst_asset: str,
        src_amount: int,
    ) -> AggregatorQuote | None:
        """Direct DeFiLlamaSwap fallback. No auth, public endpoint."""
        try:
            # DeFiLlamaSwap quote API — see coordinator/src/quotes/defillamaswap.ts
            # for the canonical request shape.
            resp = await self._client.get(
                f"{self._llamaswap_url}/swap/v1/quote",
                params={
                    "src": src_asset,
                    "dst": dst_asset,
                    "amount": str(src_amount),
                    "chainId": 42161,  # Arbitrum One per ADR-001
                },
            )
            resp.raise_for_status()
            body = resp.json()
        except httpx.HTTPError as exc:
            self._log.warn("llamaswap_unreachable", err=str(exc))
            return None
        except (KeyError, ValueError) as exc:
            self._log.warn("llamaswap_parse_error", err=str(exc))
            return None

        # TODO(scaffold): the actual DeFiLlamaSwap response shape may differ;
        # mirror the TS adapter's parsing in coordinator/src/quotes/defillamaswap.ts
        # once the request shape is verified live.
        amount_out = body.get("dstAmount") or body.get("amountOut") or "0"
        return AggregatorQuote(
            source="llamaswap",
            amount_out_str=str(amount_out),
            estimated_gas=int(body.get("estimatedGas", 0)),
            fee_bps=int(body.get("feeBps", 0)),
            timestamp_ms=int(body.get("timestampMs", 0)),
        )

    @staticmethod
    def _slippage_bps(degenbot_amount: int, agg_amount: int) -> int:
        """Compute (agg - degenbot) / degenbot in basis points.

        Signed result. +ve means aggregator beats degenbot. -ve means
        aggregator is worse (degenbot was over-optimistic).
        """
        if degenbot_amount == 0:
            return 0
        delta_bps = (Decimal(agg_amount) - Decimal(degenbot_amount)) * Decimal(10_000) / Decimal(degenbot_amount)
        return int(delta_bps)

    def _verdict_from_slippage(self, slippage_bps: int, agg_amount: int) -> ValidationVerdict:
        if agg_amount == 0:
            return ValidationVerdict.DEGRADED
        if abs(slippage_bps) <= self._slippage_tolerance_bps:
            return ValidationVerdict.VALIDATED
        return ValidationVerdict.DISPUTED

    def _rationale(
        self,
        verdict: ValidationVerdict,
        slippage_bps: int,
        agg_quote: AggregatorQuote,
    ) -> str:
        sign = "+" if slippage_bps >= 0 else ""
        return (
            f"verdict={verdict.value} slippage={sign}{slippage_bps}bps "
            f"vs tolerance ±{self._slippage_tolerance_bps}bps source={agg_quote.source}"
        )
