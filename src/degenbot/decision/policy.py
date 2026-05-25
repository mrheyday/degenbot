"""Capital policy definitions for the strategy routing engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from degenbot.decision.precedence import DecisionKind

CapitalPolicyVerdict = Literal["allow", "deny", "observe"]
CapitalFundingMode = Literal["zero_capital_atomic", "inventory_async", "observe"]


@dataclass(frozen=True)
class CapitalGateSet:
    zero_capital: bool
    flash_funded: bool
    atomic_repayment: bool
    sourced_decimals: bool
    sourced_price: bool
    sourced_liquidity: bool
    sourced_fees: bool
    sourced_gas: bool
    sourced_route_calldata: bool
    exact_simulation: bool
    same_calldata_broadcast: bool
    integer_hot_path: bool


CapitalStrategyId = Literal[
    "sourced_price_spread_arb",
    "sourced_compound_v3_liquidation",
    "sourced_morpho_blue_liquidation",
    "sourced_tarot_liquidation",
    "compound_v3_liquidation_signal",
    "native_arb_direct",
    "internal_match_direct",
    "four_leg_direct",
    "morpho_liquidation_decision",
    "cow_user_submit",
    "cow_quoter",
    "uniswapx_reactor_flash_fill",
    "across_fill",
    "launch_sniper",
    "jaredbot_legacy_signals",
    "v4_hook_arb",
    "gmx_liquidation_handler",
    "ostium_oracle_gap",
    "oracle_sandwich",
    "sandwich_s1_timeboost",
    "sandwich_s2_cow_prebatch",
    "sandwich_s3_uniswapx_filler",
    "sandwich_s4_cross_pool_flash",
    "dolomite_liquidation",
    "silo_monitor",
    "pendle_identity_arb",
    "prefunded_withdrawal_liquidity_arb",
    "eip7702_set_code",
    "pass",
]

FeedStrategyKind = Literal["cow_quoter", "filler_bid"]


@dataclass(frozen=True)
class CapitalStrategyPolicy:
    id: CapitalStrategyId
    label: str
    verdict: CapitalPolicyVerdict
    funding_mode: CapitalFundingMode
    capital_moving: bool
    required_path: str
    reason: str
    gates: CapitalGateSet


ALL_CAPITAL_GATES = CapitalGateSet(
    zero_capital=True,
    flash_funded=True,
    atomic_repayment=True,
    sourced_decimals=True,
    sourced_price=True,
    sourced_liquidity=True,
    sourced_fees=True,
    sourced_gas=True,
    sourced_route_calldata=True,
    exact_simulation=True,
    same_calldata_broadcast=True,
    integer_hot_path=True,
)

NO_CAPITAL_GATES = CapitalGateSet(
    zero_capital=False,
    flash_funded=False,
    atomic_repayment=False,
    sourced_decimals=False,
    sourced_price=False,
    sourced_liquidity=False,
    sourced_fees=False,
    sourced_gas=False,
    sourced_route_calldata=False,
    exact_simulation=False,
    same_calldata_broadcast=False,
    integer_hot_path=False,
)

INVENTORY_ASYNC_CAPITAL_GATES = CapitalGateSet(
    zero_capital=False,
    flash_funded=False,
    atomic_repayment=False,
    sourced_decimals=True,
    sourced_price=True,
    sourced_liquidity=True,
    sourced_fees=True,
    sourced_gas=True,
    sourced_route_calldata=True,
    exact_simulation=True,
    same_calldata_broadcast=True,
    integer_hot_path=True,
)


def _allow(
    strategy_id: CapitalStrategyId, label: str, required_path: str
) -> CapitalStrategyPolicy:
    return CapitalStrategyPolicy(
        id=strategy_id,
        label=label,
        verdict="allow",
        funding_mode="zero_capital_atomic",
        capital_moving=True,
        required_path=required_path,
        reason="complete sourced signal, flash repayment, exact simulation, and same-calldata broadcast path",
        gates=ALL_CAPITAL_GATES,
    )


def _allow_inventory_async(
    strategy_id: CapitalStrategyId, label: str, required_path: str, reason: str
) -> CapitalStrategyPolicy:
    return CapitalStrategyPolicy(
        id=strategy_id,
        label=label,
        verdict="allow",
        funding_mode="inventory_async",
        capital_moving=True,
        required_path=required_path,
        reason=reason,
        gates=INVENTORY_ASYNC_CAPITAL_GATES,
    )


def _observe(strategy_id: CapitalStrategyId, label: str, reason: str) -> CapitalStrategyPolicy:
    return CapitalStrategyPolicy(
        id=strategy_id,
        label=label,
        verdict="observe",
        funding_mode="observe",
        capital_moving=False,
        required_path="monitor only; do not broadcast capital-moving calldata",
        reason=reason,
        gates=NO_CAPITAL_GATES,
    )


CAPITAL_STRATEGY_POLICIES: Mapping[CapitalStrategyId, CapitalStrategyPolicy] = {
    "sourced_price_spread_arb": _allow(
        "sourced_price_spread_arb",
        "Sourced price-spread flash arb",
        "executeSourcedPriceSpreadArb(signal, deps)",
    ),
    "native_arb_direct": _allow(
        "native_arb_direct",
        "Direct native_arb decision dispatch",
        "SourcedPriceSpreadArbSignal -> executeSourcedPriceSpreadArb",
    ),
    "morpho_liquidation_decision": _allow(
        "morpho_liquidation_decision",
        "Decision-engine Morpho liquidation route",
        "executeSourcedMorphoBlueLiquidation(signal, deps)",
    ),
    "eip7702_set_code": _allow_inventory_async(
        "eip7702_set_code",
        "EIP-7702 EOA code delegation",
        "admin-triggered one-time SET_CODE_TX",
        "Setup operation to activate bot EOA as a delegated smart account; not a strategy",
    ),
    "pass": _observe("pass", "Pass", "no action"),
    # Add other variants as needed...
}


def review_capital_strategy(strategy_id: CapitalStrategyId) -> CapitalStrategyPolicy:
    return CAPITAL_STRATEGY_POLICIES[strategy_id]


def capital_policy_for_decision(kind: DecisionKind) -> CapitalStrategyPolicy:
    if kind == "native_arb":
        return review_capital_strategy("native_arb_direct")
    if kind == "morpho_liquidation":
        return review_capital_strategy("morpho_liquidation_decision")
    if kind == "pass":
        return review_capital_strategy("pass")
    msg = f"Unknown decision kind: {kind}"
    raise ValueError(msg)
