from __future__ import annotations

from pathlib import Path

from degenbot.strategies_solver.arbitrum_mev_market_map import (
    FEE_DENSITY_SNAPSHOT,
    StrategyPocStatus,
    highest_open_interest_protocol,
    protocol_snapshot,
    ranked_strategy_priorities,
    snapshot_density_matches_table,
    strategy_priority,
    top_fee_density_protocols,
)


def _find_root():
    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / "PROGRESS.md").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parents[4]


REPO_ROOT = _find_root()


def _path(ref: str) -> Path:
    return REPO_ROOT / ref


def test_fee_density_snapshot_matches_supplied_table() -> None:
    assert len(FEE_DENSITY_SNAPSHOT) == 8

    for row in FEE_DENSITY_SNAPSHOT:
        assert snapshot_density_matches_table(row), row.protocol

    assert protocol_snapshot("Ostium").fee_density_bps == 6_010
    assert protocol_snapshot("aave").tvl_usd == 468_960_000
    assert protocol_snapshot("Boros").oi_usd == 144_500_000
    assert protocol_snapshot("Variational").oi_usd == 751_900_000


def test_fee_density_leaders_prioritize_ostium_and_aave() -> None:
    leaders = [row.protocol for row in top_fee_density_protocols()]

    assert leaders[:3] == ["Ostium", "Gains Network", "aave"]
    ostium_density = protocol_snapshot("Ostium").annualized_fee_density_bps
    aave_density = protocol_snapshot("aave").annualized_fee_density_bps
    gmx_density = protocol_snapshot("gmx").annualized_fee_density_bps

    assert ostium_density is not None
    assert aave_density is not None
    assert gmx_density is not None
    assert ostium_density > 6_000
    assert aave_density > gmx_density


def test_open_interest_leader_is_variational_even_without_fee_row() -> None:
    leader = highest_open_interest_protocol()

    assert leader.protocol == "Variational"
    assert leader.oi_usd == 751_900_000
    assert leader.fee_density_bps is None

    variational_signal = strategy_priority("V-1")
    assert variational_signal.status is StrategyPocStatus.BUILD_READY
    assert "OLPToPoolTransfer" in variational_signal.immediate_action

    old_liquidation_thesis = strategy_priority("S-1")
    assert old_liquidation_thesis.status is StrategyPocStatus.DEPRIORITIZED
    assert "Do not build" in old_liquidation_thesis.immediate_action


def test_ranked_strategy_sequence_matches_corrected_research_slate() -> None:
    priorities = ranked_strategy_priorities()

    assert [priority.strategy_id for priority in priorities] == [
        "L-2",
        "U-1",
        "A-1",
        "V-1",
        "L-1",
        "J-1",
        "B-1",
        "T-1",
    ]
    assert priorities[0].label == "Morpho Blue atomic liquidation"
    assert priorities[1].source_protocols == ("Uniswap",)
    assert priorities[2].source_protocols == ("Uniswap", "Camelot", "fluid")
    assert priorities[3].status is StrategyPocStatus.BUILD_READY
    assert priorities[4].status is StrategyPocStatus.REQUIRES_INTEGRATION
    assert priorities[5].status is StrategyPocStatus.RESEARCH_ONLY
    assert priorities[7].status is StrategyPocStatus.INFRASTRUCTURE


def test_only_existing_strategy_paths_are_marked_executable() -> None:
    executable = {
        priority.strategy_id
        for priority in ranked_strategy_priorities()
        if priority.status is StrategyPocStatus.EXECUTABLE
    }
    uninvestigated = {
        priority.strategy_id
        for priority in ranked_strategy_priorities()
        if priority.status is StrategyPocStatus.UNINVESTIGATED
    }

    assert executable == set()
    assert uninvestigated == {"B-1"}
    assert strategy_priority("L-2").status is StrategyPocStatus.BUILD_READY
    assert strategy_priority("U-1").status is StrategyPocStatus.REQUIRES_INTEGRATION
    assert strategy_priority("A-1").status is StrategyPocStatus.MONITOR_ONLY
    assert strategy_priority("V-1").status is StrategyPocStatus.BUILD_READY

    for strategy_id in executable:
        priority = strategy_priority(strategy_id)
        refs = " ".join((*priority.code_refs, *priority.proof_refs))
        assert "coordinator/" in refs
        assert "test" in refs


def test_boros_effective_fee_rate_is_near_zero() -> None:
    boros = protocol_snapshot("Boros")

    assert boros.daily_derivatives_fee_rate_ppm is not None
    assert 20 < boros.daily_derivatives_fee_rate_ppm < 40
    assert strategy_priority("B-1").status is StrategyPocStatus.UNINVESTIGATED


def test_deprioritized_gmx_uniswap_is_excluded_from_default_rankings() -> None:
    default_ids = {priority.strategy_id for priority in ranked_strategy_priorities()}
    all_ids = {
        priority.strategy_id for priority in ranked_strategy_priorities(include_deprioritized=True)
    }

    assert "K-1" not in default_ids
    assert "K-1" in all_ids
    assert strategy_priority("K-1").status is StrategyPocStatus.DEPRIORITIZED


def test_strategy_priority_references_exist() -> None:
    for priority in ranked_strategy_priorities(include_deprioritized=True):
        for ref in (*priority.code_refs, *priority.proof_refs):
            assert _path(ref).exists(), f"{priority.strategy_id}: {ref}"
