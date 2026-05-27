"""Unit tests for MorphoLpClient + dataclass shape.

Read-only adapter; full GraphQL wiring is TODO. These tests cover the
dataclass surface + Decimal/int handling that's critical for off-chain
planning (no on-chain decisions made here).
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from degenbot.execution.degenbot_ipc import (
    MorphoLiquidationOpportunityEnvelope,
    decode_morpho_liquidation_opportunity,
    encode_morpho_liquidation_opportunity,
)
from degenbot.execution.morpho_lp_adapter import (
    MorphoApiMetadata,
    MorphoLiquidationCandidate,
    MorphoLiquidationLiveRiskFeeds,
    MorphoLiquidationRankingConfig,
    MorphoLiquidationRevalidation,
    MorphoLpClient,
    MorphoMarket,
    MorphoMarketParams,
    MorphoOnchainMarketState,
    MorphoOnchainPosition,
    MorphoPosition,
    MorphoSwapBackQuote,
    build_standard_liquidation_candidate_payload,
    build_standard_liquidation_plan,
    compose_standard_liquidation_executor_path,
    encode_morpho_liquidate_calldata,
    estimate_standard_liquidation_collateral_seized,
    filter_markets_for_metadata,
    liquidation_bonus_bps,
    liquidation_incentive_factor_wad,
    rank_liquidation_candidates_for_screening,
    ranking_config_from_live_risk_feeds,
)

if TYPE_CHECKING:
    from pathlib import Path

    from degenbot.execution.morpho_lp_adapter import MorphoLiquidationPlan

# Canonical Arbitrum addresses used in fixtures (from §07 §1.2 / §6).
# Morpho Blue singleton on Arbitrum (canonical; mirrors
# contracts/script/config/arbitrum-one.json lenders.morphoBlue +
# coordinator/src/router/registry.ts MORPHO_SINGLETON).
_MORPHO_BLUE = "0x6c247b1F6182318877311737BaC0844bAa518F5e"
_MORPHO_GRAPHQL = "https://api.morpho.org/graphql"
_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
_ORACLE = "0x0000000000000000000000000000000000000222"
_IRM = "0x0000000000000000000000000000000000000111"
_USER = "0xdead0000000000000000000000000000000000ad"
_USDC_SYMBOL = "USDC"
_WETH_SYMBOL = "WETH"


class TestMorphoMarketParams:
    def test_market_id_is_keccak_of_abi_encoded_five_tuple(self) -> None:
        params = MorphoMarketParams(
            loan_token=_USDC,
            collateral_token=_WETH,
            oracle=_ORACLE,
            irm=_IRM,
            lltv=860_000_000_000_000_000,
        )

        assert params.id() == "0x5df0a1ef395fcf718ac150fd4ad8835057f827920778c56d9b9a3ace5697526d"

    def test_market_id_changes_when_any_parameter_changes(self) -> None:
        base = MorphoMarketParams(
            loan_token=_USDC,
            collateral_token=_WETH,
            oracle=_ORACLE,
            irm=_IRM,
            lltv=860_000_000_000_000_000,
        )
        changed = MorphoMarketParams(
            loan_token=_USDC,
            collateral_token=_WETH,
            oracle=_ORACLE,
            irm=_IRM,
            lltv=915_000_000_000_000_000,
        )

        assert base.id() != changed.id()

    def test_market_id_rejects_zero_or_malformed_addresses(self) -> None:
        params = MorphoMarketParams(
            loan_token="0x0000000000000000000000000000000000000000",
            collateral_token=_WETH,
            oracle=_ORACLE,
            irm=_IRM,
            lltv=860_000_000_000_000_000,
        )

        with pytest.raises(ValueError, match="non-zero 20-byte address"):
            params.id()


class TestMorphoMarket:
    def test_decimal_passthrough_preserves_full_precision(self) -> None:
        m = MorphoMarket(
            id="0x" + "11" * 32,
            loan_token=_USDC,
            collateral_token=_WETH,
            lltv=860_000_000_000_000_000,  # 86% LLTV in 1e18 wad
            irm_address=_IRM,
            oracle_address=_ORACLE,
            supply_apy_str="0.043512345678901234",
            borrow_apy_str="0.063412345678901234",
            total_supply_assets_str="123456789012345",
            total_borrow_assets_str="98765432109876",
            fee_str="0.001",
            last_update_ts=1_700_000_000,
        )
        assert m.supply_apy == Decimal("0.043512345678901234")
        assert m.borrow_apy == Decimal("0.063412345678901234")
        assert m.fee == Decimal("0.001")
        assert isinstance(m.supply_apy, Decimal)
        assert m.market_params == MorphoMarketParams(
            loan_token=_USDC,
            collateral_token=_WETH,
            oracle=_ORACLE,
            irm=_IRM,
            lltv=860_000_000_000_000_000,
        )
        assert m.derived_id == "0x5df0a1ef395fcf718ac150fd4ad8835057f827920778c56d9b9a3ace5697526d"

    def test_liquidation_incentive_factor_matches_morpho_formula(self) -> None:
        low_lltv = 385_000_000_000_000_000
        mid_lltv = 860_000_000_000_000_000
        high_lltv = 945_000_000_000_000_000

        assert liquidation_incentive_factor_wad(low_lltv) == 1_150_000_000_000_000_000
        assert liquidation_bonus_bps(low_lltv) == 1_500
        assert liquidation_bonus_bps(mid_lltv) == 438
        assert liquidation_bonus_bps(high_lltv) == 167

    def test_market_exposes_liquidation_bonus_for_candidate_ranking(self) -> None:
        market = MorphoMarket(
            id="0x" + "11" * 32,
            loan_token=_USDC,
            collateral_token=_WETH,
            lltv=945_000_000_000_000_000,
            irm_address=_IRM,
            oracle_address=_ORACLE,
            supply_apy_str="0",
            borrow_apy_str="0",
            total_supply_assets_str="0",
            total_borrow_assets_str="0",
            fee_str="0",
            last_update_ts=0,
        )

        assert market.liquidation_bonus_bps == 167

    def test_liquidation_incentive_factor_rejects_invalid_lltv(self) -> None:
        with pytest.raises(ValueError, match="LLTV"):
            liquidation_incentive_factor_wad(10**18)

    def test_total_assets_coerce_to_int_exactly(self) -> None:
        m = MorphoMarket(
            id="0x" + "11" * 32,
            loan_token=_USDC,
            collateral_token=_WETH,
            lltv=0,
            irm_address="0x0000000000000000000000000000000000000111",
            oracle_address="0x0000000000000000000000000000000000000222",
            supply_apy_str="0",
            borrow_apy_str="0",
            total_supply_assets_str="999999999999999999999999999999",
            total_borrow_assets_str="0",
            fee_str="0",
            last_update_ts=0,
        )
        assert m.total_supply_assets == 999_999_999_999_999_999_999_999_999_999
        assert m.total_borrow_assets == 0


class TestMorphoPosition:
    def test_position_share_and_collateral_int_passthrough(self) -> None:
        p = MorphoPosition(
            market_id="0x" + "22" * 32,
            user=_USER,
            supply_shares_str="1000000000000000000",
            borrow_shares_str="500000000000000000",
            collateral_str="2000000000000000000",
        )
        assert p.supply_shares == 1_000_000_000_000_000_000
        assert p.borrow_shares == 500_000_000_000_000_000
        assert p.collateral == 2_000_000_000_000_000_000


class TestMorphoLiquidationRanking:
    def test_ranks_by_lif_adjusted_net_edge_not_health_factor_alone(self) -> None:
        low_lltv = _ranking_candidate(
            "0x" + "01" * 32,
            lltv=385_000_000_000_000_000,
            borrower="0x1111000000000000000000000000000000000001",
            borrow_assets_usd="50000",
            collateral_usd="80000",
            health_factor="0.99",
        )
        high_lltv = _ranking_candidate(
            "0x" + "02" * 32,
            lltv=945_000_000_000_000_000,
            borrower="0x1111000000000000000000000000000000000002",
            borrow_assets_usd="200000",
            collateral_usd="260000",
            health_factor="0.80",
        )

        ranked = rank_liquidation_candidates_for_screening(
            [high_lltv, low_lltv],
            config=MorphoLiquidationRankingConfig(
                estimated_gas_cost_usd=Decimal(25),
                flash_fee_bps_by_loan_token={_USDC.lower(): 5},
                swap_cost_bps_by_collateral_token={_WETH.lower(): 20},
                oracle_risk_bps_by_market_id={low_lltv.market.id.lower(): 10},
            ),
        )

        assert [item.market_id for item in ranked] == [low_lltv.market.id, high_lltv.market.id]
        assert ranked[0].liquidation_bonus_bps == 1500
        assert ranked[0].gross_bonus_usd == Decimal(7500)
        assert ranked[0].estimated_flash_fee_usd == Decimal(25)
        assert ranked[0].estimated_swap_cost_usd == Decimal(100)
        assert ranked[0].oracle_risk_penalty_usd == Decimal(50)
        assert ranked[0].net_edge_usd == Decimal(7300)

    def test_bad_debt_risk_is_excluded_unless_policy_allows_it(self) -> None:
        bad_debt = _ranking_candidate(
            "0x" + "03" * 32,
            lltv=860_000_000_000_000_000,
            borrower="0x1111000000000000000000000000000000000003",
            borrow_assets_usd="100000",
            collateral_usd="90000",
            health_factor="0.70",
        )

        assert rank_liquidation_candidates_for_screening([bad_debt]) == []

        ranked = rank_liquidation_candidates_for_screening(
            [bad_debt],
            config=MorphoLiquidationRankingConfig(include_bad_debt=True),
        )

        assert len(ranked) == 1
        assert ranked[0].bad_debt_risk

    def test_swap_back_liquidity_proxy_is_fail_closed_when_supplied(self) -> None:
        insufficient = _ranking_candidate(
            "0x" + "04" * 32,
            lltv=860_000_000_000_000_000,
            borrower="0x1111000000000000000000000000000000000004",
            borrow_assets_usd="100000",
            collateral_usd="140000",
            health_factor="0.94",
            collateral_token=_WETH,
        )
        sufficient = _ranking_candidate(
            "0x" + "05" * 32,
            lltv=860_000_000_000_000_000,
            borrower="0x1111000000000000000000000000000000000005",
            borrow_assets_usd="75000",
            collateral_usd="100000",
            health_factor="0.95",
            collateral_token=_USDC,
        )

        ranked = rank_liquidation_candidates_for_screening(
            [insufficient, sufficient],
            config=MorphoLiquidationRankingConfig(
                swap_back_liquidity_usd_by_collateral_token={
                    _WETH.lower(): Decimal(50000),
                    _USDC.lower(): Decimal(100000),
                },
            ),
        )

        assert [item.market_id for item in ranked] == [sufficient.market.id]
        assert ranked[0].swap_back_liquidity_usd == Decimal(100000)
        assert ranked[0].swap_back_liquidity_shortfall_usd == Decimal(0)

    def test_tie_breaks_by_lower_health_factor_after_economic_score(self) -> None:
        safer = _ranking_candidate(
            "0x" + "06" * 32,
            lltv=860_000_000_000_000_000,
            borrower="0x1111000000000000000000000000000000000006",
            borrow_assets_usd="100000",
            collateral_usd="150000",
            health_factor="0.98",
        )
        riskier = _ranking_candidate(
            "0x" + "07" * 32,
            lltv=860_000_000_000_000_000,
            borrower="0x1111000000000000000000000000000000000007",
            borrow_assets_usd="100000",
            collateral_usd="150000",
            health_factor="0.80",
        )

        ranked = rank_liquidation_candidates_for_screening([safer, riskier])

        assert [item.market_id for item in ranked] == [riskier.market.id, safer.market.id]

    def test_ranking_config_from_live_risk_feeds_normalizes_gas_and_policy_inputs(self) -> None:
        config = ranking_config_from_live_risk_feeds(
            MorphoLiquidationLiveRiskFeeds(
                estimated_gas_units=250_000,
                gas_price_wei=2_000_000_000,
                eth_price_usd=Decimal(3000),
                flash_fee_bps_by_loan_token={_USDC.lower(): 5},
                swap_cost_bps_by_collateral_token={_WETH.lower(): 20},
                oracle_risk_bps_by_market_id={"0x" + "11" * 32: 10},
                swap_back_liquidity_usd_by_collateral_token={_WETH.lower(): Decimal(100000)},
                min_net_edge_usd=Decimal(25),
            )
        )

        assert config.estimated_gas_cost_usd == Decimal("1.500000000")
        assert config.flash_fee_bps_by_loan_token == {_USDC.lower(): 5}
        assert config.swap_cost_bps_by_collateral_token == {_WETH.lower(): 20}
        assert config.oracle_risk_bps_by_market_id == {"0x" + "11" * 32: 10}
        assert config.swap_back_liquidity_usd_by_collateral_token == {
            _WETH.lower(): Decimal(100000)
        }
        assert config.min_net_edge_usd == Decimal(25)

    def test_ranking_config_from_live_risk_feeds_rejects_negative_inputs(self) -> None:
        with pytest.raises(ValueError, match="estimated_gas_units"):
            ranking_config_from_live_risk_feeds(
                MorphoLiquidationLiveRiskFeeds(
                    estimated_gas_units=-1,
                    gas_price_wei=1,
                    eth_price_usd=Decimal(1),
                )
            )


class TestMorphoLpClientLifecycle:
    async def test_async_context_manager_closes_httpx(self) -> None:
        async with MorphoLpClient(_MORPHO_BLUE, _MORPHO_GRAPHQL) as client:
            assert client is not None

    async def test_close_is_idempotent(self) -> None:
        client = MorphoLpClient(_MORPHO_BLUE, _MORPHO_GRAPHQL)
        await client.close()
        # second close should not raise
        await client.close()

    async def test_optional_rpc_url_and_bearer_token_accepted(self) -> None:
        async with MorphoLpClient(
            _MORPHO_BLUE,
            _MORPHO_GRAPHQL,
            bearer_token="placeholder-token",
            rpc_url="https://arb1.arbitrum.io/rpc",
        ) as client:
            assert client is not None


class TestMorphoLpClientQueries:
    async def test_list_markets_paginates_and_maps_exact_strings(self) -> None:
        client = _FakeMorphoLpClient([
            {"markets": {"items": [_market_payload("0x" + "11" * 32)]}},
            {"markets": {"items": []}},
        ])

        markets = await client.list_markets()

        assert [m.id for m in markets] == ["0x" + "11" * 32]
        assert "isIdle: false" in client.queries[0][0]
        assert markets[0].loan_token_symbol == _USDC_SYMBOL
        assert markets[0].loan_token_decimals == 6
        assert markets[0].collateral_token_symbol == _WETH_SYMBOL
        assert markets[0].collateral_token_decimals == 18
        assert markets[0].supply_apy_str == "0.03414218751066034"
        assert markets[0].borrow_apy_str == "0.038832719615162145"
        assert markets[0].total_supply_assets_str == "10187618968270"
        assert markets[0].total_borrow_assets_str == "8977487003172"
        assert markets[0].fee_str == "0"
        assert markets[0].utilization_str == "0.8812"
        assert markets[0].last_update_ts == 1_778_031_179

    async def test_get_market_maps_market_by_id(self) -> None:
        client = _FakeMorphoLpClient([{"marketById": _market_payload("0x" + "22" * 32)}])

        market = await client.get_market("0x" + "22" * 32)

        assert market.id == "0x" + "22" * 32
        assert market.loan_token == _USDC
        assert market.collateral_token == _WETH
        assert market.lltv == 860_000_000_000_000_000

    async def test_get_market_raises_for_missing_market(self) -> None:
        client = _FakeMorphoLpClient([{"marketById": None}])

        with pytest.raises(ValueError, match="Morpho market not found"):
            await client.get_market("0x" + "22" * 32)

    async def test_get_position_maps_single_position(self) -> None:
        client = _FakeMorphoLpClient([
            {"marketPosition": _position_payload("0x" + "33" * 32, _USER)}
        ])

        position = await client.get_position("0x" + "33" * 32, _USER)

        assert position.market_id == "0x" + "33" * 32
        assert position.user == _USER
        assert position.supply_shares == 123
        assert position.borrow_shares == 456
        assert position.collateral == 789
        assert position.supply_assets == 1000
        assert position.borrow_assets == 2000
        assert position.borrow_assets_usd == Decimal("1999.5")
        assert position.collateral_usd == Decimal("3001.25")
        assert position.health_factor == Decimal("0.99")

    async def test_get_priority_markets_returns_empty_without_query_for_empty_input(self) -> None:
        client = _FakeMorphoLpClient([])

        assert await client.get_priority_markets([]) == []
        assert client.queries == []

    async def test_get_priority_markets_maps_batched_response(self) -> None:
        client = _FakeMorphoLpClient([
            {
                "markets": {
                    "items": [_market_payload("0x" + "44" * 32), _market_payload("0x" + "55" * 32)]
                }
            }
        ])

        markets = await client.get_priority_markets(["0x" + "44" * 32, "0x" + "55" * 32])

        assert [m.id for m in markets] == ["0x" + "44" * 32, "0x" + "55" * 32]
        assert "uniqueKey_in" in client.queries[0][0]
        assert "isIdle: false" in client.queries[0][0]

    async def test_list_liquidation_candidates_pages_positions_by_health_factor(self) -> None:
        market = _market_dataclass("0x" + "66" * 32, loan_token=_USDC, collateral_token=_USDC)
        client = _FakeMorphoLpClient([
            {
                "marketPositions": {
                    "items": [_position_payload(market.id, _USER, health_factor="0.99")]
                }
            },
            {"marketPositions": {"items": []}},
        ])

        candidates = await client.list_liquidation_candidates(
            [market], max_health_factor=Decimal("1.02"), page_size=1
        )

        assert candidates == [
            MorphoLiquidationCandidate(
                market=market,
                position=MorphoPosition(
                    market_id=market.id,
                    user=_USER,
                    supply_shares_str="123",
                    borrow_shares_str="456",
                    collateral_str="789",
                    supply_assets_str="1000",
                    borrow_assets_str="2000",
                    borrow_assets_usd_str="1999.5",
                    collateral_usd_str="3001.25",
                    health_factor_str="0.99",
                ),
            )
        ]
        assert candidates[0].borrower == _USER
        assert candidates[0].repay_shares == 456
        assert candidates[0].health_factor == Decimal("0.99")
        assert "healthFactor_lte" in client.queries[0][0]
        assert client.queries[0][1]["maxHealthFactor"] == pytest.approx(1.02)

    async def test_list_liquidation_candidates_returns_empty_without_query_for_no_markets(
        self,
    ) -> None:
        client = _FakeMorphoLpClient([])

        assert await client.list_liquidation_candidates([]) == []
        assert client.queries == []

    def test_revalidate_liquidation_candidate_onchain_checks_market_and_position(self) -> None:
        market = _consistent_market(loan_token=_USDC, collateral_token=_WETH)
        candidate = MorphoLiquidationCandidate(
            market=market,
            position=MorphoPosition(
                market_id=market.id,
                user=_USER,
                supply_shares_str="0",
                borrow_shares_str="456",
                collateral_str="789",
                health_factor_str="0.99",
            ),
        )
        client = _FakeMorphoLpClient([])
        client.contract = _FakeMorphoContract(
            market_params=(
                market.loan_token,
                market.collateral_token,
                market.oracle_address,
                market.irm_address,
                market.lltv,
            ),
            position=(0, 456, 789),
            market_state=(1000, 100, 900, 456, 1_700_000_000, 0),
        )

        result = client.revalidate_liquidation_candidate_onchain(candidate)

        assert result.valid
        assert result.reasons == ()
        assert result.market_params == market.market_params
        assert result.position is not None
        assert result.position.borrow_shares == 456
        assert result.market_state is not None
        assert result.market_state.total_borrow_shares == 456

    def test_revalidate_liquidation_candidate_onchain_rejects_stale_repay_shares(self) -> None:
        market = _consistent_market(loan_token=_USDC, collateral_token=_WETH)
        candidate = MorphoLiquidationCandidate(
            market=market,
            position=MorphoPosition(
                market_id=market.id,
                user=_USER,
                supply_shares_str="0",
                borrow_shares_str="456",
                collateral_str="789",
                health_factor_str="0.99",
            ),
        )
        client = _FakeMorphoLpClient([])
        client.contract = _FakeMorphoContract(
            market_params=(
                market.loan_token,
                market.collateral_token,
                market.oracle_address,
                market.irm_address,
                market.lltv,
            ),
            position=(0, 1, 789),
            market_state=(1000, 100, 900, 1, 1_700_000_000, 0),
        )

        result = client.revalidate_liquidation_candidate_onchain(candidate)

        assert not result.valid
        assert result.reasons == ("candidate_repay_shares_exceed_onchain_borrow_shares",)

    def test_revalidate_liquidation_candidate_requires_rpc_url_for_real_client(self) -> None:
        market = _market_dataclass("0x" + "66" * 32, loan_token=_USDC, collateral_token=_WETH)
        candidate = MorphoLiquidationCandidate(
            market=market,
            position=MorphoPosition(
                market_id=market.id,
                user=_USER,
                supply_shares_str="0",
                borrow_shares_str="1",
                collateral_str="1",
            ),
        )
        client = MorphoLpClient(_MORPHO_BLUE, _MORPHO_GRAPHQL)

        with pytest.raises(ValueError, match="rpc_url is required"):
            client.revalidate_liquidation_candidate_onchain(candidate)

    def test_plan_standard_liquidation_recomputes_health_and_encodes_repaid_shares_path(
        self,
    ) -> None:
        market = _consistent_market(loan_token=_USDC, collateral_token=_WETH)
        candidate = MorphoLiquidationCandidate(
            market=market,
            position=MorphoPosition(
                market_id=market.id,
                user=_USER,
                supply_shares_str="0",
                borrow_shares_str="1000",
                collateral_str="100",
                health_factor_str="0.99",
            ),
        )
        client = _FakeMorphoLpClient([])
        client.oracle_price = 10**36
        client.contract = _FakeMorphoContract(
            market_params=(
                market.loan_token,
                market.collateral_token,
                market.oracle_address,
                market.irm_address,
                market.lltv,
            ),
            position=(0, 1000, 100),
            market_state=(1_000_000, 1_000_000, 1_000_000, 1000, 1_700_000_000, 0),
        )

        plan = client.plan_standard_liquidation(candidate, max_repay_shares=250, data=b"arb")

        assert not plan.healthy
        assert plan.collateral_price == 10**36
        assert plan.borrowed_assets == 1000
        assert plan.repay_assets == 250
        assert plan.collateral_value_assets == 100
        assert plan.max_borrow_assets == 86
        assert plan.health_factor_wad == 86_000_000_000_000_000
        assert plan.repay_shares == 250
        assert plan.borrower == _USER
        assert plan.market_id == market.id
        assert plan.calldata == encode_morpho_liquidate_calldata(
            market.market_params,
            borrower=_USER,
            seized_assets=0,
            repaid_shares=250,
            data=b"arb",
        )
        assert plan.calldata[:4].hex() == "d8eabcb8"
        step = plan.to_executor_swap_step(morpho_blue_address=_MORPHO_BLUE, amount_out_min=1)
        assert step.pool == _MORPHO_BLUE
        assert step.router == _MORPHO_BLUE
        assert step.call_data.startswith("0xd8eabcb8")
        assert step.token_in == _USDC
        assert step.token_out == _WETH
        assert step.amount_in == 250
        assert step.amount_out_min == 1
        assert not step.zero_for_one
        assert step.dex == "MorphoBlue"

    def test_compose_standard_liquidation_executor_path_adds_swap_back_step(self) -> None:
        plan = _liquidation_plan()
        quote = MorphoSwapBackQuote(
            source="paraswap",
            sell_token=_WETH,
            buy_token=_USDC,
            sell_amount=10**17,
            buy_amount=260_000_000,
            router="0x6A000F20005980200259B80c5102003040001068",
            calldata="0xabcdef",
            estimated_gas=200_000,
        )

        liquidation_step, swap_back_step = compose_standard_liquidation_executor_path(
            plan,
            morpho_blue_address=_MORPHO_BLUE,
            swap_back_quote=quote,
        )

        assert liquidation_step.dex == "MorphoBlue"
        assert liquidation_step.amount_out_min == quote.sell_amount
        assert swap_back_step.dex == "AggregatorV6"
        assert swap_back_step.router == quote.router
        assert swap_back_step.call_data == quote.calldata
        assert swap_back_step.token_in == _WETH
        assert swap_back_step.token_out == _USDC
        assert swap_back_step.amount_in == 0
        assert swap_back_step.amount_out_min == quote.buy_amount

    def test_compose_standard_liquidation_executor_path_rejects_wrong_swap_back_tokens(
        self,
    ) -> None:
        plan = _liquidation_plan()

        with pytest.raises(ValueError, match="sell_token"):
            compose_standard_liquidation_executor_path(
                plan,
                morpho_blue_address=_MORPHO_BLUE,
                swap_back_quote=MorphoSwapBackQuote(
                    source="paraswap",
                    sell_token=_USDC,
                    buy_token=_USDC,
                    sell_amount=1,
                    buy_amount=1,
                    router="0x6A000F20005980200259B80c5102003040001068",
                    calldata="0xabcdef",
                ),
            )

        with pytest.raises(ValueError, match="executable calldata"):
            compose_standard_liquidation_executor_path(
                plan,
                morpho_blue_address=_MORPHO_BLUE,
                swap_back_quote=MorphoSwapBackQuote(
                    source="paraswap",
                    sell_token=_WETH,
                    buy_token=_USDC,
                    sell_amount=1,
                    buy_amount=1,
                    router="0x6A000F20005980200259B80c5102003040001068",
                    calldata="0x",
                ),
            )

    def test_build_standard_liquidation_plan_rejects_healthy_position(self) -> None:
        market = _consistent_market(loan_token=_USDC, collateral_token=_WETH)
        revalidation = MorphoLiquidationRevalidation(
            candidate=_candidate_for_market(market, borrow_shares=1000),
            market_params=market.market_params,
            position=MorphoOnchainPosition(supply_shares=0, borrow_shares=1000, collateral=2_000),
            market_state=MorphoOnchainMarketState(
                total_supply_assets=1_000_000,
                total_supply_shares=1_000_000,
                total_borrow_assets=1_000_000,
                total_borrow_shares=1000,
                last_update=1_700_000_000,
                fee=0,
            ),
            reasons=(),
        )

        with pytest.raises(ValueError, match="healthy Morpho position"):
            build_standard_liquidation_plan(revalidation, collateral_price=10**36)

    def test_encode_morpho_liquidate_calldata_requires_exactly_one_amount_mode(self) -> None:
        market = _consistent_market(loan_token=_USDC, collateral_token=_WETH)

        with pytest.raises(ValueError, match="exactly one"):
            encode_morpho_liquidate_calldata(
                market.market_params,
                borrower=_USER,
                seized_assets=0,
                repaid_shares=0,
            )

        with pytest.raises(ValueError, match="exactly one"):
            encode_morpho_liquidate_calldata(
                market.market_params,
                borrower=_USER,
                seized_assets=1,
                repaid_shares=1,
            )

    def test_standard_liquidation_candidate_payload_includes_stage_one_fields(self) -> None:
        plan = _liquidation_plan()
        priority = rank_liquidation_candidates_for_screening(
            [plan.revalidation.candidate],
            config=MorphoLiquidationRankingConfig(
                estimated_gas_cost_usd=Decimal("1.5"),
                flash_fee_bps_by_loan_token={_USDC.lower(): 5},
                swap_cost_bps_by_collateral_token={_WETH.lower(): 20},
                oracle_risk_bps_by_market_id={plan.market_id.lower(): 10},
                swap_back_liquidity_usd_by_collateral_token={_WETH.lower(): Decimal(5000)},
                min_net_edge_usd=Decimal(0),
            ),
        )[0]

        payload = build_standard_liquidation_candidate_payload(priority, plan)
        wire = payload.to_wire()

        assert wire["payloadVersion"] == 1
        assert wire["marketId"] == plan.market_id
        assert wire["marketParams"] == {
            "loanToken": _USDC,
            "collateralToken": _WETH,
            "oracle": _ORACLE,
            "irm": _IRM,
            "lltv": "860000000000000000",
        }
        assert wire["borrower"] == _USER
        assert wire["repaidShares"] == "250"
        assert wire["loanToken"] == _USDC
        assert wire["collateralToken"] == _WETH
        assert wire["repayAssets"] == str(plan.repay_assets)
        assert wire["expectedCollateralSeized"] == str(
            estimate_standard_liquidation_collateral_seized(plan)
        )
        assert wire["rankingScoreUsd"] == priority.net_edge_usd.to_eng_string()
        assert wire["badDebtClassification"] == "collateralized"
        assert wire["riskCosts"] == {
            "estimatedFlashFeeUsd": priority.estimated_flash_fee_usd.to_eng_string(),
            "estimatedSwapCostUsd": priority.estimated_swap_cost_usd.to_eng_string(),
            "estimatedGasCostUsd": priority.estimated_gas_cost_usd.to_eng_string(),
            "oracleRiskPenaltyUsd": priority.oracle_risk_penalty_usd.to_eng_string(),
            "swapBackLiquidityUsd": "5000",
            "swapBackLiquidityShortfallUsd": "0",
        }

    def test_standard_liquidation_candidate_payload_marks_bad_debt_lane(self) -> None:
        market = _consistent_market(loan_token=_USDC, collateral_token=_WETH)
        bad_debt = MorphoLiquidationCandidate(
            market=market,
            position=MorphoPosition(
                market_id=market.id,
                user=_USER,
                supply_shares_str="0",
                borrow_shares_str="1000",
                collateral_str="100",
                borrow_assets_str="1000",
                borrow_assets_usd_str="1000",
                collateral_usd_str="900",
                health_factor_str="0.80",
            ),
        )
        priority = rank_liquidation_candidates_for_screening(
            [bad_debt],
            config=MorphoLiquidationRankingConfig(include_bad_debt=True),
        )[0]
        plan = _liquidation_plan_for_candidate(bad_debt, max_repay_shares=250)

        payload = build_standard_liquidation_candidate_payload(priority, plan)

        assert payload.bad_debt_classification == "bad_debt"
        assert payload.to_wire()["badDebtClassification"] == "bad_debt"
        assert payload.repaid_shares == 250

    def test_stage_one_payload_wraps_into_coordinator_morpho_liquidation_ipc(self) -> None:
        plan = _liquidation_plan()
        priority = rank_liquidation_candidates_for_screening(
            [plan.revalidation.candidate],
            config=MorphoLiquidationRankingConfig(
                estimated_gas_cost_usd=Decimal("1.5"),
                flash_fee_bps_by_loan_token={_USDC.lower(): 5},
                swap_cost_bps_by_collateral_token={_WETH.lower(): 20},
                oracle_risk_bps_by_market_id={plan.market_id.lower(): 10},
                swap_back_liquidity_usd_by_collateral_token={_WETH.lower(): Decimal(5000)},
            ),
        )[0]
        payload = build_standard_liquidation_candidate_payload(priority, plan)

        encoded = encode_morpho_liquidation_opportunity(
            payload.to_wire(),
            MorphoLiquidationOpportunityEnvelope(
                opportunity_id="morpho-stage6-1",
                detected_at_ns=1_700_000_000_000_000_000,
                morpho_blue_address=_MORPHO_BLUE,
                estimated_profit_wei=1_250_000,
                flash_amount=plan.repay_assets,
                risk_cost_wei=1000,
            ),
        )
        decoded = decode_morpho_liquidation_opportunity(encoded)
        kind = decoded["kind"]["MorphoLiquidation"]

        assert decoded["id"] == "morpho-stage6-1"
        assert decoded["kind"].keys() == {"MorphoLiquidation"}
        assert decoded["token_in"] == _USDC
        assert decoded["token_out"] == _WETH
        assert decoded["flash_token"] == _USDC
        assert decoded["flash_amount"] == str(plan.repay_assets)
        assert decoded["path"] == []
        assert decoded["pool_addresses"] == [_MORPHO_BLUE]
        assert kind["market_id"] == plan.market_id
        assert kind["market_params"] == {
            "loan_token": _USDC,
            "collateral_token": _WETH,
            "oracle": _ORACLE,
            "irm": _IRM,
            "lltv": "860000000000000000",
        }
        assert kind["borrower"] == _USER
        assert kind["repaid_shares"] == str(plan.repay_shares)
        assert kind["expected_seized_assets"] == str(
            estimate_standard_liquidation_collateral_seized(plan)
        )
        assert kind["risk_cost_wei"] == "1000"
        assert kind["bad_debt_mode"] == "none"


class TestMorphoApiMetadata:
    def test_loads_arbitrum_metadata_for_fail_closed_screening(self, tmp_path: Path) -> None:
        _write_metadata_fixture(tmp_path)

        metadata = MorphoApiMetadata.load(tmp_path)

        assert metadata.is_token_listed(_USDC)
        assert not metadata.is_token_listed(_WETH)
        assert metadata.vault_v2_addresses == frozenset({
            "0xbeeff1d5de8f79ff37a151681100b039661da518"
        })
        assert metadata.legacy_vault_addresses == frozenset({
            "0xa60643c90a542a95026c0f1dbdb0615ff42019cf"
        })
        assert metadata.should_skip_market("0x" + "33" * 32)
        assert metadata.should_skip_market("0x" + "44" * 32)
        assert metadata.should_skip_vault("0xa60643c90A542A95026C0F1dbdB0615fF42019Cf")

    def test_missing_metadata_file_fails_loudly(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="missing Morpho metadata file"):
            MorphoApiMetadata.load(tmp_path)

    def test_filter_markets_for_metadata_skips_blacklists_warnings_and_unlisted_tokens(
        self, tmp_path: Path
    ) -> None:
        _write_metadata_fixture(tmp_path)
        metadata = MorphoApiMetadata.load(tmp_path)
        good = _market_dataclass("0x" + "11" * 32, loan_token=_USDC, collateral_token=_USDC)
        red = _market_dataclass("0x" + "44" * 32, loan_token=_USDC, collateral_token=_USDC)
        unlisted = _market_dataclass("0x" + "55" * 32, loan_token=_USDC, collateral_token=_WETH)

        assert filter_markets_for_metadata([good, red, unlisted], metadata) == [good]


def _write_metadata_fixture(root: Path) -> None:
    (root / "tokens.json").write_text(
        json.dumps([
            {
                "chainId": 42161,
                "address": _USDC,
                "name": "USD Coin",
                "symbol": _USDC_SYMBOL,
                "decimals": 6,
                "metadata": {"tags": ["stablecoin", "simple-permit"]},
                "isListed": True,
            },
            {
                "chainId": 42161,
                "address": _WETH,
                "name": "Wrapped Ether",
                "symbol": _WETH_SYMBOL,
                "decimals": 18,
                "metadata": {"tags": ["eth"]},
                "isListed": False,
            },
        ])
    )
    (root / "vaults-v2-listing.json").write_text(
        json.dumps([{"chainId": 42161, "address": "0xbeeff1D5dE8F79ff37a151681100B039661da518"}])
    )
    (root / "vaults-listing.json").write_text(
        json.dumps([{"chainId": 42161, "address": "0xa60643c90A542A95026C0F1dbdB0615fF42019Cf"}])
    )
    (root / "markets-blacklist.json").write_text(
        json.dumps([{"chainId": 42161, "id": "0x" + "33" * 32, "countryCodes": ["*"]}])
    )
    (root / "custom-warnings.json").write_text(
        json.dumps([
            {
                "chainId": 42161,
                "marketId": "0x" + "44" * 32,
                "level": "red",
                "metadata": {"content": "market risk"},
            },
            {
                "chainId": 42161,
                "vaultAddress": "0xa60643c90A542A95026C0F1dbdB0615fF42019Cf",
                "level": "red",
                "metadata": {"content": "vault risk"},
            },
        ])
    )


class _FakeMorphoLpClient(MorphoLpClient):
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = responses
        self.queries: list[tuple[str, dict[str, object]]] = []
        self.contract: _FakeMorphoContract | None = None
        self.oracle_price = 0
        super().__init__(_MORPHO_BLUE, _MORPHO_GRAPHQL)

    async def _query(self, query: str, variables: dict[str, object]) -> dict[str, object]:
        self.queries.append((query, variables))
        if not self.responses:
            msg = "unexpected GraphQL query"
            raise AssertionError(msg)
        return self.responses.pop(0)

    def _morpho_contract(self) -> _FakeMorphoContract:
        if self.contract is None:
            msg = "missing fake Morpho contract"
            raise AssertionError(msg)
        return self.contract

    def _oracle_price(self, _oracle_address: str) -> int:
        return self.oracle_price


class _FakeContractCall:
    def __init__(self, value: object) -> None:
        self.value = value

    def call(self) -> object:
        return self.value


class _FakeMorphoFunctions:
    def __init__(
        self,
        *,
        market_params: tuple[str, str, str, str, int],
        position: tuple[int, int, int],
        market_state: tuple[int, int, int, int, int, int],
    ) -> None:
        self._market_params = market_params
        self._position = position
        self._market_state = market_state

    def idToMarketParams(self, _market_id: bytes) -> _FakeContractCall:  # noqa: N802
        return _FakeContractCall(self._market_params)

    def position(self, _market_id: bytes, _user: str) -> _FakeContractCall:
        return _FakeContractCall(self._position)

    def market(self, _market_id: bytes) -> _FakeContractCall:
        return _FakeContractCall(self._market_state)


class _FakeMorphoContract:
    def __init__(
        self,
        *,
        market_params: tuple[str, str, str, str, int],
        position: tuple[int, int, int],
        market_state: tuple[int, int, int, int, int, int],
    ) -> None:
        self.functions = _FakeMorphoFunctions(
            market_params=market_params,
            position=position,
            market_state=market_state,
        )


def _market_payload(market_id: str) -> dict[str, object]:
    return {
        "marketId": market_id,
        "lltv": "860000000000000000",
        "irmAddress": _IRM,
        "oracle": {"address": _ORACLE},
        "loanAsset": {"address": _USDC, "symbol": _USDC_SYMBOL, "decimals": 6},
        "collateralAsset": {"address": _WETH, "symbol": _WETH_SYMBOL, "decimals": 18},
        "state": {
            "supplyApy": 0.03414218751066034,
            "borrowApy": 0.038832719615162145,
            "borrowAssets": 8_977_487_003_172,
            "supplyAssets": 10_187_618_968_270,
            "fee": 0,
            "utilization": "0.8812",
            "timestamp": 1_778_031_179,
        },
    }


def _position_payload(
    market_id: str, user: str, *, health_factor: str = "0.99"
) -> dict[str, object]:
    return {
        "healthFactor": health_factor,
        "market": {"marketId": market_id},
        "user": {"address": user},
        "state": {
            "supplyShares": "123",
            "borrowShares": "456",
            "collateral": "789",
            "supplyAssets": 1000,
            "borrowAssets": 2000,
            "borrowAssetsUsd": "1999.5",
            "collateralUsd": "3001.25",
        },
    }


def _market_dataclass(market_id: str, *, loan_token: str, collateral_token: str) -> MorphoMarket:
    return MorphoMarket(
        id=market_id,
        loan_token=loan_token,
        collateral_token=collateral_token,
        lltv=860_000_000_000_000_000,
        irm_address=_IRM,
        oracle_address=_ORACLE,
        supply_apy_str="0",
        borrow_apy_str="0",
        total_supply_assets_str="0",
        total_borrow_assets_str="0",
        fee_str="0",
        last_update_ts=0,
    )


def _ranking_candidate(
    market_id: str,
    *,
    lltv: int,
    borrower: str,
    borrow_assets_usd: str,
    collateral_usd: str,
    health_factor: str,
    collateral_token: str = _WETH,
) -> MorphoLiquidationCandidate:
    return MorphoLiquidationCandidate(
        market=(
            MorphoMarket(
                id=market_id,
                loan_token=_USDC,
                collateral_token=collateral_token,
                lltv=lltv,
                irm_address=_IRM,
                oracle_address=_ORACLE,
                supply_apy_str="0",
                borrow_apy_str="0",
                total_supply_assets_str="0",
                total_borrow_assets_str="0",
                fee_str="0",
                last_update_ts=0,
            )
        ),
        position=MorphoPosition(
            market_id=market_id,
            user=borrower,
            supply_shares_str="0",
            borrow_shares_str="1",
            collateral_str="1",
            borrow_assets_str="1",
            borrow_assets_usd_str=borrow_assets_usd,
            collateral_usd_str=collateral_usd,
            health_factor_str=health_factor,
        ),
    )


def _consistent_market(*, loan_token: str, collateral_token: str) -> MorphoMarket:
    market_params = MorphoMarketParams(
        loan_token=loan_token,
        collateral_token=collateral_token,
        oracle=_ORACLE,
        irm=_IRM,
        lltv=860_000_000_000_000_000,
    )
    return _market_dataclass(
        market_params.id(), loan_token=loan_token, collateral_token=collateral_token
    )


def _candidate_for_market(
    market: MorphoMarket, *, borrow_shares: int
) -> MorphoLiquidationCandidate:
    return MorphoLiquidationCandidate(
        market=market,
        position=MorphoPosition(
            market_id=market.id,
            user=_USER,
            supply_shares_str="0",
            borrow_shares_str=str(borrow_shares),
            collateral_str="0",
            borrow_assets_str="100",
            borrow_assets_usd_str="100",
            collateral_usd_str="150",
            health_factor_str="0.99",
        ),
    )


def _liquidation_plan() -> MorphoLiquidationPlan:
    market = _consistent_market(loan_token=_USDC, collateral_token=_WETH)
    candidate = _candidate_for_market(market, borrow_shares=1000)
    return _liquidation_plan_for_candidate(candidate, max_repay_shares=250)


def _liquidation_plan_for_candidate(
    candidate: MorphoLiquidationCandidate,
    *,
    max_repay_shares: int,
) -> MorphoLiquidationPlan:
    revalidation = MorphoLiquidationRevalidation(
        candidate=candidate,
        market_params=candidate.market.market_params,
        position=MorphoOnchainPosition(supply_shares=0, borrow_shares=1000, collateral=100),
        market_state=MorphoOnchainMarketState(
            total_supply_assets=1_000_000,
            total_supply_shares=1_000_000,
            total_borrow_assets=1_000_000,
            total_borrow_shares=1000,
            last_update=1_700_000_000,
            fee=0,
        ),
        reasons=(),
    )
    return build_standard_liquidation_plan(
        revalidation,
        collateral_price=10**36,
        max_repay_shares=max_repay_shares,
    )
