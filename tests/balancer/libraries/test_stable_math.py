from degenbot.balancer.libraries import stable_math
from degenbot.balancer.libraries.constants import ONE


def test_calculate_invariant():
    amp = 100 * 1000  # A = 100, amp precision = 1000
    balances = [10 * ONE, 10 * ONE]
    invariant = stable_math._calculateInvariant(amp, balances)
    # For balanced 50/50 stable pool, invariant should be the sum of balances
    assert invariant == 20 * ONE


def test_calc_out_given_in():
    amp = 100 * 1000
    balances = [10 * ONE, 10 * ONE]
    token_index_in = 0
    token_index_out = 1
    token_amount_in = 1 * ONE
    invariant = stable_math._calculateInvariant(amp, balances)

    amount_out = stable_math._calcOutGivenIn(amp, balances, token_index_in, token_index_out, token_amount_in, invariant)

    # In a stable pool with A=100, swapping 1 for 1 should be close to 1
    assert amount_out < 1 * ONE
    assert amount_out > 0.99 * ONE
