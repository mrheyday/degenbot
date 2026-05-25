"""Degenbot IPC adapter.

Runs a Unix-domain-socket NDJSON bridge between the TypeScript coordinator and
the vendored degenbot Python package. Degenbot is the source of market-state and
pathfinding primitives; this adapter owns process supervision and the wire
contract used by the coordinator.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import json
import logging
import os
import stat
import sys
import time
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Protocol, cast

import structlog

from degenbot.adapters.ipc import (  # pylint: disable=useless-import-alias
    ADDRESS_KEYED_DEGENBOT_DEX_KINDS as ADDRESS_KEYED_DEGENBOT_DEX_KINDS,
)
from degenbot.adapters.ipc import (  # pylint: disable=useless-import-alias
    POOL_ID_REQUIRED_DEX_KINDS as POOL_ID_REQUIRED_DEX_KINDS,
)
from degenbot.adapters.ipc import (  # pylint: disable=useless-import-alias
    RECOGNIZED_DEX_KINDS as RECOGNIZED_DEX_KINDS,
)
from degenbot.adapters.config import DegenbotSettings, load_degenbot_settings

type JsonObject = dict[str, Any]
REPO_ROOT = Path(__file__).resolve().parents[3]
ARBITRUM_CHAIN_ID = 42161
ADDRESS_HEX_LEN = 42
BYTES32_HEX_LEN = 66
PAIR_TOKEN_COUNT = 2
V2_TOKEN_SLOTS = 2


@dataclass(frozen=True)
class DegenbotRuntime:
    """Loaded degenbot package metadata."""

    version: str
    source_path: Path


@dataclass(frozen=True)
class SwapStep:
    """One coordinator-provided exact-input swap step."""

    pool: str
    token_in: str
    token_out: str
    amount_in: int
    amount_out_min: int
    zero_for_one: bool
    dex: str
    router: str | None = None
    call_data: str | None = None
    fee: int | None = None
    pool_key: JsonObject | None = None
    hook_data: str | None = None
    deadline: int | None = None
    token_in_idx: int | None = None
    token_out_idx: int | None = None
    is_legacy: bool | None = None


@dataclass(frozen=True)
class SimulationResult:
    """Exact-input path simulation result."""

    amount_in: int
    amount_out: int
    path: tuple[SwapStep, ...]

    @property
    def estimated_profit_wei(self) -> int:
        return max(self.amount_out - self.amount_in, 0)


@dataclass(frozen=True)
class MorphoLiquidationOpportunityEnvelope:
    """Coordinator Opportunity envelope inputs for a Morpho liquidation payload."""

    opportunity_id: str
    detected_at_ns: int
    morpho_blue_address: str
    estimated_profit_wei: int
    flash_amount: int | None = None
    risk_cost_wei: int = 0


@dataclass(frozen=True)
class BotBestOpportunityRequest:
    """Coordinator request for degenbot's ranked pathfinding opportunity."""

    chain_id: int
    input_token: str
    from_address: str
    min_profit: int = 0
    min_depth: int = 2
    max_depth: int | None = None
    max_input: int | None = None
    min_rate_of_exchange: Fraction | None = None


class DegenbotSimulator(Protocol):
    """Simulator interface used by the IPC server.

    Tests can inject this protocol without importing degenbot. Production uses
    `RegistryBackedDegenbotSimulator`, which delegates to hydrated degenbot
    pool objects from `degenbot.pool_registry`.
    """

    def simulate_exact_input_path(self, path: tuple[SwapStep, ...], amount_in: int) -> SimulationResult:
        """Simulate an exact-input path and return final amount out."""
        ...


@dataclass(frozen=True)
class TokenPair:
    """One unordered token-pair subscription from the coordinator."""

    token0: str
    token1: str


class DegenbotSubscriptionSource(Protocol):
    """Source of adapter-to-coordinator subscription events."""

    def subscribe(self, pairs: tuple[TokenPair, ...]) -> AsyncIterator[str]:
        """Yield externally-tagged NDJSON lines for a subscription."""
        ...


class DegenbotOpportunitySource(Protocol):
    """Source of ranked degenbot opportunities."""

    def best_opportunity(self, request: BotBestOpportunityRequest) -> str | None:
        """Return an encoded Opportunity line, or None when no path qualifies."""
        ...


class SimulationInputError(ValueError):
    """Malformed or unsupported simulation request."""


class SimulationUnavailableError(RuntimeError):
    """Simulation could not run because degenbot pool state is unavailable."""


def resolve_degenbot_source_path(source_path: Path) -> Path:
    """Resolve degenbot checkout path from either repo root or solver cwd."""
    if source_path.is_absolute():
        return source_path.resolve()

    candidates = (
        Path.cwd() / source_path,
        REPO_ROOT / source_path,
        REPO_ROOT / "solver" / source_path,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    return (REPO_ROOT / source_path).resolve()


def load_degenbot_runtime(source_path: Path) -> DegenbotRuntime:
    """Import degenbot and return immutable runtime metadata."""
    resolved_source_path = resolve_degenbot_source_path(source_path)
    src_path = resolved_source_path / "src"
    if src_path.exists():
        src_entry = str(src_path)
        if src_entry not in sys.path:
            sys.path.insert(0, src_entry)

    module = importlib.import_module("degenbot")
    version = str(getattr(module, "__version__", "unknown"))
    return DegenbotRuntime(version=version, source_path=resolved_source_path)


def decode_control_message(line: str) -> JsonObject:
    """Decode one inbound coordinator control message."""
    parsed = json.loads(line)
    if not isinstance(parsed, dict):
        raise ValueError("control message must be a JSON object")

    wire = cast("JsonObject", parsed)
    if "kind" in wire and isinstance(wire["kind"], str):
        return wire

    if len(wire) == 1:
        key, value = next(iter(wire.items()))
        if isinstance(key, str):
            payload = cast("JsonObject", value) if isinstance(value, dict) else {}
            return {"kind": key, **payload}

    raise ValueError("control message is missing a kind")


def encode_heartbeat(runtime: DegenbotRuntime) -> str:
    """Encode the adapter heartbeat using the coordinator's expected variant."""
    return json.dumps(
        {
            "Heartbeat": {
                "ts_ms": int(time.time() * 1000),
                "degenbot_version": runtime.version,
                "source_path": str(runtime.source_path),
            },
        },
        separators=(",", ":"),
    )


def encode_error(code: str, message: str, context: JsonObject | None = None) -> str:
    """Encode a degenbot adapter error using the coordinator's expected variant."""
    payload: JsonObject = {"code": code, "message": message}
    if context:
        payload["context"] = context
    return json.dumps({"Error": payload}, separators=(",", ":"))


def parse_simulation_request(msg: JsonObject) -> tuple[tuple[SwapStep, ...], int]:
    """Parse and validate an inbound `Simulate` request."""
    raw_path = msg.get("path")
    if not isinstance(raw_path, list) or not raw_path:
        raise SimulationInputError("Simulate.path must be a non-empty array")

    try:
        amount_in = int(cast("str | int", msg["amount_in"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise SimulationInputError("Simulate.amount_in must be a positive integer string") from exc
    if amount_in <= 0:
        raise SimulationInputError("Simulate.amount_in must be positive")

    steps: list[SwapStep] = []
    for idx, raw_step in enumerate(raw_path):
        if not isinstance(raw_step, dict):
            raise SimulationInputError(f"Simulate.path[{idx}] must be an object")
        step = cast("JsonObject", raw_step)
        try:
            dex = str(step["dex"])
            amount_step_in = int(cast("str | int", step["amount_in"]))
            amount_out_min = int(cast("str | int", step["amount_out_min"]))
            zero_for_one = step["zero_for_one"]
            if not isinstance(zero_for_one, bool):
                raise TypeError("zero_for_one must be bool")
            parsed = SwapStep(
                pool=str(step["pool"]),
                token_in=str(step["token_in"]),
                token_out=str(step["token_out"]),
                amount_in=amount_step_in,
                amount_out_min=amount_out_min,
                zero_for_one=zero_for_one,
                dex=dex,
                router=str(step["router"]) if "router" in step else None,
                call_data=str(step["call_data"]) if "call_data" in step else None,
                fee=_optional_int(step, "fee"),
                pool_key=_optional_pool_key(step.get("pool_key")),
                hook_data=str(step["hook_data"]) if step.get("hook_data") is not None else None,
                deadline=_optional_int(step, "deadline"),
                token_in_idx=_optional_int(step, "token_in_idx"),
                token_out_idx=_optional_int(step, "token_out_idx"),
                is_legacy=_optional_bool(step, "is_legacy"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SimulationInputError(f"Simulate.path[{idx}] is malformed: {exc}") from exc

        if parsed.dex not in RECOGNIZED_DEX_KINDS:
            raise SimulationInputError(f"Simulate.path[{idx}] dex {parsed.dex!r} is not recognized by degenbot IPC")
        if parsed.amount_in <= 0:
            raise SimulationInputError(f"Simulate.path[{idx}].amount_in must be positive")
        if parsed.amount_out_min < 0:
            raise SimulationInputError(f"Simulate.path[{idx}].amount_out_min must be non-negative")
        steps.append(parsed)

    if steps[0].amount_in != amount_in:
        raise SimulationInputError("Simulate.amount_in must equal path[0].amount_in")

    return tuple(steps), amount_in


def _optional_int(payload: JsonObject, key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    return int(cast("str | int", value))


def _optional_bool(payload: JsonObject, key: str) -> bool | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be bool when supplied")
    return value


def _optional_pool_key(value: object) -> JsonObject | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("pool_key must be object when supplied")
    key = cast("JsonObject", value)
    required = ("currency0", "currency1", "fee", "tick_spacing", "hooks")
    missing = [name for name in required if name not in key]
    if missing:
        raise ValueError(f"pool_key missing required fields: {', '.join(missing)}")
    return {
        "currency0": str(key["currency0"]),
        "currency1": str(key["currency1"]),
        "fee": int(cast("str | int", key["fee"])),
        "tick_spacing": int(cast("str | int", key["tick_spacing"])),
        "hooks": str(key["hooks"]),
    }


def _swap_step_to_wire(step: SwapStep) -> JsonObject:
    wire: JsonObject = {
        "pool": step.pool,
        "token_in": step.token_in,
        "token_out": step.token_out,
        "amount_in": str(step.amount_in),
        "amount_out_min": str(step.amount_out_min),
        "zero_for_one": step.zero_for_one,
        "dex": step.dex,
    }
    if step.router is not None:
        wire["router"] = step.router
    if step.call_data is not None:
        wire["call_data"] = step.call_data
    if step.fee is not None:
        wire["fee"] = step.fee
    if step.pool_key is not None:
        wire["pool_key"] = step.pool_key
    if step.hook_data is not None:
        wire["hook_data"] = step.hook_data
    if step.deadline is not None:
        wire["deadline"] = step.deadline
    if step.token_in_idx is not None:
        wire["token_in_idx"] = step.token_in_idx
    if step.token_out_idx is not None:
        wire["token_out_idx"] = step.token_out_idx
    if step.is_legacy is not None:
        wire["is_legacy"] = step.is_legacy
    return wire


def parse_subscribe_request(msg: JsonObject) -> tuple[TokenPair, ...]:
    """Parse and validate an inbound `Subscribe` request."""
    raw_pairs = msg.get("pairs")
    if not isinstance(raw_pairs, list):
        raise SimulationInputError("Subscribe.pairs must be an array")

    pairs: list[TokenPair] = []
    for idx, raw_pair in enumerate(raw_pairs):
        if not isinstance(raw_pair, dict):
            raise SimulationInputError(f"Subscribe.pairs[{idx}] must be an object")
        try:
            token0 = str(raw_pair["token0"])
            token1 = str(raw_pair["token1"])
        except KeyError as exc:
            raise SimulationInputError(f"Subscribe.pairs[{idx}] missing {exc.args[0]}") from exc
        if not _is_address_like(token0) or not _is_address_like(token1):
            raise SimulationInputError(f"Subscribe.pairs[{idx}] token addresses must be 0x-prefixed 20-byte hex")
        if token0.lower() == token1.lower():
            raise SimulationInputError(f"Subscribe.pairs[{idx}] token0 and token1 must differ")
        pairs.append(TokenPair(token0=token0, token1=token1))

    return tuple(pairs)


def parse_best_opportunity_request(msg: JsonObject) -> BotBestOpportunityRequest:
    """Parse and validate an inbound `BestOpportunity` request."""
    try:
        chain_id = int(cast("str | int", msg.get("chain_id", ARBITRUM_CHAIN_ID)))
    except (TypeError, ValueError) as exc:
        raise SimulationInputError("BestOpportunity.chain_id must be a positive integer") from exc
    if chain_id <= 0:
        raise SimulationInputError("BestOpportunity.chain_id must be positive")

    input_token = str(msg.get("input_token", ""))
    if not _is_address_like(input_token):
        raise SimulationInputError("BestOpportunity.input_token must be a 0x-prefixed 20-byte hex address")

    from_address = str(msg.get("from_address", ""))
    if not _is_address_like(from_address):
        raise SimulationInputError("BestOpportunity.from_address must be a 0x-prefixed 20-byte hex address")

    min_profit = _non_negative_int(msg, "min_profit", default=0)
    min_depth = _positive_int(msg, "min_depth", default=2)
    max_depth = _optional_positive_int(msg, "max_depth")
    if max_depth is not None and max_depth < min_depth:
        raise SimulationInputError("BestOpportunity.max_depth must be >= min_depth")
    max_input = _optional_positive_int(msg, "max_input")
    min_rate = _optional_fraction(msg, "min_rate_of_exchange")

    return BotBestOpportunityRequest(
        chain_id=chain_id,
        input_token=input_token,
        from_address=from_address,
        min_profit=min_profit,
        min_depth=min_depth,
        max_depth=max_depth,
        max_input=max_input,
        min_rate_of_exchange=min_rate,
    )


def _non_negative_int(payload: JsonObject, key: str, *, default: int) -> int:
    value = payload.get(key, default)
    try:
        parsed = int(cast("str | int", value))
    except (TypeError, ValueError) as exc:
        raise SimulationInputError(f"BestOpportunity.{key} must be a non-negative integer") from exc
    if parsed < 0:
        raise SimulationInputError(f"BestOpportunity.{key} must be non-negative")
    return parsed


def _positive_int(payload: JsonObject, key: str, *, default: int) -> int:
    value = payload.get(key, default)
    try:
        parsed = int(cast("str | int", value))
    except (TypeError, ValueError) as exc:
        raise SimulationInputError(f"BestOpportunity.{key} must be a positive integer") from exc
    if parsed <= 0:
        raise SimulationInputError(f"BestOpportunity.{key} must be positive")
    return parsed


def _optional_positive_int(payload: JsonObject, key: str) -> int | None:
    if payload.get(key) is None:
        return None
    return _positive_int(payload, key, default=1)


def _optional_fraction(payload: JsonObject, key: str) -> Fraction | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        parsed = Fraction(str(value))
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise SimulationInputError(f"BestOpportunity.{key} must be a positive decimal or fraction string") from exc
    if parsed <= 0:
        raise SimulationInputError(f"BestOpportunity.{key} must be positive")
    return parsed


def encode_opportunity_from_simulation(result: SimulationResult) -> str:
    """Encode a successful simulation as an externally-tagged Opportunity."""
    first = result.path[0]
    last = result.path[-1]
    now_ns = time.time_ns()
    payload: JsonObject = {
        "id": f"sim-{now_ns}",
        "detected_at_ns": str(now_ns),
        "kind": "NativeArb",
        "token_in": first.token_in,
        "token_out": last.token_out,
        "amount_in": str(result.amount_in),
        "expected_amount_out": str(result.amount_out),
        "estimated_profit_wei": str(result.estimated_profit_wei),
        "flash_token": first.token_in,
        "flash_amount": str(result.amount_in),
        "path": [_swap_step_to_wire(step) for step in result.path],
        "pool_addresses": [step.pool for step in result.path],
    }
    return json.dumps({"Opportunity": payload}, separators=(",", ":"))


def encode_opportunity_from_bot(request: BotBestOpportunityRequest, opportunity: object) -> str:
    """Encode a degenbot bot result as a coordinator-native arb Opportunity."""
    opportunity_any = cast("Any", opportunity)
    result = opportunity_any.result
    result_any = cast("Any", result)
    input_amount = int(result_any.input_amount)
    profit_amount = int(result_any.profit_amount)
    if input_amount <= 0:
        raise SimulationUnavailableError("degenbot bot opportunity input_amount must be positive")
    if profit_amount < 0:
        raise SimulationUnavailableError("degenbot bot opportunity profit_amount must be non-negative")

    path = _swap_steps_from_bot_opportunity(opportunity)
    if not path:
        raise SimulationUnavailableError("degenbot bot opportunity has no executable swap path")

    input_token = _token_address(getattr(result, "input_token", None)) or request.input_token
    profit_token = _token_address(getattr(result, "profit_token", None)) or input_token
    now_ns = time.time_ns()
    strategy_id = str(getattr(opportunity, "strategy_id", "degenbot"))
    payload: JsonObject = {
        "id": f"bot-{now_ns}",
        "detected_at_ns": str(now_ns),
        "kind": "NativeArb",
        "token_in": input_token,
        "token_out": profit_token,
        "amount_in": str(input_amount),
        "expected_amount_out": str(input_amount + profit_amount),
        "estimated_profit_wei": str(profit_amount),
        "flash_token": input_token,
        "flash_amount": str(input_amount),
        "path": [_swap_step_to_wire(step) for step in path],
        "pool_addresses": [step.pool for step in path],
        "strategy_id": strategy_id,
        "state_block": _optional_state_block(result),
    }
    return json.dumps({"Opportunity": payload}, separators=(",", ":"))


def _swap_steps_from_bot_opportunity(opportunity: object) -> tuple[SwapStep, ...]:
    opportunity_any = cast("Any", opportunity)
    result = opportunity_any.result
    result_any = cast("Any", result)
    raw_amounts = getattr(result_any, "swap_amounts", ())
    raw_pools = getattr(opportunity_any, "swap_pools", ())
    if not isinstance(raw_amounts, Iterable) or not isinstance(raw_pools, Iterable):
        raise SimulationUnavailableError("degenbot bot opportunity exposes invalid swap path metadata")

    amounts = tuple(raw_amounts)
    pools = tuple(raw_pools)
    if len(amounts) != len(pools):
        raise SimulationUnavailableError("degenbot bot opportunity swap_pools length does not match swap_amounts")

    steps: list[SwapStep] = []
    for pool, amounts_for_pool in zip(pools, amounts, strict=True):
        steps.append(_swap_step_from_degenbot_pool_amounts(pool, amounts_for_pool))
    return tuple(steps)


def _swap_step_from_degenbot_pool_amounts(pool: object, amounts: object) -> SwapStep:
    pool_address = str(getattr(amounts, "pool", getattr(amounts, "address", getattr(pool, "address", ""))))
    if not _is_address_like(pool_address):
        raise SimulationUnavailableError(f"degenbot bot pool address is invalid: {pool_address!r}")

    if hasattr(amounts, "amounts_in") and hasattr(amounts, "amounts_out"):
        amount_any = cast("Any", amounts)
        amounts_in = tuple(int(value) for value in amount_any.amounts_in)
        amounts_out = tuple(int(value) for value in amount_any.amounts_out)
        if len(amounts_in) != V2_TOKEN_SLOTS or len(amounts_out) != V2_TOKEN_SLOTS:
            raise SimulationUnavailableError("V2 swap amounts must have two input and output slots")
        zero_for_one = amounts_in[0] > 0
        token_in_attr = "token0" if zero_for_one else "token1"
        token_out_attr = "token1" if zero_for_one else "token0"
        amount_in = amounts_in[0] if zero_for_one else amounts_in[1]
        amount_out = amounts_out[1] if zero_for_one else amounts_out[0]
        return SwapStep(
            pool=pool_address,
            token_in=_pool_token_address(pool, token_in_attr),
            token_out=_pool_token_address(pool, token_out_attr),
            amount_in=amount_in,
            amount_out_min=amount_out,
            zero_for_one=zero_for_one,
            dex=_dex_kind_from_pool(pool),
        )

    if hasattr(amounts, "token_in_index") and hasattr(amounts, "token_out_index"):
        amount_any = cast("Any", amounts)
        return SwapStep(
            pool=pool_address,
            token_in=_token_address_or_raise(amount_any.token_in),
            token_out=_token_address_or_raise(amount_any.token_out),
            amount_in=int(amount_any.amount_in),
            amount_out_min=int(amount_any.min_amount_out),
            zero_for_one=bool(int(amount_any.token_in_index) < int(amount_any.token_out_index)),
            dex="Curve",
            token_in_idx=int(amount_any.token_in_index),
            token_out_idx=int(amount_any.token_out_index),
            is_legacy=True,
        )

    if hasattr(amounts, "amount_in") and hasattr(amounts, "amount_out") and hasattr(amounts, "zero_for_one"):
        amount_any = cast("Any", amounts)
        zero_for_one = bool(amount_any.zero_for_one)
        pool_key = _optional_v4_pool_key(pool)
        return SwapStep(
            pool=pool_address,
            token_in=_pool_token_address(pool, "token0" if zero_for_one else "token1"),
            token_out=_pool_token_address(pool, "token1" if zero_for_one else "token0"),
            amount_in=int(amount_any.amount_in),
            amount_out_min=int(amount_any.amount_out),
            zero_for_one=zero_for_one,
            dex=_dex_kind_from_pool(pool),
            fee=_optional_pool_fee(pool),
            pool_key=pool_key,
            hook_data="0x" if pool_key is not None else None,
        )

    raise SimulationUnavailableError(f"unsupported degenbot bot swap amount type: {type(amounts).__name__}")


def _pool_token_address(pool: object, attr: str) -> str:
    token = getattr(pool, attr, None)
    if token is None:
        raise SimulationUnavailableError(f"pool {getattr(pool, 'address', '<unknown>')} missing {attr}")
    return _token_address_or_raise(token)


def _token_address_or_raise(token: object) -> str:
    address = _token_address(token)
    if address is None:
        raise SimulationUnavailableError(f"invalid token address on degenbot object: {token!r}")
    return address


def _dex_kind_from_pool(pool: object) -> str:
    class_name = type(pool).__name__
    lowered = class_name.lower()
    dex_kind: str | None = None
    for parts, candidate in (
        (("curve",), "Curve"),
        (("camelot", "v2"), "CamelotV2"),
        (("pancake", "v3"), "PancakeSwapV3"),
        (("pancake", "v2"), "PancakeSwapV2"),
        (("sushi", "v3"), "SushiSwapV3"),
        (("sushi", "v2"), "SushiSwapV2"),
        (("v4",), "UniswapV4"),
        (("v3",), "UniswapV3"),
        (("v2",), "UniswapV2"),
    ):
        if all(part in lowered for part in parts):
            dex_kind = candidate
            break
    if dex_kind is None:
        raise SimulationUnavailableError(f"unsupported degenbot bot pool type: {class_name}")
    return dex_kind


def _optional_pool_fee(pool: object) -> int | None:
    value = getattr(pool, "fee", None)
    return None if value is None else int(value)


def _optional_v4_pool_key(pool: object) -> JsonObject | None:
    key = getattr(pool, "pool_key", None)
    if key is None:
        return None
    fee = _first_present_attr(key, ("fee",), default=_first_present_attr(pool, ("fee",), default=None))
    tick_spacing = _first_present_attr(
        key,
        ("tick_spacing",),
        default=_first_present_attr(pool, ("tick_spacing",), default=None),
    )
    return {
        "currency0": _token_address_or_raise(getattr(key, "currency0", getattr(pool, "token0", None))),
        "currency1": _token_address_or_raise(getattr(key, "currency1", getattr(pool, "token1", None))),
        "fee": _object_to_int(fee, "pool_key.fee"),
        "tick_spacing": _object_to_int(tick_spacing, "pool_key.tick_spacing"),
        "hooks": _token_address_or_raise(getattr(key, "hooks", getattr(pool, "hooks", None))),
    }


def _optional_state_block(result: object) -> str | None:
    state_block = getattr(result, "state_block", None)
    return None if state_block is None else str(int(state_block))


def _object_to_int(value: object, field_name: str) -> int:
    if value is None:
        raise SimulationUnavailableError(f"{field_name} is required")
    return int(cast("Any", value))


def encode_morpho_liquidation_opportunity(
    payload: JsonObject,
    envelope: MorphoLiquidationOpportunityEnvelope,
) -> str:
    """Wrap a Morpho standard-liquidation payload as an IPC Opportunity.

    Morpho protocol-specific fields are built in `morpho_lp_adapter.py`. This
    helper owns only the degenbot/coordinator wire envelope and emits the same
    externally-tagged kind shape decoded by `coordinator/src/ipc/client.ts`.
    """
    if envelope.opportunity_id == "":
        raise ValueError("opportunity_id must be non-empty")
    if envelope.detected_at_ns < 0:
        raise ValueError(f"detected_at_ns must be non-negative, got {envelope.detected_at_ns}")
    if envelope.estimated_profit_wei < 0:
        raise ValueError(f"estimated_profit_wei must be non-negative, got {envelope.estimated_profit_wei}")
    if envelope.flash_amount is not None and envelope.flash_amount <= 0:
        raise ValueError(f"flash_amount must be positive when provided, got {envelope.flash_amount}")
    if envelope.risk_cost_wei < 0:
        raise ValueError(f"risk_cost_wei must be non-negative, got {envelope.risk_cost_wei}")
    _validate_morpho_liquidation_payload(payload)

    loan_token = _required_str(payload, "loanToken")
    collateral_token = _required_str(payload, "collateralToken")
    repay_assets = _required_str(payload, "repayAssets")
    expected_seized_assets = _required_str(payload, "expectedCollateralSeized")
    if expected_seized_assets == "None":
        raise ValueError("expectedCollateralSeized is required for coordinator Morpho liquidation opportunities")
    ranking_score_bps = str(payload.get("rankingScoreBps", payload.get("liquidationBonusBps", 0)))
    resolved_flash_amount = str(envelope.flash_amount) if envelope.flash_amount is not None else repay_assets

    opportunity: JsonObject = {
        "id": envelope.opportunity_id,
        "detected_at_ns": str(envelope.detected_at_ns),
        "kind": {
            "MorphoLiquidation": {
                "market_id": _required_str(payload, "marketId"),
                "market_params": _market_params_to_wire(cast("JsonObject", payload["marketParams"])),
                "borrower": _required_str(payload, "borrower"),
                "repaid_shares": _required_str(payload, "repaidShares"),
                "expected_seized_assets": expected_seized_assets,
                "ranking_score_bps": ranking_score_bps,
                "risk_cost_wei": str(envelope.risk_cost_wei),
                "bad_debt_mode": _bad_debt_mode_from_classification(_required_str(payload, "badDebtClassification")),
            },
        },
        "token_in": loan_token,
        "token_out": collateral_token,
        "amount_in": repay_assets,
        "expected_amount_out": expected_seized_assets,
        "estimated_profit_wei": str(envelope.estimated_profit_wei),
        "flash_token": loan_token,
        "flash_amount": resolved_flash_amount,
        "path": [],
        "pool_addresses": [envelope.morpho_blue_address],
    }
    return json.dumps({"Opportunity": opportunity}, separators=(",", ":"))


def encode_pool_update_from_degenbot(publisher: object, message: object | None = None) -> str:
    """Encode a degenbot pool-state notification as coordinator `PoolUpdate`.

    Degenbot pool classes publish typed `PoolStateMessage` variants with a
    `.state` payload. Tests and some adapters can pass a pool object directly;
    in that case we fall back to `publisher.state`.
    """
    state = getattr(message, "state", None) if message is not None else None
    if state is None:
        state = getattr(publisher, "state", None)
    if state is None:
        raise ValueError("pool update has no state")

    address = str(getattr(state, "address", getattr(publisher, "address", "")))
    if not _is_address_like(address):
        raise ValueError(f"pool update address is invalid: {address!r}")

    block_number = getattr(state, "block", None)
    reserves = _encode_reserves_from_pool_state(publisher, state)
    payload: JsonObject = {
        "address": address,
        "block_number": str(0 if block_number is None else int(block_number)),
        "reserves": reserves,
    }
    return json.dumps({"PoolUpdate": payload}, separators=(",", ":"))


def decode_morpho_liquidation_opportunity(line: str) -> JsonObject:
    """Decode and validate an externally-tagged Morpho liquidation Opportunity."""
    parsed = json.loads(line)
    if not isinstance(parsed, dict):
        raise ValueError("Morpho liquidation opportunity must be a JSON object")
    envelope = cast("JsonObject", parsed)
    raw_opportunity = envelope.get("Opportunity")
    if not isinstance(raw_opportunity, dict):
        raise ValueError("Morpho liquidation opportunity is missing Opportunity envelope")
    opportunity = cast("JsonObject", raw_opportunity)
    raw_kind = opportunity.get("kind")
    if not isinstance(raw_kind, dict) or "MorphoLiquidation" not in raw_kind:
        raise ValueError("Opportunity.kind must contain MorphoLiquidation")
    raw_payload = raw_kind["MorphoLiquidation"]
    if not isinstance(raw_payload, dict):
        raise ValueError("Opportunity.kind.MorphoLiquidation must be an object")
    _validate_morpho_liquidation_wire_opportunity(opportunity, cast("JsonObject", raw_payload))
    return opportunity


def _validate_morpho_liquidation_payload(payload: JsonObject) -> None:
    required_keys = (
        "marketId",
        "marketParams",
        "borrower",
        "repaidShares",
        "loanToken",
        "collateralToken",
        "expectedCollateralSeized",
        "rankingScoreUsd",
        "riskCosts",
        "badDebtClassification",
    )
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ValueError("Morpho liquidation payload missing required keys: " + ", ".join(missing))
    if payload["badDebtClassification"] not in {"collateralized", "bad_debt"}:
        raise ValueError("badDebtClassification must be collateralized or bad_debt")
    if not isinstance(payload["marketParams"], dict):
        raise ValueError("marketParams must be an object")
    if not isinstance(payload["riskCosts"], dict):
        raise ValueError("riskCosts must be an object")


def _validate_morpho_liquidation_wire_opportunity(opportunity: JsonObject, payload: JsonObject) -> None:
    required_opportunity_keys = (
        "id",
        "detected_at_ns",
        "token_in",
        "token_out",
        "amount_in",
        "expected_amount_out",
        "estimated_profit_wei",
        "flash_token",
        "flash_amount",
        "path",
        "pool_addresses",
    )
    missing_opportunity_keys = [key for key in required_opportunity_keys if key not in opportunity]
    if missing_opportunity_keys:
        raise ValueError(
            "Morpho liquidation opportunity missing required keys: " + ", ".join(missing_opportunity_keys),
        )

    required_payload_keys = (
        "market_id",
        "market_params",
        "borrower",
        "repaid_shares",
        "expected_seized_assets",
        "ranking_score_bps",
        "risk_cost_wei",
        "bad_debt_mode",
    )
    missing_payload_keys = [key for key in required_payload_keys if key not in payload]
    if missing_payload_keys:
        raise ValueError(
            "Morpho liquidation kind payload missing required keys: " + ", ".join(missing_payload_keys),
        )
    if payload["bad_debt_mode"] not in {"none", "allow_profitable", "realize_anyway"}:
        raise ValueError("bad_debt_mode must be none, allow_profitable, or realize_anyway")
    if not isinstance(payload["market_params"], dict):
        raise ValueError("market_params must be an object")
    if not isinstance(opportunity["path"], list):
        raise ValueError("path must be an array")
    if not isinstance(opportunity["pool_addresses"], list) or not opportunity["pool_addresses"]:
        raise ValueError("pool_addresses must be a non-empty array")


def _required_str(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    if value is None:
        raise ValueError(f"Morpho liquidation payload field {key} is required")
    return str(value)


def _market_params_to_wire(market_params: JsonObject) -> JsonObject:
    return {
        "loan_token": _required_str(market_params, "loanToken"),
        "collateral_token": _required_str(market_params, "collateralToken"),
        "oracle": _required_str(market_params, "oracle"),
        "irm": _required_str(market_params, "irm"),
        "lltv": _required_str(market_params, "lltv"),
    }


def _bad_debt_mode_from_classification(classification: str) -> str:
    if classification == "collateralized":
        return "none"
    if classification == "bad_debt":
        return "allow_profitable"
    raise ValueError("badDebtClassification must be collateralized or bad_debt")


def _is_address_like(value: str) -> bool:
    return (
        value.startswith("0x")
        and len(value) == ADDRESS_HEX_LEN
        and all(c in "0123456789abcdefABCDEF" for c in value[2:])
    )


def _pair_key(token0: str, token1: str) -> frozenset[str]:
    return frozenset((token0.lower(), token1.lower()))


def _pool_registry_key_matches_chain(key: object, chain_id: int) -> bool:
    return isinstance(key, tuple) and len(key) >= 1 and key[0] == chain_id


def _token_address(value: object) -> str | None:
    if value is None:
        return None
    address = getattr(value, "address", value)
    text = str(address)
    return text.lower() if _is_address_like(text) else None


def _pool_token_set(pool: object) -> frozenset[str] | None:
    token0 = _token_address(getattr(pool, "token0", None))
    token1 = _token_address(getattr(pool, "token1", None))
    if token0 is not None and token1 is not None:
        return _pair_key(token0, token1)

    raw_tokens = getattr(pool, "tokens", None)
    if isinstance(raw_tokens, Iterable) and not isinstance(raw_tokens, (bytes, str)):
        tokens: list[str] = []
        for token in raw_tokens:
            token_address = _token_address(token)
            if token_address is not None:
                tokens.append(token_address)
        if len(tokens) >= PAIR_TOKEN_COUNT:
            return frozenset(tokens)

    return None


def _encode_reserves_from_pool_state(pool: object, state: object) -> JsonObject:
    if hasattr(state, "reserves_token0") and hasattr(state, "reserves_token1"):
        state_any = cast("Any", state)
        return {
            "V2": {
                "reserve0": str(int(state_any.reserves_token0)),
                "reserve1": str(int(state_any.reserves_token1)),
            },
        }

    if hasattr(state, "sqrt_price_x96") and hasattr(state, "liquidity") and hasattr(state, "tick"):
        state_any = cast("Any", state)
        base: JsonObject = {
            "sqrt_price_x96": str(int(state_any.sqrt_price_x96)),
            "liquidity": str(int(state_any.liquidity)),
            "tick": int(state_any.tick),
        }
        pool_id = getattr(state, "id", None) or getattr(pool, "pool_id", None)
        if pool_id is not None:
            return {"V4": {"key": _bytes32_hex(pool_id), **base}}
        return {"V3": base}

    if hasattr(state, "balances"):
        balances = cast("Any", state).balances
        if not isinstance(balances, Iterable):
            raise ValueError("Curve pool state balances must be iterable")
        amplification = _first_present_attr(pool, ("A", "amplification_coefficient", "_A"), default=0)
        return {
            "Curve": {
                "balances": [str(int(balance)) for balance in balances],
                "A": str(_object_to_int(amplification, "Curve.A")),
                "fee": _object_to_int(_first_present_attr(pool, ("fee", "_fee"), default=0), "Curve.fee"),
            },
        }

    raise ValueError(f"unsupported degenbot pool state type: {type(state).__name__}")


def _bytes32_hex(value: object) -> str:
    if hasattr(value, "to_0x_hex"):
        text = str(value.to_0x_hex())
    elif isinstance(value, bytes):
        text = "0x" + value.hex()
    else:
        text = str(value)

    if not text.startswith("0x"):
        text = "0x" + text
    if len(text) != BYTES32_HEX_LEN:
        raise ValueError(f"expected 32-byte hex value, got {text!r}")
    return text.lower()


def _first_present_attr(obj: object, names: tuple[str, ...], *, default: object) -> object:
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


class RegistryBackedDegenbotSimulator:
    """Exact-input simulator backed by degenbot's in-memory pool registry."""

    def __init__(self, *, chain_id: int = ARBITRUM_CHAIN_ID) -> None:
        self._chain_id = chain_id

    def simulate_exact_input_path(self, path: tuple[SwapStep, ...], amount_in: int) -> SimulationResult:
        running_amount = amount_in
        normalized_steps: list[SwapStep] = []
        override_states: dict[str, object] = {}

        for raw_step in path:
            if raw_step.dex in POOL_ID_REQUIRED_DEX_KINDS:
                raise SimulationUnavailableError(f"dex {raw_step.dex!r} requires a pool-id-aware IPC wire format")
            if raw_step.dex not in ADDRESS_KEYED_DEGENBOT_DEX_KINDS:
                raise SimulationUnavailableError(
                    f"dex {raw_step.dex!r} is recognized but does not have an enabled degenbot pool adapter yet"
                )
            step = SwapStep(
                pool=raw_step.pool,
                token_in=raw_step.token_in,
                token_out=raw_step.token_out,
                amount_in=running_amount,
                amount_out_min=raw_step.amount_out_min,
                zero_for_one=raw_step.zero_for_one,
                dex=raw_step.dex,
                router=raw_step.router,
                call_data=raw_step.call_data,
                fee=raw_step.fee,
                pool_key=raw_step.pool_key,
                hook_data=raw_step.hook_data,
                deadline=raw_step.deadline,
                token_in_idx=raw_step.token_in_idx,
                token_out_idx=raw_step.token_out_idx,
                is_legacy=raw_step.is_legacy,
            )
            running_amount = self._simulate_step(step, override_states)
            if running_amount < step.amount_out_min:
                raise SimulationUnavailableError(
                    f"simulated amount_out {running_amount} below min {step.amount_out_min} for pool {step.pool}"
                )
            normalized_steps.append(step)

        return SimulationResult(
            amount_in=amount_in,
            amount_out=running_amount,
            path=tuple(normalized_steps),
        )

    def _simulate_step(self, step: SwapStep, override_states: dict[str, object]) -> int:
        try:
            pool_registry = importlib.import_module("degenbot.registry").pool_registry
        except (AttributeError, ImportError) as exc:  # pragma: no cover - production config issue
            raise SimulationUnavailableError("degenbot registry is not importable") from exc

        pool = pool_registry.get(chain_id=self._chain_id, pool_address=step.pool)
        if pool is None:
            raise SimulationUnavailableError(f"pool {step.pool} is not loaded in degenbot registry")

        token_in = self._resolve_pool_token(pool, step.token_in)
        token_out = self._resolve_pool_token(pool, step.token_out)
        override_state = override_states.get(step.pool.lower())

        try:
            if hasattr(pool, "simulate_exact_input_swap"):
                result = pool.simulate_exact_input_swap(
                    token_in=token_in,
                    token_in_quantity=step.amount_in,
                    override_state=override_state,
                )
                override_states[step.pool.lower()] = getattr(result, "final_state", None)
                return self._amount_out_from_delta(
                    result,
                    token_out_index=0 if token_out is getattr(pool, "token0", None) else 1,
                )

            amount_out = pool.calculate_tokens_out_from_tokens_in(
                token_in=token_in,
                token_out=token_out,
                token_in_quantity=step.amount_in,
                override_state=override_state,
            )
        except TypeError:
            amount_out = pool.calculate_tokens_out_from_tokens_in(
                token_in=token_in,
                token_in_quantity=step.amount_in,
                override_state=override_state,
            )
        except Exception as exc:  # pragma: no cover - degenbot pool-specific failure
            raise SimulationUnavailableError(f"degenbot simulation failed for pool {step.pool}: {exc}") from exc

        if not isinstance(amount_out, int) or amount_out < 0:
            raise SimulationUnavailableError(f"degenbot returned invalid amount_out for pool {step.pool}")
        return amount_out

    @staticmethod
    def _resolve_pool_token(pool: object, token_address: str) -> object:
        target = token_address.lower()
        for attr in ("token0", "token1"):
            token = getattr(pool, attr, None)
            if token is not None and str(getattr(token, "address", "")).lower() == target:
                return token
        for token in getattr(pool, "tokens", ()):
            if str(getattr(token, "address", "")).lower() == target:
                return token
        pool_address = getattr(pool, "address", "<unknown>")
        raise SimulationUnavailableError(
            f"token {token_address} is not part of pool {pool_address}",
        )

    @staticmethod
    def _amount_out_from_delta(result: object, *, token_out_index: int) -> int:
        amount0_delta = getattr(result, "amount0_delta", None)
        amount1_delta = getattr(result, "amount1_delta", None)
        if isinstance(amount0_delta, int) and isinstance(amount1_delta, int):
            delta = amount1_delta if token_out_index == 1 else amount0_delta
            if delta >= 0:
                raise SimulationUnavailableError("degenbot simulation did not produce negative output delta")
            return -delta

        raise SimulationUnavailableError("degenbot simulation result has no token delta fields")


class RegistryBackedDegenbotSubscriptionSource:
    """Subscribe to loaded degenbot pool publishers and emit IPC updates."""

    def __init__(self, *, chain_id: int = ARBITRUM_CHAIN_ID) -> None:
        self._chain_id = chain_id

    async def subscribe(self, pairs: tuple[TokenPair, ...]) -> AsyncIterator[str]:
        try:
            pools = self._matching_pools(pairs)
        except SimulationUnavailableError as exc:
            yield encode_error("subscription_unavailable", str(exc))
            return

        if not pools:
            yield encode_error(
                "subscription_unavailable",
                "no loaded degenbot pools match subscribed token pairs",
                {
                    "pair_count": len(pairs),
                    "chain_id": self._chain_id,
                },
            )
            return

        queue: asyncio.Queue[str] = asyncio.Queue()
        subscriber = _PoolUpdateSubscriber(queue)
        subscribed: list[object] = []
        for pool in pools:
            subscribe = getattr(pool, "subscribe", None)
            if not callable(subscribe):
                continue
            subscribe(subscriber)
            subscribed.append(pool)

            try:
                yield encode_pool_update_from_degenbot(pool)
            except ValueError:
                # Some pool classes hydrate state lazily. Live notifications
                # still flow once degenbot publishes the first state update.
                continue

        if not subscribed:
            yield encode_error(
                "subscription_unavailable",
                "matching degenbot pools are not publishers",
                {
                    "pair_count": len(pairs),
                    "chain_id": self._chain_id,
                },
            )
            return

        try:
            while True:
                yield await queue.get()
        finally:
            for pool in subscribed:
                unsubscribe = getattr(pool, "unsubscribe", None)
                if callable(unsubscribe):
                    unsubscribe(subscriber)

    def _matching_pools(self, pairs: tuple[TokenPair, ...]) -> tuple[object, ...]:
        try:
            pool_registry = importlib.import_module("degenbot.registry").pool_registry
        except (AttributeError, ImportError) as exc:  # pragma: no cover - production config issue
            raise SimulationUnavailableError("degenbot registry is not importable") from exc

        raw_pools = getattr(pool_registry, "_all_pools", None)
        if not isinstance(raw_pools, dict):
            raise SimulationUnavailableError("degenbot pool registry does not expose loaded pools")

        pair_keys = {_pair_key(pair.token0, pair.token1) for pair in pairs}
        out: list[object] = []
        seen: set[int] = set()
        for key, pool in raw_pools.items():
            if not _pool_registry_key_matches_chain(key, self._chain_id):
                continue
            pool_tokens = _pool_token_set(pool)
            if pool_tokens is None or not any(pair_key.issubset(pool_tokens) for pair_key in pair_keys):
                continue
            pool_identity = id(pool)
            if pool_identity in seen:
                continue
            seen.add(pool_identity)
            out.append(pool)

        return tuple(out)


class PathfindingDegenbotOpportunitySource:
    """Rank native-arb opportunities with degenbot's pathfinding bot."""

    def best_opportunity(self, request: BotBestOpportunityRequest) -> str | None:
        try:
            bot_module = importlib.import_module("degenbot.bot")
        except ImportError as exc:  # pragma: no cover - production configuration issue
            raise SimulationUnavailableError("degenbot bot module is not importable") from exc

        bot = bot_module.DegenbotBot.from_pathfinding(
            chain_id=request.chain_id,
            input_token=request.input_token,
            min_depth=request.min_depth,
            max_depth=request.max_depth,
            max_input=request.max_input,
        )
        config = bot_module.BotScanConfig(
            from_address=request.from_address,
            min_profit=request.min_profit,
            min_rate_of_exchange=request.min_rate_of_exchange,
        )
        opportunity = bot.best(config=config)
        if opportunity is None:
            return None
        return encode_opportunity_from_bot(request, opportunity)


class _PoolUpdateSubscriber:
    """Degenbot Subscriber that forwards pool updates into an asyncio queue."""

    def __init__(self, queue: asyncio.Queue[str]) -> None:
        self._queue = queue
        self._loop = asyncio.get_running_loop()

    def notify(self, publisher: object, message: object) -> None:
        try:
            line = encode_pool_update_from_degenbot(publisher, message)
        except Exception as exc:  # pylint: disable=broad-exception-caught  # pragma: no cover
            line = encode_error(
                "pool_update_encode_failed",
                str(exc),
                {"pool": str(getattr(publisher, "address", "<unknown>"))},
            )

        # A closing event loop is safer to drop the update into than to raise
        # back into degenbot's publisher callback.
        with contextlib.suppress(RuntimeError):
            self._loop.call_soon_threadsafe(self._queue.put_nowait, line)


class DegenbotIpcServer:
    """Unix-socket NDJSON server for degenbot/coordinator integration."""

    def __init__(
        self,
        settings: DegenbotSettings,
        runtime: DegenbotRuntime,
        simulator: DegenbotSimulator | None = None,
        subscription_source: DegenbotSubscriptionSource | None = None,
        opportunity_source: DegenbotOpportunitySource | None = None,
    ) -> None:
        self._settings = settings
        self._runtime = runtime
        self._simulator = simulator if simulator is not None else RegistryBackedDegenbotSimulator()
        self._subscription_source = (
            subscription_source if subscription_source is not None else RegistryBackedDegenbotSubscriptionSource()
        )
        self._opportunity_source = (
            opportunity_source if opportunity_source is not None else PathfindingDegenbotOpportunitySource()
        )
        self._log = structlog.get_logger(__name__).bind(
            service="degenbot",
            component="execution.degenbot_ipc",
        )

    async def run_forever(self) -> None:
        """Start the Unix socket and serve until cancelled."""
        socket_path = Path(self._settings.degenbot_ipc_socket_path)
        self._prepare_socket_path(socket_path)

        server = await asyncio.start_unix_server(self._handle_client, path=str(socket_path))
        self._log.info(
            "degenbot_ipc_started",
            socket_path=str(socket_path),
            degenbot_version=self._runtime.version,
            degenbot_source=str(self._runtime.source_path),
        )

        async with server:
            await server.serve_forever()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername")
        self._log.info("degenbot_ipc_client_connected", peer=peer)
        write_lock = asyncio.Lock()
        heartbeat = asyncio.create_task(self._heartbeat_loop(writer, write_lock))
        subscription: asyncio.Task[None] | None = None
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                subscription = await self._handle_line(
                    line.decode("utf-8").strip(),
                    writer,
                    write_lock,
                    subscription,
                )
        finally:
            heartbeat.cancel()
            if subscription is not None:
                subscription.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
            if subscription is not None:
                with contextlib.suppress(asyncio.CancelledError):
                    await subscription
            writer.close()
            await writer.wait_closed()
            self._log.info("degenbot_ipc_client_closed", peer=peer)

    async def _handle_line(
        self,
        line: str,
        writer: asyncio.StreamWriter,
        write_lock: asyncio.Lock,
        subscription: asyncio.Task[None] | None,
    ) -> asyncio.Task[None] | None:
        if not line:
            return subscription

        try:
            msg = decode_control_message(line)
        except (ValueError, json.JSONDecodeError) as exc:
            await self._write_line(writer, encode_error("bad_control_message", str(exc)), write_lock)
            return subscription

        kind_value = msg.get("kind")
        if not isinstance(kind_value, str):
            await self._write_line(
                writer,
                encode_error("bad_control_message", "control kind must be a string"),
                write_lock,
            )
            return subscription

        kind = kind_value
        match kind:
            case "Ping":
                await self._write_line(writer, encode_heartbeat(self._runtime), write_lock)
            case "Subscribe":
                subscription = await self._handle_subscribe(msg, writer, write_lock, subscription)
            case "Simulate":
                await self._handle_simulate(msg, writer, write_lock)
            case "BestOpportunity":
                await self._handle_best_opportunity(msg, writer, write_lock)
            case _:
                await self._write_line(
                    writer,
                    encode_error("unsupported_control_message", f"unsupported control kind: {kind}"),
                    write_lock,
                )
        return subscription

    async def _handle_subscribe(
        self,
        msg: JsonObject,
        writer: asyncio.StreamWriter,
        write_lock: asyncio.Lock,
        subscription: asyncio.Task[None] | None,
    ) -> asyncio.Task[None] | None:
        try:
            pairs = parse_subscribe_request(msg)
        except SimulationInputError as exc:
            await self._write_line(
                writer,
                encode_error("bad_subscribe_request", str(exc), {"degenbot_version": self._runtime.version}),
                write_lock,
            )
            return subscription

        if subscription is not None:
            subscription.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await subscription

        self._log.info("degenbot_subscription_updated", pair_count=len(pairs))
        if not pairs:
            return None

        return asyncio.create_task(self._subscription_loop(pairs, writer, write_lock))

    async def _handle_simulate(
        self,
        msg: JsonObject,
        writer: asyncio.StreamWriter,
        write_lock: asyncio.Lock,
    ) -> None:
        try:
            path, amount_in = parse_simulation_request(msg)
            result = self._simulator.simulate_exact_input_path(path, amount_in)
        except SimulationInputError as exc:
            await self._write_line(
                writer,
                encode_error("bad_simulation_request", str(exc), {"degenbot_version": self._runtime.version}),
                write_lock,
            )
            return
        except SimulationUnavailableError as exc:
            await self._write_line(
                writer,
                encode_error("simulation_unavailable", str(exc), {"degenbot_version": self._runtime.version}),
                write_lock,
            )
            return

        await self._write_line(writer, encode_opportunity_from_simulation(result), write_lock)

    async def _handle_best_opportunity(
        self,
        msg: JsonObject,
        writer: asyncio.StreamWriter,
        write_lock: asyncio.Lock,
    ) -> None:
        try:
            request = parse_best_opportunity_request(msg)
            line = self._opportunity_source.best_opportunity(request)
        except SimulationInputError as exc:
            await self._write_line(
                writer,
                encode_error("bad_opportunity_request", str(exc), {"degenbot_version": self._runtime.version}),
                write_lock,
            )
            return
        except SimulationUnavailableError as exc:
            await self._write_line(
                writer,
                encode_error("opportunity_unavailable", str(exc), {"degenbot_version": self._runtime.version}),
                write_lock,
            )
            return

        if line is None:
            await self._write_line(
                writer,
                encode_error(
                    "no_opportunity",
                    "degenbot found no opportunity matching the requested policy",
                    {"degenbot_version": self._runtime.version},
                ),
                write_lock,
            )
            return

        await self._write_line(writer, line, write_lock)

    async def _subscription_loop(
        self,
        pairs: tuple[TokenPair, ...],
        writer: asyncio.StreamWriter,
        write_lock: asyncio.Lock,
    ) -> None:
        try:
            async for line in self._subscription_source.subscribe(pairs):
                await self._write_line(writer, line, write_lock)
        except asyncio.CancelledError:  # pylint: disable=try-except-raise
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            await self._write_line(
                writer,
                encode_error(
                    "subscription_failed",
                    str(exc),
                    {
                        "degenbot_version": self._runtime.version,
                        "pair_count": len(pairs),
                    },
                ),
                write_lock,
            )

    async def _heartbeat_loop(self, writer: asyncio.StreamWriter, write_lock: asyncio.Lock) -> None:
        interval = self._settings.degenbot_heartbeat_interval_sec
        while True:
            await self._write_line(writer, encode_heartbeat(self._runtime), write_lock)
            await asyncio.sleep(interval)

    async def _write_line(
        self,
        writer: asyncio.StreamWriter,
        line: str,
        write_lock: asyncio.Lock,
    ) -> None:
        async with write_lock:
            writer.write(f"{line}\n".encode())
            await writer.drain()

    @staticmethod
    def _prepare_socket_path(socket_path: Path) -> None:
        socket_path.parent.mkdir(parents=True, exist_ok=True)
        if not socket_path.exists():
            return

        mode = socket_path.stat().st_mode
        if stat.S_ISSOCK(mode):
            socket_path.unlink()
            return

        raise RuntimeError(f"refusing to replace non-socket path: {socket_path}")


def configure_logging(level: str) -> None:
    """Configure JSON logging for the adapter process."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def main() -> None:
    """Async console entrypoint."""
    settings = load_degenbot_settings()
    configure_logging(settings.log_level)

    os.environ.setdefault("DEGENBOT_DEBUG", "0")
    runtime = load_degenbot_runtime(settings.degenbot_source_path)
    await DegenbotIpcServer(settings=settings, runtime=runtime).run_forever()


def run() -> None:
    """Console entrypoint (`mev-degenbot-adapter`)."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
