from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from numbers import Real

from degenbot.strategy_signals.arbitrum_atomic_flash_research import (
    AtomicFlashStatus,
    atomic_flash_target,
    ranked_atomic_flash_targets,
    workflow_required_atomic_flash_targets,
)


def _assert_no_float(value: object) -> None:
    assert not (isinstance(value, Real) and not isinstance(value, (bool, int))), value
    if isinstance(value, Mapping):
        for nested in value.values():
            _assert_no_float(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _assert_no_float(nested)


def test_ranked_atomic_flash_targets_match_research_plan() -> None:
    targets = ranked_atomic_flash_targets()

    assert [target.target_id for target in targets] == ["E-1", "P-2", "D-1", "C-1", "P-3"]
    assert targets[0].protocol == "Euler v2"
    assert targets[1].protocol == "Pendle"
    assert targets[2].protocol == "Dolomite"
    assert targets[3].protocol == "Compound v3 / Silo v2"
    assert targets[4].protocol == "Pendle / Uniswap v4"


def test_targets_are_atomic_flash_financed_and_workflow_required() -> None:
    targets = ranked_atomic_flash_targets()

    assert workflow_required_atomic_flash_targets() == targets
    for target in targets:
        assert target.atomic_single_tx
        assert "Vault.unlock" in target.flash_source or "Balancer V3" in target.flash_source
        assert not target.dispatchable
        assert target.required_checks
        assert target.workflow_requirements
        assert any(
            "minProfit" in requirement or "profit" in requirement.lower()
            for requirement in target.workflow_requirements
        )


def test_target_statuses_preserve_unexplored_vs_quick_check_distinction() -> None:
    assert atomic_flash_target("E-1").status is AtomicFlashStatus.REQUIRES_DECODE
    assert atomic_flash_target("P-2").status is AtomicFlashStatus.REQUIRES_DECODE
    assert atomic_flash_target("D-1").status is AtomicFlashStatus.REQUIRES_DECODE
    assert atomic_flash_target("C-1").status is AtomicFlashStatus.QUICK_CHECK
    assert atomic_flash_target("P-3").status is AtomicFlashStatus.QUICK_CHECK


def test_research_targets_are_integer_only_and_json_safe() -> None:
    payload = [
        {
            "target_id": target.target_id,
            "rank": target.rank,
            "protocol": target.protocol,
            "status": target.status.value,
            "tvl_usd": target.tvl_usd,
            "fees_30d_usd": target.fees_30d_usd,
            "trend_30d_bps": target.trend_30d_bps,
            "poc_steps": target.poc_steps,
            "workflow_requirements": target.workflow_requirements,
        }
        for target in ranked_atomic_flash_targets()
    ]

    _assert_no_float(payload)
    json.dumps(payload, sort_keys=True)


def test_poc_steps_bind_to_real_execution_surfaces() -> None:
    euler = atomic_flash_target("E-1")
    assert "EVC.batch" in " ".join(euler.poc_steps)
    assert "liquidate" in euler.execution_surface.lower()

    pendle = atomic_flash_target("P-2")
    assert "redeemPyToSy" in " ".join(pendle.poc_steps)
    assert "PT + YT = SY" in pendle.thesis

    dolomite = atomic_flash_target("D-1")
    assert "LiquidatorProxyV4WithGenericTrader" in dolomite.execution_surface
    assert "negative balance" in dolomite.workflow_requirements[-1]

    compound = atomic_flash_target("C-1")
    assert "Comet.absorb" in " ".join(compound.poc_steps)
    assert "buyCollateral" in compound.execution_surface

    pendle_limit = atomic_flash_target("P-3")
    assert "limit-order" in pendle_limit.execution_surface
    assert "v4 hook" in " ".join(pendle_limit.workflow_requirements)
