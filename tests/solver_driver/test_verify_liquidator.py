from __future__ import annotations

from degenbot.ops_solver import verify_liquidator as verifier


def test_liquidator_verifier_reads_canonical_deployment_env_aliases() -> None:
    liquidator = "0x0000000000000000000000000000000000002222"
    delegatee = "0x000000000000000000000000000000000000dEaD"

    assert (
        verifier.liquidator_address_from_env({"LIQUIDATION_EXECUTOR_ADDRESS": liquidator})
        == liquidator
    )
    assert verifier.delegatee_csv_from_env({"DELEGATEES_INITIAL": delegatee}) == delegatee
