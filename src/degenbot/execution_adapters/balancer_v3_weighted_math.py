"""Python port of Balancer V3's WeightedMath library.

**Source:** `pkg/solidity-utils/contracts/math/WeightedMath.sol` from the
cached `balancer-v3-monorepo`.

Implements the constant-weighted-product invariant
`I = product(balances[i] ** weights[i])` and its inverses, used by
Balancer V3 Weighted Pools (50/50, 80/20, n-asset weighted). All math
uses 18-decimal fixed point on top of `balancer_fixed_point` and
`balancer_log_exp_math`.

**Rounding direction:** matches Solidity exactly. Down rounds favor the
protocol on output side; Up rounds favor the protocol on input side. The
Solidity comments at the top of each function explain why each operation
chose its direction.

**Pool limits (from Solidity constants):**
- swaps may not exceed 30% of the source-side balance (in or out)
- non-proportional liquidity ops may not change the invariant by more
  than ±300%/-30% bands

`compute_balance_out_given_invariant` is included for parity with the
Solidity surface, but the solver's primary swap-simulation path uses
`compute_out_given_exact_in` directly.
"""

from __future__ import annotations

from typing import Final

from degenbot.execution_adapters import balancer_fixed_point as fp

# ---------------------------------------------------------------------------
# Constants — mirror Solidity verbatim
# ---------------------------------------------------------------------------

#: Max amount-in as a fraction of the source-side balance (30%).
MAX_IN_RATIO: Final[int] = 30 * 10**16

#: Max amount-out as a fraction of the source-side balance (30%).
MAX_OUT_RATIO: Final[int] = 30 * 10**16

#: Max invariant growth on a non-proportional add (300%).
MAX_INVARIANT_RATIO: Final[int] = 300 * 10**16

#: Min invariant after a non-proportional remove (70%).
MIN_INVARIANT_RATIO: Final[int] = 70 * 10**16


class MaxInRatioError(ValueError):
    """`amount_in` exceeded `MAX_IN_RATIO * balance_in`."""


class MaxOutRatioError(ValueError):
    """`amount_out` exceeded `MAX_OUT_RATIO * balance_out`."""


class ZeroInvariantError(ValueError):
    """Computed invariant was zero — typically a zero balance somewhere."""


# ---------------------------------------------------------------------------
# Invariant
# ---------------------------------------------------------------------------


def _validate_inputs(
    normalized_weights: list[int] | tuple[int, ...],
    balances: list[int] | tuple[int, ...],
) -> None:
    if len(normalized_weights) != len(balances):
        raise ValueError(
            f"weights / balances length mismatch: {len(normalized_weights)} vs {len(balances)}",
        )
    if len(normalized_weights) == 0:
        raise ValueError("weights and balances must be non-empty")


def compute_invariant_down(
    normalized_weights: list[int] | tuple[int, ...],
    balances: list[int] | tuple[int, ...],
) -> int:
    """`invariant = product(balances[i]^weights[i])`, rounded down.

    Used when the protocol wants the smaller of two valid invariants
    (e.g., on adds where a smaller invariant means more BPT minted to the
    Vault).
    """
    _validate_inputs(normalized_weights, balances)
    invariant = fp.ONE
    for w, b in zip(normalized_weights, balances, strict=True):
        invariant = fp.mul_down(invariant, fp.pow_down(b, w))
    if invariant == 0:
        raise ZeroInvariantError("computed invariant is zero")
    return invariant


def compute_invariant_up(
    normalized_weights: list[int] | tuple[int, ...],
    balances: list[int] | tuple[int, ...],
) -> int:
    """`invariant = product(balances[i]^weights[i])`, rounded up.

    Used when the protocol wants the larger of two valid invariants.
    """
    _validate_inputs(normalized_weights, balances)
    invariant = fp.ONE
    for w, b in zip(normalized_weights, balances, strict=True):
        invariant = fp.mul_up(invariant, fp.pow_up(b, w))
    if invariant == 0:
        raise ZeroInvariantError("computed invariant is zero")
    return invariant


# ---------------------------------------------------------------------------
# Inverse invariant
# ---------------------------------------------------------------------------


def compute_balance_out_given_invariant(
    current_balance: int,
    weight: int,
    invariant_ratio: int,
) -> int:
    """`new_balance = current_balance * invariant_ratio^(1/weight)`, rounded up.

    Used in liquidity ops to compute the new token balance that would make
    the invariant move by `invariant_ratio`. Rounding direction picked so
    the protocol always errs on the side of more tokens leaving.
    """
    # Exponent: 1/weight. For invariantRatio > 1, x^y is increasing → round
    # exponent up. For invariantRatio < 1, x^y is decreasing → round down.
    exponent = fp.div_up(fp.ONE, weight) if invariant_ratio > fp.ONE else fp.div_down(fp.ONE, weight)
    balance_ratio = fp.pow_up(invariant_ratio, exponent)
    return fp.mul_up(current_balance, balance_ratio)


# ---------------------------------------------------------------------------
# Swap math (the hot path)
# ---------------------------------------------------------------------------


def compute_out_given_exact_in(
    balance_in: int,
    weight_in: int,
    balance_out: int,
    weight_out: int,
    amount_in: int,
) -> int:
    """ExactIn swap: given `amount_in`, return the corresponding `amount_out`.

    Identity:
        amount_out = balance_out * (1 - (balance_in / (balance_in + amount_in))^(weight_in / weight_out))

    Rounding plan (matching Solidity comments):
    - overall result rounded DOWN (we owe the user no more than this)
    - `base = balance_in / (balance_in + amount_in)` rounded UP (so the
      complement rounds DOWN)
    - exponent rounded DOWN (since base < 1, this rounds power UP, which
      rounds the complement DOWN — favors the protocol)
    """
    if amount_in > fp.mul_down(balance_in, MAX_IN_RATIO):
        raise MaxInRatioError(
            f"amount_in {amount_in} exceeds MAX_IN_RATIO * balance_in ({fp.mul_down(balance_in, MAX_IN_RATIO)})",
        )

    denominator = balance_in + amount_in
    base = fp.div_up(balance_in, denominator)
    exponent = fp.div_down(weight_in, weight_out)
    power = fp.pow_up(base, exponent)
    # `complement` clamps `1 - power` to zero if power > 1 (which can
    # happen due to rounding-up of the power); avoids underflow.
    return fp.mul_down(balance_out, fp.complement(power))


def compute_in_given_exact_out(
    balance_in: int,
    weight_in: int,
    balance_out: int,
    weight_out: int,
    amount_out: int,
) -> int:
    """ExactOut swap: given `amount_out`, return the required `amount_in`.

    Identity:
        amount_in = balance_in * ((balance_out / (balance_out - amount_out))^(weight_out / weight_in) - 1)

    Rounding plan:
    - overall result rounded UP (we ask the user for at least this)
    - `base = balance_out / (balance_out - amount_out)` rounded UP (≥ 1)
    - exponent rounded UP (since base ≥ 1, rounds power UP — favors protocol)
    """
    if amount_out > fp.mul_down(balance_out, MAX_OUT_RATIO):
        raise MaxOutRatioError(
            f"amount_out {amount_out} exceeds MAX_OUT_RATIO * balance_out ({fp.mul_down(balance_out, MAX_OUT_RATIO)})",
        )

    base = fp.div_up(balance_out, balance_out - amount_out)
    exponent = fp.div_up(weight_out, weight_in)
    power = fp.pow_up(base, exponent)
    # base > 1 and pow rounds up, so power > 1 — subtraction is safe.
    ratio = power - fp.ONE
    return fp.mul_up(balance_in, ratio)
