"""Deterministic flash-source router for Executor-backed strategies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from degenbot.strategies_coordinator.types import FLASH_PROTOCOL, FlashProtocol

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from degenbot.decision.types import Address

logger = logging.getLogger(__name__)

FlashRouteSource = Literal["default", "explicit", "candidate"]

DEFAULT_AAVE_V3_POOL: Address = "0x794a61358D6845594F94dc1DB02A252b5b4814aD"  # Arbitrum One
DEFAULT_MORPHO_BLUE: Address = "0x6c247b1F6182318877311737BaC0844bAa518F5e"
DEFAULT_WRAPPED_NATIVE_TOKEN: Address = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
DEFAULT_WRAP_GAS_UNITS = 30_000
DEFAULT_UNWRAP_GAS_UNITS = 35_000


@dataclass(frozen=True)
class FlashRouteCandidate:
    protocol: FlashProtocol
    lender: Address | None = None
    available_liquidity: int | None = None
    estimated_fee_bps: int | None = None
    flat_fee: int | None = None
    gas_score_wei: int | None = None
    gas_units: int | None = None
    gas_price_wei: int | None = None
    wrap_native: bool | None = None
    unwrap_native: bool | None = None
    wrap_gas_units: int | None = None
    unwrap_gas_units: int | None = None
    native_cost_in_borrow_token: int | None = None
    extra_cost_in_borrow_token: int | None = None
    enabled: bool = True


@dataclass(frozen=True)
class ExecutorFlashRoute:
    protocol: FlashProtocol
    lender: Address
    source: FlashRouteSource
    flash_fee: int
    native_gas_cost_wei: int
    wrapping_cost_wei: int
    total_cost_in_borrow_token: int
    available_liquidity: int | None = None


def resolve_executor_flash_route(
    token: Address,
    amount: int,
    context: str = "default",
    requested_protocol: FlashProtocol | None = None,
    explicit_lender: Address | None = None,
    candidates: Sequence[FlashRouteCandidate] | None = None,
    wrapped_native_token: Address | None = None,
    aave_v3_pool: Address | None = None,
    morpho_blue: Address | None = None,
) -> ExecutorFlashRoute:
    """Select the flash route used by Executor strategy structs."""

    if requested_protocol is not None:
        return _normalize_route(
            token=token,
            amount=amount,
            protocol=requested_protocol,
            source="explicit",
            context=context,
            lender=explicit_lender,
            wrapped_native_token=wrapped_native_token,
            aave_v3_pool=aave_v3_pool,
            morpho_blue=morpho_blue,
        )

    candidate = _pick_best_candidate(
        token=token,
        amount=amount,
        context=context,
        candidates=candidates,
        wrapped_native_token=wrapped_native_token,
        aave_v3_pool=aave_v3_pool,
        morpho_blue=morpho_blue,
    )
    if candidate is not None:
        return candidate

    return _normalize_route(
        token=token,
        amount=amount,
        protocol=cast("FlashProtocol", FLASH_PROTOCOL.AAVE_V3),
        source="default",
        context=context,
        lender=explicit_lender,
        wrapped_native_token=wrapped_native_token,
        aave_v3_pool=aave_v3_pool,
        morpho_blue=morpho_blue,
    )


def _pick_best_candidate(
    token: Address,
    amount: int,
    context: str,
    candidates: Sequence[FlashRouteCandidate] | None,
    wrapped_native_token: Address | None,
    aave_v3_pool: Address | None,
    morpho_blue: Address | None,
) -> ExecutorFlashRoute | None:
    if not candidates:
        return None

    valid: list[ExecutorFlashRoute] = []
    for candidate in candidates:
        if not candidate.enabled:
            continue

        if candidate.available_liquidity is not None and candidate.available_liquidity < amount:
            continue

        route = _normalize_route(
            token=token,
            amount=amount,
            protocol=candidate.protocol,
            source="candidate",
            context=context,
            candidate=candidate,
            lender=candidate.lender,
            wrapped_native_token=wrapped_native_token,
            aave_v3_pool=aave_v3_pool,
            morpho_blue=morpho_blue,
        )
        valid.append(route)

    if not valid:
        msg = f"{context}: no flash candidate has enough liquidity for requested amount"
        raise ValueError(msg)

    valid.sort(key=lambda r: r.total_cost_in_borrow_token)
    return valid[0]


def _normalize_route(
    token: Address,
    amount: int,
    protocol: FlashProtocol,
    source: FlashRouteSource,
    context: str,
    lender: Address | None = None,
    candidate: FlashRouteCandidate | None = None,
    wrapped_native_token: Address | None = None,
    aave_v3_pool: Address | None = None,
    morpho_blue: Address | None = None,
) -> ExecutorFlashRoute:
    cost = _calculate_route_cost(
        token=token,
        amount=amount,
        protocol=protocol,
        context=context,
        candidate=candidate,
        wrapped_native_token=wrapped_native_token,
    )

    if protocol == FLASH_PROTOCOL.AAVE_V3:
        canonical = aave_v3_pool or DEFAULT_AAVE_V3_POOL
        _assert_canonical_lender(context, "Aave V3", canonical, lender)
        return _with_cost(protocol, canonical, source, candidate, cost)

    if protocol == FLASH_PROTOCOL.MORPHO:
        canonical = morpho_blue or DEFAULT_MORPHO_BLUE
        _assert_canonical_lender(context, "Morpho Blue", canonical, lender)
        return _with_cost(protocol, canonical, source, candidate, cost)

    if protocol == FLASH_PROTOCOL.ERC3156:
        if lender is None:
            msg = f"{context}: ERC3156 flashProtocol requires explicit flashLender"
            raise ValueError(msg)
        return _with_cost(protocol, lender, source, candidate, cost)

    if protocol == FLASH_PROTOCOL.UNI_V3:
        if lender is None:
            msg = f"{context}: Uniswap V3 flashProtocol requires explicit pool lender"
            raise ValueError(msg)
        return _with_cost(protocol, lender, source, candidate, cost)

    msg = f"{context}: unsupported Executor flashProtocol {protocol}"
    raise ValueError(msg)


def _with_cost(
    protocol: FlashProtocol,
    lender: Address,
    source: FlashRouteSource,
    candidate: FlashRouteCandidate | None,
    cost: Mapping[str, int],
) -> ExecutorFlashRoute:
    return ExecutorFlashRoute(
        protocol=protocol,
        lender=lender,
        source=source,
        available_liquidity=candidate.available_liquidity if candidate else None,
        **cost,
    )


def _calculate_route_cost(
    token: Address,
    amount: int,
    protocol: FlashProtocol,
    context: str,
    candidate: FlashRouteCandidate | None,
    wrapped_native_token: Address | None,
) -> Mapping[str, int]:
    fee_bps = (
        candidate.estimated_fee_bps
        if candidate and candidate.estimated_fee_bps is not None
        else _default_fee_rank_bps(protocol)
    )

    flash_fee = (amount * fee_bps + 9999) // 10000 + (
        candidate.flat_fee if candidate and candidate.flat_fee else 0
    )

    wrapping_cost_wei = _calculate_wrapping_cost_wei(candidate)
    native_gas_cost_wei = (
        candidate.gas_score_wei if candidate and candidate.gas_score_wei else 0
    ) + _calculate_gas_units_cost_wei(candidate)

    native_cost_wei = wrapping_cost_wei + native_gas_cost_wei
    native_cost_in_borrow_token = _convert_native_cost_to_borrow_token(
        context=context,
        token=token,
        native_cost_wei=native_cost_wei,
        candidate=candidate,
        wrapped_native_token=wrapped_native_token,
    )

    total_cost_in_borrow_token = (
        flash_fee
        + native_cost_in_borrow_token
        + (
            candidate.extra_cost_in_borrow_token
            if candidate and candidate.extra_cost_in_borrow_token
            else 0
        )
    )

    return {
        "flash_fee": flash_fee,
        "native_gas_cost_wei": native_gas_cost_wei,
        "wrapping_cost_wei": wrapping_cost_wei,
        "total_cost_in_borrow_token": total_cost_in_borrow_token,
    }


def _calculate_gas_units_cost_wei(candidate: FlashRouteCandidate | None) -> int:
    if not candidate or candidate.gas_units is None or candidate.gas_price_wei is None:
        return 0
    return candidate.gas_units * candidate.gas_price_wei


def _calculate_wrapping_cost_wei(candidate: FlashRouteCandidate | None) -> int:
    if not candidate or candidate.gas_price_wei is None:
        return 0
    wrap_units = candidate.wrap_gas_units if candidate.wrap_native else 0
    if wrap_units is None or (wrap_units == 0 and candidate.wrap_native):
        wrap_units = DEFAULT_WRAP_GAS_UNITS

    unwrap_units = candidate.unwrap_gas_units if candidate.unwrap_native else 0
    if unwrap_units is None or (unwrap_units == 0 and candidate.unwrap_native):
        unwrap_units = DEFAULT_UNWRAP_GAS_UNITS

    return (wrap_units + unwrap_units) * candidate.gas_price_wei


def _convert_native_cost_to_borrow_token(
    context: str,
    token: Address,
    native_cost_wei: int,
    candidate: FlashRouteCandidate | None,
    wrapped_native_token: Address | None,
) -> int:
    if native_cost_wei == 0:
        return 0
    if candidate and candidate.native_cost_in_borrow_token is not None:
        return candidate.native_cost_in_borrow_token

    wrapped_native = wrapped_native_token or DEFAULT_WRAPPED_NATIVE_TOKEN
    if token.lower() == wrapped_native.lower():
        return native_cost_wei

    msg = f"{context}: non-WETH flash route with native gas/wrap cost requires nativeCostInBorrowToken"
    raise ValueError(msg)


def _assert_canonical_lender(
    context: str,
    protocol_name: str,
    canonical: Address,
    explicit: Address | None,
) -> None:
    if explicit is not None and explicit.lower() != canonical.lower():
        msg = f"{context}: {protocol_name} flashLender must match configured Executor pin"
        raise ValueError(msg)


def _default_fee_rank_bps(protocol: FlashProtocol) -> int:
    if protocol == FLASH_PROTOCOL.MORPHO:
        return 0
    if protocol == FLASH_PROTOCOL.AAVE_V3:
        return 5
    if protocol == FLASH_PROTOCOL.UNI_V3:
        return 30
    if protocol == FLASH_PROTOCOL.ERC3156:
        return 1000000  # Max rank
    msg = f"flash source router: unsupported protocol {protocol}"
    raise ValueError(msg)
