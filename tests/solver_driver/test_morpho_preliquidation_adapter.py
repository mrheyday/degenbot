"""Tests for the Morpho pre-liquidation discovery adapter."""

from __future__ import annotations

import pytest
from degenbot.execution.morpho_preliquidation_adapter import (
    ARBITRUM_CHAIN_ID,
    ORACLE_PRICE_SCALE,
    WAD,
    MorphoPreLiquidationAuthorization,
    MorphoPreLiquidationClient,
    MorphoPreLiquidationContract,
    MorphoPreLiquidationIndexedPosition,
    MorphoPreLiquidationPositionInput,
    MorphoPreLiquidationPositionSnapshot,
    authorized_contracts_for_borrower,
    ensure_hyperindex_market_id,
    evaluate_pre_liquidation_eligibility,
    hyperindex_market_id,
    pre_liquidation_authorization_from_graphql,
    pre_liquidation_contract_from_graphql,
    pre_liquidation_position_from_graphql,
    select_pre_liquidation_candidates,
    split_hyperindex_market_id,
    to_assets_up,
)

_HYPERINDEX = "https://example.invalid/graphql"
_MARKET_ID = "0x" + "11" * 32
_PRE_LIQUIDATION = "0x2222222222222222222222222222222222222222"
_PRE_LIQUIDATION_2 = "0x4444444444444444444444444444444444444444"
_ORACLE = "0x3333333333333333333333333333333333333333"
_BORROWER = "0x5555555555555555555555555555555555555555"
_OTHER_BORROWER = "0x6666666666666666666666666666666666666666"
_ZERO = "0x0000000000000000000000000000000000000000"


class TestMorphoPreLiquidationIds:
    def test_hyperindex_market_id_uses_official_chain_prefix(self) -> None:
        assert hyperindex_market_id(ARBITRUM_CHAIN_ID, _MARKET_ID) == f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}"

    def test_ensure_hyperindex_market_id_accepts_raw_or_indexed_id(self) -> None:
        indexed = f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}"

        assert ensure_hyperindex_market_id(ARBITRUM_CHAIN_ID, _MARKET_ID) == indexed
        assert ensure_hyperindex_market_id(ARBITRUM_CHAIN_ID, indexed) == indexed

    def test_ensure_hyperindex_market_id_rejects_wrong_chain_prefix(self) -> None:
        with pytest.raises(ValueError, match="does not match requested chain"):
            ensure_hyperindex_market_id(1, f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}")

    def test_split_hyperindex_market_id_returns_raw_market_id(self) -> None:
        assert split_hyperindex_market_id(f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}") == (
            ARBITRUM_CHAIN_ID,
            _MARKET_ID,
        )


class TestMorphoPreLiquidationContract:
    def test_maps_official_hyperindex_row_shape(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row())

        assert contract == MorphoPreLiquidationContract(
            chain_id=ARBITRUM_CHAIN_ID,
            market_id=_MARKET_ID,
            address=_PRE_LIQUIDATION,
            pre_lltv=810_000_000_000_000_000,
            pre_lcf1=100_000_000_000_000_000,
            pre_lcf2=WAD,
            pre_lif1=1_035_000_000_000_000_000,
            pre_lif2=1_035_000_000_000_000_000,
            pre_liquidation_oracle=_ORACLE,
        )
        assert contract.hyperindex_market_id == f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}"
        assert contract.hyperindex_contract_id == f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}-{_PRE_LIQUIDATION}"
        assert contract.params_tuple == (
            810_000_000_000_000_000,
            100_000_000_000_000_000,
            WAD,
            1_035_000_000_000_000_000,
            1_035_000_000_000_000_000,
            _ORACLE,
        )

    def test_screening_accepts_balanced_preliquidation_params(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row())

        assert contract.screening_reject_reasons(860_000_000_000_000_000) == ()

    def test_screening_rejects_pre_lltv_at_or_above_market_lltv(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row(preLltv=str(860_000_000_000_000_000)))

        assert "preLLTV must be below market LLTV" in contract.screening_reject_reasons(
            860_000_000_000_000_000,
        )

    def test_screening_rejects_invalid_close_factor_and_incentive_shape(self) -> None:
        contract = pre_liquidation_contract_from_graphql(
            _row(
                preLCF1=str(WAD + 1),
                preLCF2=str(WAD + 2),
                preLIF1=str(1_040_000_000_000_000_000),
                preLIF2=str(1_030_000_000_000_000_000),
            ),
        )

        reasons = contract.screening_reject_reasons(860_000_000_000_000_000)

        assert "preLCF1 must be <= 1e18" in reasons
        assert "preLIF1 must be <= preLIF2" in reasons

    def test_screening_allows_pre_lcf2_above_one_per_source_constructor(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row(preLCF2=str(2 * WAD)))

        assert contract.screening_reject_reasons(860_000_000_000_000_000) == ()

    def test_screening_allows_zero_pre_liquidation_oracle_for_market_oracle_mode(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row(preLiquidationOracle=_ZERO))

        assert contract.screening_reject_reasons(860_000_000_000_000_000) == ()

    def test_rejects_malformed_bigint_fields(self) -> None:
        with pytest.raises(ValueError, match="preLltv"):
            pre_liquidation_contract_from_graphql(_row(preLltv="-1"))


class TestMorphoPreLiquidationAuthorizations:
    def test_maps_official_authorization_row_shape(self) -> None:
        authorization = pre_liquidation_authorization_from_graphql(
            {"authorizer": _BORROWER, "authorizee": _PRE_LIQUIDATION},
            chain_id=ARBITRUM_CHAIN_ID,
        )

        assert authorization == MorphoPreLiquidationAuthorization(
            chain_id=ARBITRUM_CHAIN_ID,
            authorizer=_BORROWER,
            authorizee=_PRE_LIQUIDATION,
        )
        assert authorization.matches(borrower=_BORROWER, contract=_PRE_LIQUIDATION)
        assert not authorization.matches(borrower=_OTHER_BORROWER, contract=_PRE_LIQUIDATION)

    def test_rejects_zero_authorizer_or_authorizee(self) -> None:
        with pytest.raises(ValueError, match="authorizer"):
            pre_liquidation_authorization_from_graphql(
                {"authorizer": _ZERO, "authorizee": _PRE_LIQUIDATION},
                chain_id=ARBITRUM_CHAIN_ID,
            )

        with pytest.raises(ValueError, match="authorizee"):
            pre_liquidation_authorization_from_graphql(
                {"authorizer": _BORROWER, "authorizee": _ZERO},
                chain_id=ARBITRUM_CHAIN_ID,
            )

    def test_filters_contracts_authorized_by_borrower(self) -> None:
        first = pre_liquidation_contract_from_graphql(_row(address=_PRE_LIQUIDATION))
        second = pre_liquidation_contract_from_graphql(_row(address=_PRE_LIQUIDATION_2))
        authorizations = [
            MorphoPreLiquidationAuthorization(
                chain_id=ARBITRUM_CHAIN_ID,
                authorizer=_BORROWER,
                authorizee=_PRE_LIQUIDATION,
            ),
            MorphoPreLiquidationAuthorization(
                chain_id=ARBITRUM_CHAIN_ID,
                authorizer=_OTHER_BORROWER,
                authorizee=_PRE_LIQUIDATION_2,
            ),
        ]

        assert authorized_contracts_for_borrower([first, second], authorizations, _BORROWER) == [first]


class TestMorphoPreLiquidationPositions:
    def test_maps_official_hyperindex_position_row_shape(self) -> None:
        position = pre_liquidation_position_from_graphql(_position_row())

        assert position == MorphoPreLiquidationIndexedPosition(
            chain_id=ARBITRUM_CHAIN_ID,
            market_id=_MARKET_ID,
            borrower=_BORROWER,
            indexed_supply_shares=0,
            indexed_borrow_shares=1000,
            indexed_collateral=2000,
        )
        assert position.hyperindex_market_id == f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}"

    def test_position_row_rejects_zero_user(self) -> None:
        with pytest.raises(ValueError, match="position user"):
            pre_liquidation_position_from_graphql(_position_row(user=_ZERO))

    def test_to_assets_up_matches_morpho_virtual_share_rounding(self) -> None:
        assert to_assets_up(1000, 10_000, 10_000) == 10
        assert to_assets_up(0, 10_000, 10_000) == 0


class TestMorphoPreLiquidationEligibility:
    def test_computes_source_pre_liquidation_trigger_lcf_and_lif(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row())

        eligibility = evaluate_pre_liquidation_eligibility(
            contract,
            market_lltv=860_000_000_000_000_000,
            position=MorphoPreLiquidationPositionSnapshot(
                collateral_assets=1000,
                borrowed_assets=830,
                borrow_shares=1000,
                collateral_price=ORACLE_PRICE_SCALE,
            ),
        )

        assert eligibility.eligible
        assert eligibility.reject_reasons == ()
        assert eligibility.collateral_quoted == 1000
        assert eligibility.ltv == 830_000_000_000_000_000
        assert eligibility.quotient == 400_000_000_000_000_000
        assert eligibility.pre_lcf == 460_000_000_000_000_000
        assert eligibility.pre_lif == 1_035_000_000_000_000_000
        assert eligibility.repayable_shares == 460

    def test_rejects_position_below_pre_lltv(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row())

        eligibility = evaluate_pre_liquidation_eligibility(
            contract,
            market_lltv=860_000_000_000_000_000,
            position=MorphoPreLiquidationPositionSnapshot(
                collateral_assets=1000,
                borrowed_assets=810,
                borrow_shares=1000,
                collateral_price=ORACLE_PRICE_SCALE,
            ),
        )

        assert not eligibility.eligible
        assert "position is below preLLTV" in eligibility.reject_reasons

    def test_rejects_position_already_standard_liquidatable(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row())

        eligibility = evaluate_pre_liquidation_eligibility(
            contract,
            market_lltv=860_000_000_000_000_000,
            position=MorphoPreLiquidationPositionSnapshot(
                collateral_assets=1000,
                borrowed_assets=861,
                borrow_shares=1000,
                collateral_price=ORACLE_PRICE_SCALE,
            ),
        )

        assert not eligibility.eligible
        assert "position is already standard-liquidatable" in eligibility.reject_reasons

    def test_allows_pre_lcf_above_one_for_large_pre_lcf2(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row(preLCF2=str(2 * WAD)))

        eligibility = evaluate_pre_liquidation_eligibility(
            contract,
            market_lltv=860_000_000_000_000_000,
            position=MorphoPreLiquidationPositionSnapshot(
                collateral_assets=1000,
                borrowed_assets=855,
                borrow_shares=1000,
                collateral_price=ORACLE_PRICE_SCALE,
            ),
        )

        assert eligibility.eligible
        assert eligibility.pre_lcf == 1_810_000_000_000_000_000
        assert eligibility.repayable_shares == 1810


class TestMorphoPreLiquidationCandidateSelection:
    def test_selects_best_authorized_contract_per_market_and_borrower(self) -> None:
        lower_close_factor = pre_liquidation_contract_from_graphql(_row(address=_PRE_LIQUIDATION))
        higher_close_factor = pre_liquidation_contract_from_graphql(
            _row(address=_PRE_LIQUIDATION_2, preLCF2=str(2 * WAD)),
        )
        position = MorphoPreLiquidationPositionInput(
            market_id=_MARKET_ID,
            borrower=_BORROWER,
            snapshot=MorphoPreLiquidationPositionSnapshot(
                collateral_assets=1000,
                borrowed_assets=830,
                borrow_shares=1000,
                collateral_price=ORACLE_PRICE_SCALE,
            ),
        )

        selected = select_pre_liquidation_candidates(
            [lower_close_factor, higher_close_factor],
            [
                MorphoPreLiquidationAuthorization(
                    chain_id=ARBITRUM_CHAIN_ID,
                    authorizer=_BORROWER,
                    authorizee=_PRE_LIQUIDATION,
                ),
                MorphoPreLiquidationAuthorization(
                    chain_id=ARBITRUM_CHAIN_ID,
                    authorizer=_BORROWER,
                    authorizee=_PRE_LIQUIDATION_2,
                ),
            ],
            [position],
            market_lltv_by_id={_MARKET_ID: 860_000_000_000_000_000},
        )

        assert len(selected) == 1
        assert selected[0].contract.address == _PRE_LIQUIDATION_2
        assert selected[0].eligibility.repayable_shares == 860

    def test_candidate_selection_requires_authorization_and_market_lltv(self) -> None:
        contract = pre_liquidation_contract_from_graphql(_row(address=_PRE_LIQUIDATION))
        position = MorphoPreLiquidationPositionInput(
            market_id=_MARKET_ID,
            borrower=_BORROWER,
            snapshot=MorphoPreLiquidationPositionSnapshot(
                collateral_assets=1000,
                borrowed_assets=830,
                borrow_shares=1000,
                collateral_price=ORACLE_PRICE_SCALE,
            ),
        )

        assert (
            select_pre_liquidation_candidates(
                [contract],
                [],
                [position],
                market_lltv_by_id={_MARKET_ID: 860_000_000_000_000_000},
            )
            == []
        )
        assert (
            select_pre_liquidation_candidates(
                [contract],
                [
                    MorphoPreLiquidationAuthorization(
                        chain_id=ARBITRUM_CHAIN_ID,
                        authorizer=_BORROWER,
                        authorizee=_PRE_LIQUIDATION,
                    ),
                ],
                [position],
                market_lltv_by_id={},
            )
            == []
        )


class TestMorphoPreLiquidationClient:
    async def test_list_contracts_returns_empty_without_query_for_empty_market_list(self) -> None:
        client = _FakeMorphoPreLiquidationClient([])

        assert await client.list_contracts([]) == []
        assert client.queries == []

    async def test_list_contracts_queries_official_schema_and_maps_rows(self) -> None:
        client = _FakeMorphoPreLiquidationClient(
            [{"PreLiquidationContract": [_row(address=_PRE_LIQUIDATION)]}],
        )

        contracts = await client.list_contracts([_MARKET_ID])

        assert [c.address for c in contracts] == [_PRE_LIQUIDATION]
        assert "PreLiquidationContract(where: { market_id: { _in: $marketIds } })" in client.queries[0][0]
        assert client.queries[0][1] == {"marketIds": [f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}"]}

    async def test_list_contracts_accepts_already_indexed_market_ids(self) -> None:
        client = _FakeMorphoPreLiquidationClient([{"PreLiquidationContract": []}])

        await client.list_contracts([f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}"])

        assert client.queries[0][1] == {"marketIds": [f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}"]}

    async def test_list_contracts_rejects_non_list_response(self) -> None:
        client = _FakeMorphoPreLiquidationClient([{"PreLiquidationContract": {"bad": "shape"}}])

        with pytest.raises(ValueError, match="must be a list"):
            await client.list_contracts([_MARKET_ID])

    async def test_list_authorizations_returns_empty_without_query_for_empty_authorizees(self) -> None:
        client = _FakeMorphoPreLiquidationClient([])

        assert await client.list_authorizations([]) == []
        assert client.queries == []

    async def test_list_authorizations_queries_official_schema_and_maps_rows(self) -> None:
        client = _FakeMorphoPreLiquidationClient(
            [{"Authorization": [{"authorizer": _BORROWER, "authorizee": _PRE_LIQUIDATION}]}],
        )

        authorizations = await client.list_authorizations([_PRE_LIQUIDATION])

        assert authorizations == [
            MorphoPreLiquidationAuthorization(
                chain_id=ARBITRUM_CHAIN_ID,
                authorizer=_BORROWER,
                authorizee=_PRE_LIQUIDATION,
            ),
        ]
        assert "Authorization(" in client.queries[0][0]
        assert "isAuthorized: { _eq: true }" in client.queries[0][0]
        assert client.queries[0][1] == {
            "chainId": ARBITRUM_CHAIN_ID,
            "authorizees": [_PRE_LIQUIDATION],
        }

    async def test_list_authorizations_rejects_non_list_response(self) -> None:
        client = _FakeMorphoPreLiquidationClient([{"Authorization": {"bad": "shape"}}])

        with pytest.raises(ValueError, match="must be a list"):
            await client.list_authorizations([_PRE_LIQUIDATION])

    async def test_list_positions_queries_official_schema_and_maps_pages(self) -> None:
        client = _FakeMorphoPreLiquidationClient(
            [
                {"Position": [_position_row()]},
                {"Position": []},
            ],
        )

        positions = await client.list_positions([_MARKET_ID], page_size=1)

        assert [position.borrower for position in positions] == [_BORROWER]
        assert "Position(" in client.queries[0][0]
        assert 'borrowShares: { _gt: "0" }' in client.queries[0][0]
        assert client.queries[0][1] == {
            "marketIds": [f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}"],
            "limit": 1,
            "offset": 0,
        }
        assert client.queries[1][1] == {
            "marketIds": [f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}"],
            "limit": 1,
            "offset": 1,
        }

    async def test_list_positions_rejects_non_list_response(self) -> None:
        client = _FakeMorphoPreLiquidationClient([{"Position": {"bad": "shape"}}])

        with pytest.raises(ValueError, match="must be a list"):
            await client.list_positions([_MARKET_ID])

    async def test_list_live_candidates_joins_hyperindex_rows_with_onchain_snapshots(self) -> None:
        client = _FakeMorphoPreLiquidationClient(
            [
                {"PreLiquidationContract": [_row(address=_PRE_LIQUIDATION)]},
                {"Position": [_position_row()]},
                {"Authorization": [{"authorizer": _BORROWER, "authorizee": _PRE_LIQUIDATION}]},
            ],
            snapshots={
                (_PRE_LIQUIDATION, _BORROWER): (
                    860_000_000_000_000_000,
                    MorphoPreLiquidationPositionSnapshot(
                        collateral_assets=1000,
                        borrowed_assets=830,
                        borrow_shares=1000,
                        collateral_price=ORACLE_PRICE_SCALE,
                    ),
                ),
            },
        )

        candidates = await client.list_live_candidates([_MARKET_ID])

        assert len(candidates) == 1
        assert candidates[0].borrower == _BORROWER
        assert candidates[0].contract.address == _PRE_LIQUIDATION
        assert candidates[0].eligibility.repayable_shares == 460

    async def test_list_live_candidates_fails_closed_without_authorization(self) -> None:
        client = _FakeMorphoPreLiquidationClient(
            [
                {"PreLiquidationContract": [_row(address=_PRE_LIQUIDATION)]},
                {"Position": [_position_row()]},
                {"Authorization": []},
            ],
        )

        assert await client.list_live_candidates([_MARKET_ID]) == []


class _FakeMorphoPreLiquidationClient(MorphoPreLiquidationClient):
    def __init__(
        self,
        responses: list[dict[str, object]],
        *,
        snapshots: dict[
            tuple[str, str],
            tuple[int, MorphoPreLiquidationPositionSnapshot],
        ]
        | None = None,
    ) -> None:
        self.responses = responses
        self.queries: list[tuple[str, dict[str, object]]] = []
        self.snapshots = snapshots or {}
        super().__init__(_HYPERINDEX)

    async def _query(self, query: str, variables: dict[str, object]) -> dict[str, object]:
        self.queries.append((query, variables))
        if not self.responses:
            raise AssertionError("unexpected GraphQL query")
        return self.responses.pop(0)

    def read_onchain_position_snapshot(
        self,
        contract: MorphoPreLiquidationContract,
        borrower: str,
    ) -> tuple[int, MorphoPreLiquidationPositionSnapshot]:
        key = (contract.address, borrower)
        if key not in self.snapshots:
            raise AssertionError(f"unexpected on-chain read for {key}")
        return self.snapshots[key]


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "market_id": f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}",
        "address": _PRE_LIQUIDATION,
        "preLltv": "810000000000000000",
        "preLCF1": "100000000000000000",
        "preLCF2": "1000000000000000000",
        "preLIF1": "1035000000000000000",
        "preLIF2": "1035000000000000000",
        "preLiquidationOracle": _ORACLE,
    }
    row.update(overrides)
    return row


def _position_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "market_id": f"{ARBITRUM_CHAIN_ID}-{_MARKET_ID}",
        "user": _BORROWER,
        "supplyShares": "0",
        "borrowShares": "1000",
        "collateral": "2000",
    }
    row.update(overrides)
    return row
