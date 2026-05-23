from degenbot.dispatch import compose_dispatch_envelope


def test_compose_dispatch_envelope_preserves_admitted_calldata_and_lane() -> None:
    plan = {
        "trace_id": "trace-native-1",
        "strategy": "native_arb",
        "chain_id": 42161,
        "target": "0x000000000000000000000000000000000000beef",
        "calldata": "0x12345678",
        "value": 0,
        "gas_limit": 500_000,
        "max_fee_per_gas": 1_000_000_000,
        "max_priority_fee_per_gas": 100_000_000,
        "deadline_ms": 10_000,
        "profit_token": "0x0000000000000000000000000000000000000001",
        "min_profit_wei": 100,
        "require_preflight": True,
        "dry_run": False,
        "broadcast_lane": "private_relay",
    }
    policy = {
        "expected_chain_id": 42161,
        "min_profit_wei": 50,
        "max_gas_limit": 1_000_000,
        "require_preflight": True,
        "require_live_sources": True,
        "min_gate_count": 1,
        "min_deadline_ms_from_now": 1_000,
        "allowed_targets": [plan["target"]],
        "allowed_lanes": ["private_relay"],
    }
    sources = [{"name": "same-block-pool-state", "block_number": 123, "observed_at_ns": 456}]
    gates = [{"name": "min-profit", "admitted": True}]
    simulation = {
        "success": True,
        "expected_profit_wei": 150,
        "gas_used": 250_000,
        "state_read_count": 8,
    }

    envelope = compose_dispatch_envelope(plan, policy, sources, gates, simulation, now_ms=8_000)

    assert envelope["trace_id"] == "trace-native-1"
    assert envelope["strategy"] == "native_arb"
    assert envelope["target"].lower() == plan["target"].lower()
    assert envelope["calldata"] == plan["calldata"]
    assert envelope["max_fee_per_gas"] == "1000000000"
    assert envelope["broadcast_lane"] == "private_relay"
    assert envelope["submit"] is True
    assert envelope["private_submission"] is True
    assert envelope["require_preflight"] is True
    assert envelope["engine_report"]["calldata_len"] == 4
