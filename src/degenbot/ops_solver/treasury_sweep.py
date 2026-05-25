"""Treasury-sweep helper: propose `Executor.rescueToken` to the Safe.

Run via ApeWorx: `ape run driver/ops/treasury_sweep.py --network arbitrum:mainnet`.

Queries the Executor's idle ERC-20 + native balances and proposes a
`rescueToken` (or equivalent) call to the 3-of-5 Safe (ADR-014). Used
periodically (e.g., weekly) to move accumulated profits out of the
hot Executor into the treasury Safe.
"""

from __future__ import annotations


def main() -> None:
    """ApeWorx entrypoint — propose treasury sweep."""
    # TODO(scaffold): import ape + ape_arbitrum lazily inside main().
    # TODO(scaffold): import Safe SDK or ape-safe plugin.
    # TODO(scaffold): query Executor balances:
    #                   - native: provider.get_balance(EXECUTOR_ADDRESS)
    #                   - per-token: ERC20.balanceOf(EXECUTOR_ADDRESS) for
    #                     each tracked token (USDC, WETH, ARB, ...).
    # TODO(scaffold): for each non-zero balance > min_sweep_threshold,
    #                 build calldata for Executor.rescueToken(token,
    #                 SAFE_ADDRESS, amount).
    # TODO(scaffold): propose all rescue calls as a single SafeTx
    #                 (multiSend) so signers approve one bundle.
    # TODO(scaffold): structured-log proposed SafeTxHash + per-token amounts.
    msg = "TODO(scaffold): implement treasury sweep proposer"
    raise NotImplementedError(msg)


if __name__ == "__main__":
    main()
