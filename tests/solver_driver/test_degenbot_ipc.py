from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest
from degenbot.execution.degenbot_ipc import (
    BotBestOpportunityRequest,
    DegenbotRuntime,
    MorphoLiquidationOpportunityEnvelope,
    RegistryBackedDegenbotSimulator,
    RegistryBackedDegenbotSubscriptionSource,
    SimulationInputError,
    SimulationResult,
    SimulationUnavailableError,
    SwapStep,
    TokenPair,
    decode_control_message,
    decode_morpho_liquidation_opportunity,
    encode_error,
    encode_heartbeat,
    encode_morpho_liquidation_opportunity,
    encode_opportunity_from_bot,
    encode_opportunity_from_simulation,
    encode_pool_update_from_degenbot,
    parse_best_opportunity_request,
    parse_simulation_request,
    parse_subscribe_request,
    resolve_degenbot_source_path,
)

_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
_MORPHO_BLUE = "0x6c247b1F6182318877311737BaC0844bAa518F5e"


def test_decode_control_message_accepts_internal_tags() -> None:
    assert decode_control_message('{"kind":"Ping"}') == {"kind": "Ping"}


def test_decode_control_message_accepts_external_tags() -> None:
    assert decode_control_message('{"Ping":{}}') == {"kind": "Ping"}


def test_resolve_degenbot_source_path_from_repo_relative_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    assert (
        resolve_degenbot_source_path(Path("vendor/degenbot"))
        == (repo_root / "vendor/degenbot").resolve()
    )


def test_encode_heartbeat_matches_coordinator_wire_shape() -> None:
    encoded = encode_heartbeat(
        DegenbotRuntime(version="0.6.0a2", source_path=Path("vendor/degenbot"))
    )
    decoded = json.loads(encoded)

    assert decoded["Heartbeat"]["degenbot_version"] == "0.6.0a2"
    assert isinstance(decoded["Heartbeat"]["ts_ms"], int)


def test_encode_error_matches_coordinator_wire_shape() -> None:
    encoded = encode_error("simulation_requires_strategy_adapter", "not enabled", {"x": 1})
    decoded = json.loads(encoded)

    assert decoded == {
        "Error": {
            "code": "simulation_requires_strategy_adapter",
            "message": "not enabled",
            "context": {"x": 1},
        },
    }


def test_parse_simulation_request_accepts_coordinator_wire_shape() -> None:
    path, amount_in = parse_simulation_request({
        "kind": "Simulate",
        "amount_in": "1000",
        "path": [
            {
                "pool": "0x1111111111111111111111111111111111111111",
                "router": "0x4444444444444444444444444444444444444444",
                "call_data": "0x12345678",
                "token_in": "0x2222222222222222222222222222222222222222",
                "token_out": "0x3333333333333333333333333333333333333333",
                "amount_in": "1000",
                "amount_out_min": "990",
                "zero_for_one": True,
                "dex": "UniswapV3",
                "fee": 500,
            },
        ],
    })

    assert amount_in == 1000
    assert path == (
        SwapStep(
            pool="0x1111111111111111111111111111111111111111",
            token_in="0x2222222222222222222222222222222222222222",
            token_out="0x3333333333333333333333333333333333333333",
            amount_in=1000,
            amount_out_min=990,
            zero_for_one=True,
            dex="UniswapV3",
            router="0x4444444444444444444444444444444444444444",
            call_data="0x12345678",
            fee=500,
        ),
    )


def test_parse_simulation_request_recognizes_forward_and_action_dex_names() -> None:
    path, _ = parse_simulation_request({
        "kind": "Simulate",
        "amount_in": "1000",
        "path": [
            {
                "pool": "0x1111111111111111111111111111111111111111",
                "token_in": "0x2222222222222222222222222222222222222222",
                "token_out": "0x3333333333333333333333333333333333333333",
                "amount_in": "1000",
                "amount_out_min": "990",
                "zero_for_one": True,
                "dex": "MorphoBlue",
            },
            {
                "pool": "0x1111111111111111111111111111111111111111",
                "token_in": "0x2222222222222222222222222222222222222222",
                "token_out": "0x3333333333333333333333333333333333333333",
                "amount_in": "1000",
                "amount_out_min": "990",
                "zero_for_one": True,
                "dex": "CamelotV3",
            },
        ],
    })

    assert [step.dex for step in path] == ["MorphoBlue", "CamelotV3"]


def test_parse_simulation_request_recognizes_address_keyed_degenbot_adapter_names() -> None:
    path, _ = parse_simulation_request({
        "kind": "Simulate",
        "amount_in": "1000",
        "path": [
            {
                "pool": "0x1111111111111111111111111111111111111111",
                "token_in": "0x2222222222222222222222222222222222222222",
                "token_out": "0x3333333333333333333333333333333333333333",
                "amount_in": "1000",
                "amount_out_min": "990",
                "zero_for_one": True,
                "dex": dex,
            }
            for dex in (
                "PancakeSwapV2",
                "PancakeSwapV3",
                "SushiSwapV2",
                "SushiSwapV3",
                "CamelotV2",
                "BalancerV2",
            )
        ],
    })

    assert [step.dex for step in path] == [
        "PancakeSwapV2",
        "PancakeSwapV3",
        "SushiSwapV2",
        "SushiSwapV3",
        "CamelotV2",
        "BalancerV2",
    ]


def test_parse_subscribe_request_accepts_pairs() -> None:
    pairs = parse_subscribe_request({
        "kind": "Subscribe",
        "pairs": [
            {
                "token0": _USDC,
                "token1": _WETH,
            },
        ],
    })

    assert pairs == (TokenPair(token0=_USDC, token1=_WETH),)


def test_parse_subscribe_request_rejects_same_token_pair() -> None:
    with pytest.raises(SimulationInputError, match="token0 and token1 must differ"):
        parse_subscribe_request({
            "kind": "Subscribe",
            "pairs": [
                {
                    "token0": _USDC,
                    "token1": _USDC.lower(),
                },
            ],
        })


def test_parse_best_opportunity_request_accepts_policy_fields() -> None:
    request = parse_best_opportunity_request({
        "kind": "BestOpportunity",
        "chain_id": "42161",
        "input_token": _WETH,
        "from_address": "0x000000000000000000000000000000000000dEaD",
        "min_profit": "100",
        "min_depth": 2,
        "max_depth": 4,
        "max_input": "1000000",
        "min_rate_of_exchange": "9/10",
    })

    assert request == BotBestOpportunityRequest(
        chain_id=42161,
        input_token=_WETH,
        from_address="0x000000000000000000000000000000000000dEaD",
        min_profit=100,
        min_depth=2,
        max_depth=4,
        max_input=1_000_000,
        min_rate_of_exchange=Fraction(9, 10),
    )


def test_encode_pool_update_from_degenbot_v2_state_matches_coordinator_wire_shape() -> None:
    class State:
        address = "0x1111111111111111111111111111111111111111"
        block = 123
        reserves_token0 = 1_000
        reserves_token1 = 2_000

    class Message:
        state = State()

    decoded = json.loads(encode_pool_update_from_degenbot(object(), Message()))

    assert decoded == {
        "PoolUpdate": {
            "address": "0x1111111111111111111111111111111111111111",
            "block_number": "123",
            "reserves": {
                "V2": {
                    "reserve0": "1000",
                    "reserve1": "2000",
                },
            },
        },
    }


def test_encode_opportunity_from_bot_builds_executable_v3_native_arb_path() -> None:
    class Token:
        def __init__(self, address: str) -> None:
            self.address = address

    pool = type("UniswapV3Pool", (), {})()
    pool.address = "0x1111111111111111111111111111111111111111"
    pool.token0 = Token(_WETH)
    pool.token1 = Token(_USDC)
    pool.fee = 500
    amounts = SimpleNamespace(
        pool=pool.address,
        amount_in=1_000,
        amount_out=1_100,
        amount_specified=1_000,
        zero_for_one=True,
    )
    result = SimpleNamespace(
        input_token=Token(_WETH),
        profit_token=Token(_WETH),
        input_amount=1_000,
        profit_amount=100,
        swap_amounts=(amounts,),
        state_block=123,
    )
    opportunity = SimpleNamespace(strategy_id="weth-cycle", result=result, swap_pools=(pool,))
    request = BotBestOpportunityRequest(
        chain_id=42161,
        input_token=_WETH,
        from_address="0x000000000000000000000000000000000000dEaD",
    )

    decoded = json.loads(encode_opportunity_from_bot(request, opportunity))
    opp = decoded["Opportunity"]

    assert opp["kind"] == "NativeArb"
    assert opp["token_in"] == _WETH.lower()
    assert opp["token_out"] == _WETH.lower()
    assert opp["amount_in"] == "1000"
    assert opp["expected_amount_out"] == "1100"
    assert opp["estimated_profit_wei"] == "100"
    assert opp["pool_addresses"] == [pool.address]
    assert opp["path"] == [
        {
            "pool": pool.address,
            "token_in": _WETH.lower(),
            "token_out": _USDC.lower(),
            "amount_in": "1000",
            "amount_out_min": "1100",
            "zero_for_one": True,
            "dex": "UniswapV3",
            "fee": 500,
        }
    ]


def test_registry_subscription_source_matches_multitoken_pool_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Token:
        def __init__(self, address: str) -> None:
            self.address = address

    class Pool:
        tokens = (
            Token(_USDC),
            Token(_WETH),
            Token("0xff970a61a04b1ca14834a43f5de4533ebddb5cc8"),
        )

    pool = Pool()
    registry = SimpleNamespace(
        _all_pools={(42161, "0x1111111111111111111111111111111111111111"): pool}
    )
    monkeypatch.setattr(
        "degenbot.connection.ipc.importlib.import_module",
        lambda _name: SimpleNamespace(pool_registry=registry),
    )

    source = RegistryBackedDegenbotSubscriptionSource()

    assert source._matching_pools((TokenPair(token0=_USDC, token1=_WETH),)) == (pool,)


def test_registry_simulator_rejects_uniswap_v4_without_pool_key() -> None:
    simulator = RegistryBackedDegenbotSimulator()

    step = SwapStep(
        pool="0x1111111111111111111111111111111111111111",
        token_in="0x2222222222222222222222222222222222222222",
        token_out="0x3333333333333333333333333333333333333333",
        amount_in=1000,
        amount_out_min=990,
        zero_for_one=True,
        dex="UniswapV4",
    )

    with pytest.raises(SimulationUnavailableError, match="requires a pool_key"):
        simulator.simulate_exact_input_path((step,), 1000)


def test_registry_simulator_uses_uniswap_v4_pool_key_registry_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Token:
        def __init__(self, address: str) -> None:
            self.address = address

    class V4Pool:
        address = "0x000000000004444c5dc75cB358380D2e3dE08A90"
        token0 = Token(_WETH)
        token1 = Token(_USDC)

        def calculate_tokens_out_from_tokens_in(
            self,
            *,
            token_in: Token,
            token_out: Token,
            token_in_quantity: int,
            override_state: object | None,
        ) -> int:
            assert token_in is self.token0
            assert token_out is self.token1
            assert token_in_quantity == 1000
            assert override_state is None
            return 1234

    class Registry:
        seen_pool_id: object | None = None

        def __init__(self, pool: V4Pool) -> None:
            self.pool = pool

        def get(
            self,
            *,
            chain_id: int,
            pool_address: str,
            pool_id: object | None = None,
        ) -> object | None:
            assert chain_id == 42161
            assert pool_address == self.pool.address
            self.seen_pool_id = pool_id
            return self.pool if pool_id is not None else None

    registry = Registry(V4Pool())
    monkeypatch.setattr(
        "degenbot.connection.ipc.importlib.import_module",
        lambda _name: SimpleNamespace(pool_registry=registry),
    )
    simulator = RegistryBackedDegenbotSimulator()

    step = SwapStep(
        pool=registry.pool.address,
        token_in=_WETH,
        token_out=_USDC,
        amount_in=1000,
        amount_out_min=1200,
        zero_for_one=True,
        dex="UniswapV4",
        pool_key={
            "currency0": _WETH,
            "currency1": _USDC,
            "fee": 100,
            "tick_spacing": 1,
            "hooks": "0x0000000000000000000000000000000000000000",
        },
        hook_data="0x",
        deadline=1_900_000_000,
    )

    result = simulator.simulate_exact_input_path((step,), 1000)

    assert result.amount_out == 1234
    assert result.path == (step,)
    assert registry.seen_pool_id is not None


def test_encode_opportunity_from_simulation_matches_coordinator_wire_shape() -> None:
    result = SimulationResult(
        amount_in=1000,
        amount_out=1100,
        path=(
            SwapStep(
                pool="0x1111111111111111111111111111111111111111",
                token_in="0x2222222222222222222222222222222222222222",
                token_out="0x3333333333333333333333333333333333333333",
                amount_in=1000,
                amount_out_min=990,
                zero_for_one=True,
                dex="UniswapV3",
                router="0x4444444444444444444444444444444444444444",
                call_data="0x12345678",
                fee=500,
                token_in_idx=0,
                token_out_idx=1,
                is_legacy=True,
            ),
        ),
    )

    decoded = json.loads(encode_opportunity_from_simulation(result))
    opp = decoded["Opportunity"]

    assert opp["kind"] == "NativeArb"
    assert opp["amount_in"] == "1000"
    assert opp["expected_amount_out"] == "1100"
    assert opp["estimated_profit_wei"] == "100"
    assert opp["path"][0]["dex"] == "UniswapV3"
    assert opp["path"][0]["router"] == "0x4444444444444444444444444444444444444444"
    assert opp["path"][0]["call_data"] == "0x12345678"
    assert opp["path"][0]["fee"] == 500
    assert opp["path"][0]["token_in_idx"] == 0
    assert opp["path"][0]["token_out_idx"] == 1
    assert opp["path"][0]["is_legacy"] is True


def test_encode_morpho_liquidation_opportunity_wraps_stage_one_payload() -> None:
    payload = _morpho_liquidation_payload()

    encoded = encode_morpho_liquidation_opportunity(
        payload,
        MorphoLiquidationOpportunityEnvelope(
            opportunity_id="morpho-liq-1",
            detected_at_ns=123456789,
            morpho_blue_address=_MORPHO_BLUE,
            estimated_profit_wei=12345,
            flash_amount=250,
            risk_cost_wei=1000,
        ),
    )
    decoded = json.loads(encoded)
    opp = decoded["Opportunity"]

    assert opp["id"] == "morpho-liq-1"
    assert opp["detected_at_ns"] == "123456789"
    assert opp["token_in"] == payload["loanToken"]
    assert opp["token_out"] == payload["collateralToken"]
    assert opp["amount_in"] == "250"
    assert opp["expected_amount_out"] == "259"
    assert opp["estimated_profit_wei"] == "12345"
    assert opp["flash_token"] == payload["loanToken"]
    assert opp["flash_amount"] == "250"
    assert opp["path"] == []
    assert opp["pool_addresses"] == [_MORPHO_BLUE]
    assert opp["kind"] == {
        "MorphoLiquidation": {
            "market_id": payload["marketId"],
            "market_params": {
                "loan_token": _USDC,
                "collateral_token": _WETH,
                "oracle": "0x0000000000000000000000000000000000000222",
                "irm": "0x0000000000000000000000000000000000000111",
                "lltv": "860000000000000000",
            },
            "borrower": "0xdead0000000000000000000000000000000000ad",
            "repaid_shares": "250",
            "expected_seized_assets": "259",
            "ranking_score_bps": "438",
            "risk_cost_wei": "1000",
            "bad_debt_mode": "none",
        },
    }


def test_decode_morpho_liquidation_opportunity_validates_required_payload() -> None:
    encoded = encode_morpho_liquidation_opportunity(
        _morpho_liquidation_payload(),
        MorphoLiquidationOpportunityEnvelope(
            opportunity_id="morpho-liq-1",
            detected_at_ns=123456789,
            morpho_blue_address=_MORPHO_BLUE,
            estimated_profit_wei=12345,
            flash_amount=250,
            risk_cost_wei=1000,
        ),
    )

    decoded = decode_morpho_liquidation_opportunity(encoded)
    payload = decoded["kind"]["MorphoLiquidation"]

    assert payload["bad_debt_mode"] == "none"
    assert payload["risk_cost_wei"] == "1000"
    assert payload["market_params"]["loan_token"] == _USDC
    assert decoded["estimated_profit_wei"] == "12345"
    assert decoded["path"] == []


def test_encode_morpho_liquidation_opportunity_rejects_incomplete_payload() -> None:
    payload = _morpho_liquidation_payload()
    del payload["riskCosts"]

    with pytest.raises(ValueError, match="missing required keys: riskCosts"):
        encode_morpho_liquidation_opportunity(
            payload,
            MorphoLiquidationOpportunityEnvelope(
                opportunity_id="morpho-liq-1",
                detected_at_ns=123456789,
                morpho_blue_address=_MORPHO_BLUE,
                estimated_profit_wei=12345,
            ),
        )


def _morpho_liquidation_payload() -> dict[str, object]:
    return {
        "payloadVersion": 1,
        "marketId": "0x" + "11" * 32,
        "marketParams": {
            "loanToken": _USDC,
            "collateralToken": _WETH,
            "oracle": "0x0000000000000000000000000000000000000222",
            "irm": "0x0000000000000000000000000000000000000111",
            "lltv": "860000000000000000",
        },
        "borrower": "0xdead0000000000000000000000000000000000ad",
        "repaidShares": "250",
        "loanToken": _USDC,
        "collateralToken": _WETH,
        "repayAssets": "250",
        "expectedCollateralSeized": "259",
        "healthFactorWad": "86000000000000000",
        "liquidationBonusBps": 438,
        "borrowAssetsUsd": "100",
        "collateralUsd": "150",
        "grossBonusUsd": "4.38",
        "rankingScoreUsd": "2.53",
        "riskCosts": {
            "estimatedFlashFeeUsd": "0.05",
            "estimatedSwapCostUsd": "0.2",
            "estimatedGasCostUsd": "1.5",
            "oracleRiskPenaltyUsd": "0.1",
            "swapBackLiquidityUsd": "5000",
            "swapBackLiquidityShortfallUsd": "0",
        },
        "badDebtClassification": "collateralized",
    }
