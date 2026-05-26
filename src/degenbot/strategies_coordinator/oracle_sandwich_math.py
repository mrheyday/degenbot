"""Pure math for the S-5 oracle-update sandwich strategy.

Mirrors FrontrunCalldata.sol and coordinator/src/strategies/oracle-sandwich/profit-estimator.ts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from degenbot.decision.types import Address

PRICE_SCALE = 1 << 96


@dataclass(frozen=True)
class OracleSandwichProfitEstimate:
    expected_profit_wei: int
    frontrun_size_wei: int
    backrun_size_wei: int
    amm_pool: Address
    pre_update_price_x96: int
    post_update_price_x96: int


def get_amount_out(
    amount_in: int,
    reserve_in: int,
    reserve_out: int,
    fee_bps: int,
) -> int:
    """V2 exact-input quote."""
    if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
        return 0
    if fee_bps < 0 or fee_bps >= 10_000:
        return 0
    amount_in_with_fee = amount_in * (10_000 - fee_bps)
    numerator = amount_in_with_fee * reserve_out
    denominator = reserve_in * 10_000 + amount_in_with_fee
    return numerator // denominator


def v3_virtual_reserves(
    sqrt_price_x96: int,
    liquidity: int,
) -> tuple[int, int]:
    """Project V3 in-tick liquidity into virtual V2 reserves."""
    if sqrt_price_x96 == 0 or liquidity == 0:
        return 0, 0
    reserve0 = (liquidity * PRICE_SCALE) // sqrt_price_x96
    reserve1 = (liquidity * sqrt_price_x96) // PRICE_SCALE
    return reserve0, reserve1


def apply_gap_to_price_x96(price_x96: int, gap_bps: int) -> int:
    """Apply the gap to a price (basis points; positive moves price up)."""
    factor = max(0, 10_000 + gap_bps)
    return (price_x96 * factor) // 10_000


def synthetic_victim_amount_in(gap_bps: int, reserve_in: int) -> int:
    """Synthetic victim swap size — gap magnitude scaled against pool depth."""
    mag = abs(gap_bps)
    if mag == 0:
        return 0
    # Clamp at 50% of pool depth
    fraction = min(mag, 5_000)
    return (reserve_in * fraction) // 10_000


def estimate_oracle_sandwich_profit(
    gap_bps: int,
    pool_address: Address,
    reserve_in: int,
    reserve_out: int,
    fee_bps: int,
    gas_cost_wei: int,
    margin_bps: int = 10,
    frontrun_cap_wei: int | None = None,
) -> OracleSandwichProfitEstimate:
    """Compute the expected sandwich profit + optimal frontrun size."""
    from degenbot import optimal_v2_frontrun_amount

    # 1. Synthetic victim from the gap
    syn_av = synthetic_victim_amount_in(gap_bps, reserve_in)
    if syn_av <= 0:
        return _zero_estimate(pool_address)

    # 2. Baseline victim out
    syn_mv = get_amount_out(syn_av, reserve_in, reserve_out, fee_bps)
    if syn_mv <= 0:
        return _zero_estimate(pool_address)
    # Apply 1bp slippage tolerance
    syn_mv_tolerated = (syn_mv * 9_999) // 10_000

    # 3. Optimal frontrun amount (Rust accelerated)
    res_str = optimal_v2_frontrun_amount(
        syn_av,
        syn_mv_tolerated,
        reserve_in,
        reserve_out,
        fee_bps,
        margin_bps,
    )
    frontrun_size_wei = int(res_str)
    if frontrun_size_wei <= 0:
        return _zero_estimate(pool_address)

    if frontrun_cap_wei is not None and 0 < frontrun_cap_wei < frontrun_size_wei:
        frontrun_size_wei = frontrun_cap_wei

    # 4. Profit simulation
    frontrun_out = get_amount_out(frontrun_size_wei, reserve_in, reserve_out, fee_bps)

    r0_after_front = reserve_in + frontrun_size_wei
    r1_after_front = reserve_out - frontrun_out

    # Victim swap
    syn_victim_out = get_amount_out(syn_av, r0_after_front, r1_after_front, fee_bps)

    r0_after_victim = r0_after_front + syn_av
    r1_after_victim = r1_after_front - syn_victim_out

    # Backrun
    backrun_in = frontrun_out
    backrun_out = get_amount_out(backrun_in, r1_after_victim, r0_after_victim, fee_bps)

    gross_profit = backrun_out - frontrun_size_wei
    expected_profit_wei = max(0, gross_profit - gas_cost_wei)

    # Pre/post metadata follows the executor-side mid-price convention.
    pre_price_x96 = (reserve_out * (1 << 96)) // reserve_in if reserve_in > 0 else 0

    return OracleSandwichProfitEstimate(
        expected_profit_wei=expected_profit_wei,
        frontrun_size_wei=frontrun_size_wei,
        backrun_size_wei=backrun_in,
        amm_pool=pool_address,
        pre_update_price_x96=pre_price_x96,
        post_update_price_x96=apply_gap_to_price_x96(pre_price_x96, gap_bps),
    )


def _zero_estimate(amm_pool: Address) -> OracleSandwichProfitEstimate:
    return OracleSandwichProfitEstimate(
        expected_profit_wei=0,
        frontrun_size_wei=0,
        backrun_size_wei=0,
        amm_pool=amm_pool,
        pre_update_price_x96=0,
        post_update_price_x96=0,
    )
