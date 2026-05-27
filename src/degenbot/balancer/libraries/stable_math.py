"""Balancer stable-pool math port preserving Solidity helper names."""

# ruff: noqa: ERA001,N802

from degenbot.balancer.libraries import fixed_point, math
from degenbot.balancer.libraries.constants import ONE
from degenbot.exceptions.evm import EVMRevertError

_MIN_AMP = 1
_MAX_AMP = 5000
_AMP_PRECISION = 1000

_MAX_STABLE_TOKENS = 5


def _calculateInvariant(amplification_parameter: int, balances: list[int]) -> int:
    sum_balances = 0
    num_tokens = len(balances)
    for balance in balances:
        sum_balances = math.add(sum_balances, balance)

    if sum_balances == 0:
        return 0

    prev_invariant = 0
    invariant = sum_balances
    amp_times_total = amplification_parameter * num_tokens

    for _ in range(255):
        d_p = invariant

        for balance in balances:
            # (d_p * invariant) / (balance * num_tokens)
            d_p = math.div_down(math.mul(d_p, invariant), math.mul(balance, num_tokens))

        prev_invariant = invariant

        # invariant = ((amp_times_total * sum) / _AMP_PRECISION + d_p * num_tokens) * invariant /
        #             (((amp_times_total - _AMP_PRECISION) * invariant) / _AMP_PRECISION + (num_tokens + 1) * d_p)

        numerator = math.mul(
            math.add(
                math.div_down(math.mul(amp_times_total, sum_balances), _AMP_PRECISION),
                math.mul(d_p, num_tokens),
            ),
            invariant,
        )

        denominator = math.add(
            math.div_down(
                math.mul(amp_times_total - _AMP_PRECISION, invariant), _AMP_PRECISION
            ),
            math.mul(num_tokens + 1, d_p),
        )

        invariant = math.div_down(numerator, denominator)

        if invariant > prev_invariant:
            if invariant - prev_invariant <= 1:
                return invariant
        elif prev_invariant - invariant <= 1:
            return invariant

    raise EVMRevertError(error="STABLE_INVARIANT_DIDNT_CONVERGE")


def _calcOutGivenIn(
    amplification_parameter: int,
    balances: list[int],
    token_index_in: int,
    token_index_out: int,
    token_amount_in: int,
    invariant: int,
) -> int:
    # Amount out, so we round down overall.
    balances[token_index_in] = math.add(balances[token_index_in], token_amount_in)

    final_balance_out = _getTokenBalanceGivenInvariantAndAllOtherBalances(
        amplification_parameter,
        balances,
        invariant,
        token_index_out,
    )

    balances[token_index_in] = math.sub(balances[token_index_in], token_amount_in)

    # return balances[tokenIndexOut].sub(finalBalanceOut).sub(1);
    return math.sub(math.sub(balances[token_index_out], final_balance_out), 1)


def _calcInGivenOut(
    amplification_parameter: int,
    balances: list[int],
    token_index_in: int,
    token_index_out: int,
    token_amount_out: int,
    invariant: int,
) -> int:
    # Amount in, so we round up overall.
    balances[token_index_out] = math.sub(balances[token_index_out], token_amount_out)

    final_balance_in = _getTokenBalanceGivenInvariantAndAllOtherBalances(
        amplification_parameter,
        balances,
        invariant,
        token_index_in,
    )

    balances[token_index_out] = math.add(balances[token_index_out], token_amount_out)

    # return finalBalanceIn.sub(balances[tokenIndexIn]).add(1);
    return math.add(math.sub(final_balance_in, balances[token_index_in]), 1)


def _getTokenBalanceGivenInvariantAndAllOtherBalances(
    amplification_parameter: int,
    balances: list[int],
    invariant: int,
    token_index: int,
) -> int:
    # Rounds result up overall

    amp_times_total = amplification_parameter * len(balances)
    sum_balances = balances[0]
    p_d = balances[0] * len(balances)

    for i in range(1, len(balances)):
        p_d = math.div_down(
            math.mul(math.mul(p_d, balances[i]), len(balances)), invariant
        )
        sum_balances = math.add(sum_balances, balances[i])

    sum_balances -= balances[token_index]

    inv2 = math.mul(invariant, invariant)

    # c = (inv2 / (amp_times_total * p_d)) * _AMP_PRECISION * balances[token_index]
    c = math.mul(
        math.mul(
            math.div_up(inv2, math.mul(amp_times_total, p_d)),
            _AMP_PRECISION,
        ),
        balances[token_index],
    )

    # b = sum + (invariant / amp_times_total) * _AMP_PRECISION
    b = math.add(
        sum_balances,
        math.mul(math.div_down(invariant, amp_times_total), _AMP_PRECISION),
    )

    token_balance = math.div_up(math.add(inv2, c), math.add(invariant, b))

    for _ in range(255):
        prev_token_balance = token_balance

        # token_balance = (token_balance^2 + c) / (2 * token_balance + b - invariant)
        token_balance = math.div_up(
            math.add(math.mul(token_balance, token_balance), c),
            math.sub(math.add(math.mul(token_balance, 2), b), invariant),
        )

        if token_balance > prev_token_balance:
            if token_balance - prev_token_balance <= 1:
                return token_balance
        elif prev_token_balance - token_balance <= 1:
            return token_balance

    raise EVMRevertError(error="STABLE_GET_BALANCE_DIDNT_CONVERGE")


def _calcBptOutGivenExactTokensIn(
    amp: int,
    balances: list[int],
    amounts_in: list[int],
    bpt_total_supply: int,
    current_invariant: int,
    swap_fee_percentage: int,
) -> int:
    # BPT out, so we round down overall.

    sum_balances = 0
    for balance in balances:
        sum_balances = math.add(sum_balances, balance)

    balance_ratios_with_fee = []
    invariant_ratio_with_fees = 0
    for i in range(len(balances)):
        current_weight = fixed_point.div_down(balances[i], sum_balances)
        balance_ratio_with_fee = fixed_point.div_down(
            math.add(balances[i], amounts_in[i]), balances[i]
        )
        balance_ratios_with_fee.append(balance_ratio_with_fee)
        invariant_ratio_with_fees = math.add(
            invariant_ratio_with_fees,
            fixed_point.mul_down(balance_ratio_with_fee, current_weight),
        )

    new_balances = []
    for i in range(len(balances)):
        if balance_ratios_with_fee[i] > invariant_ratio_with_fees:
            non_taxable_amount = fixed_point.mul_down(
                balances[i], math.sub(invariant_ratio_with_fees, ONE)
            )
            taxable_amount = math.sub(amounts_in[i], non_taxable_amount)
            amount_in_without_fee = math.add(
                non_taxable_amount,
                fixed_point.mul_down(taxable_amount, ONE - swap_fee_percentage),
            )
        else:
            amount_in_without_fee = amounts_in[i]

        new_balances.append(math.add(balances[i], amount_in_without_fee))

    new_invariant = _calculateInvariant(amp, new_balances)
    invariant_ratio = fixed_point.div_down(new_invariant, current_invariant)

    if invariant_ratio > ONE:
        return fixed_point.mul_down(bpt_total_supply, invariant_ratio - ONE)
    return 0


def _calcTokenInGivenExactBptOut(
    amp: int,
    balances: list[int],
    token_index: int,
    bpt_amount_out: int,
    bpt_total_supply: int,
    current_invariant: int,
    swap_fee_percentage: int,
) -> int:
    # Token in, so we round up overall.

    new_invariant = fixed_point.mul_up(
        fixed_point.div_up(math.add(bpt_total_supply, bpt_amount_out), bpt_total_supply),
        current_invariant,
    )

    new_balance_token_index = _getTokenBalanceGivenInvariantAndAllOtherBalances(
        amp,
        balances,
        new_invariant,
        token_index,
    )
    amount_in_without_fee = math.sub(new_balance_token_index, balances[token_index])

    sum_balances = 0
    for balance in balances:
        sum_balances = math.add(sum_balances, balance)

    current_weight = fixed_point.div_down(balances[token_index], sum_balances)
    taxable_percentage = fixed_point.complement(current_weight)
    taxable_amount = fixed_point.mul_up(amount_in_without_fee, taxable_percentage)
    non_taxable_amount = math.sub(amount_in_without_fee, taxable_amount)

    return math.add(
        non_taxable_amount,
        fixed_point.div_up(taxable_amount, ONE - swap_fee_percentage),
    )


def _calcBptInGivenExactTokensOut(
    amp: int,
    balances: list[int],
    amounts_out: list[int],
    bpt_total_supply: int,
    current_invariant: int,
    swap_fee_percentage: int,
) -> int:
    # BPT in, so we round up overall.

    sum_balances = 0
    for balance in balances:
        sum_balances = math.add(sum_balances, balance)

    balance_ratios_without_fee = []
    invariant_ratio_without_fees = 0
    for i in range(len(balances)):
        current_weight = fixed_point.div_up(balances[i], sum_balances)
        balance_ratio_without_fee = fixed_point.div_up(
            math.sub(balances[i], amounts_out[i]), balances[i]
        )
        balance_ratios_without_fee.append(balance_ratio_without_fee)
        invariant_ratio_without_fees = math.add(
            invariant_ratio_without_fees,
            fixed_point.mul_up(balance_ratio_without_fee, current_weight),
        )

    new_balances = []
    for i in range(len(balances)):
        if invariant_ratio_without_fees > balance_ratios_without_fee[i]:
            non_taxable_amount = fixed_point.mul_down(
                balances[i], fixed_point.complement(invariant_ratio_without_fees)
            )
            taxable_amount = math.sub(amounts_out[i], non_taxable_amount)
            amount_out_with_fee = math.add(
                non_taxable_amount,
                fixed_point.div_up(taxable_amount, ONE - swap_fee_percentage),
            )
        else:
            amount_out_with_fee = amounts_out[i]

        new_balances.append(math.sub(balances[i], amount_out_with_fee))

    new_invariant = _calculateInvariant(amp, new_balances)
    invariant_ratio = fixed_point.div_down(new_invariant, current_invariant)

    return fixed_point.mul_up(bpt_total_supply, fixed_point.complement(invariant_ratio))


def _calcTokenOutGivenExactBptIn(
    amp: int,
    balances: list[int],
    token_index: int,
    bpt_amount_in: int,
    bpt_total_supply: int,
    current_invariant: int,
    swap_fee_percentage: int,
) -> int:
    # Token out, so we round down overall.

    new_invariant = fixed_point.mul_up(
        fixed_point.div_up(math.sub(bpt_total_supply, bpt_amount_in), bpt_total_supply),
        current_invariant,
    )

    new_balance_token_index = _getTokenBalanceGivenInvariantAndAllOtherBalances(
        amp,
        balances,
        new_invariant,
        token_index,
    )
    amount_out_without_fee = math.sub(balances[token_index], new_balance_token_index)

    sum_balances = 0
    for balance in balances:
        sum_balances = math.add(sum_balances, balance)

    current_weight = fixed_point.div_down(balances[token_index], sum_balances)
    taxable_percentage = fixed_point.complement(current_weight)

    taxable_amount = fixed_point.mul_up(amount_out_without_fee, taxable_percentage)
    non_taxable_amount = math.sub(amount_out_without_fee, taxable_amount)

    return math.add(
        non_taxable_amount,
        fixed_point.mul_down(taxable_amount, ONE - swap_fee_percentage),
    )
