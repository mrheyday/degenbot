from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from numbers import Real

from degenbot.strategy_signals.rehackt_adversarial_fixtures import (
    FixtureStatus,
    QuoteOutcome,
    rehackt_fixture,
    rehackt_fixtures,
)


def _assert_no_float(value: object) -> None:
    assert not (isinstance(value, Real) and not isinstance(value, (bool, int))), value
    if isinstance(value, Mapping):
        for nested in value.values():
            _assert_no_float(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _assert_no_float(nested)


def test_rehackt_fixture_order_matches_port_backlog() -> None:
    fixtures = rehackt_fixtures()

    assert [fixture.fixture_id for fixture in fixtures] == [
        "rehackt-balancer-v2-stable-rounding",
        "rehackt-cover-reward-accounting",
    ]
    assert fixtures[0].protocol == "Balancer V2 Composable Stable Pool"
    assert fixtures[1].protocol == "Cover Protocol reward accounting"


def test_balancer_fixture_is_source_bound_and_non_dispatchable() -> None:
    fixture = rehackt_fixture("rehackt-balancer-v2-stable-rounding")

    assert fixture.source_url == "https://github.com/nonseodion/reHackt.git"
    assert fixture.source_commit == "4fad9644387c0fbd5cd5f7384935dea27362347a"
    assert fixture.status is FixtureStatus.REGRESSION_READY
    assert not fixture.dispatchable
    assert fixture.chain == "ethereum-mainnet"
    assert fixture.fork_block == 23_717_396
    assert "src/Balancer/SwapQuoter.sol" in fixture.source_paths
    assert "vendor/degenbot/rust/src/simulation/" in fixture.implementation_targets


def test_balancer_fixture_requires_structured_quote_failure_states() -> None:
    fixture = rehackt_fixture("rehackt-balancer-v2-stable-rounding")

    assert QuoteOutcome.VALID in fixture.simulator_quote_outcomes
    assert QuoteOutcome.NUMERICAL_NON_CONVERGENCE in fixture.simulator_quote_outcomes
    assert QuoteOutcome.FEE_SCALING_MISMATCH in fixture.simulator_quote_outcomes
    assert any("non-convergence" in check for check in fixture.required_checks)


def test_fixtures_forbid_live_exploit_ports() -> None:
    forbidden = " ".join(
        forbidden_port
        for fixture in rehackt_fixtures()
        for forbidden_port in fixture.forbidden_ports
    )

    assert "constructor-executed exploit contracts" in forbidden
    assert "live strategy dispatch" in forbidden
    assert "Solidity 0.7 libraries in contracts/src" in forbidden


def test_fixture_payloads_are_integer_only_and_json_safe() -> None:
    payload = [
        {
            "fixture_id": fixture.fixture_id,
            "protocol": fixture.protocol,
            "source_url": fixture.source_url,
            "source_commit": fixture.source_commit,
            "status": fixture.status.value,
            "dispatchable": fixture.dispatchable,
            "chain": fixture.chain,
            "fork_block": fixture.fork_block,
            "pool_addresses": fixture.pool_addresses,
            "token_addresses": fixture.token_addresses,
            "simulator_quote_outcomes": tuple(
                outcome.value for outcome in fixture.simulator_quote_outcomes
            ),
            "required_checks": fixture.required_checks,
        }
        for fixture in rehackt_fixtures()
    ]

    _assert_no_float(payload)
    json.dumps(payload, sort_keys=True)
