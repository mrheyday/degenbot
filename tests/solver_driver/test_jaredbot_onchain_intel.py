"""Unit tests for the Jaredbot on-chain intel verifier.

These are pure tests: no network, no explorer calls, no transaction signing.
"""

from __future__ import annotations

import pytest

from degenbot.intel.jaredbot_onchain import (
    JAREDBOT_ADDRESS_CLAIMS,
    build_eth_get_code_payloads,
    normalize_address,
    parse_chain_id_response,
    parse_eth_get_code_response,
    report_to_dict,
)


class TestAddressClaims:
    def test_all_claims_normalize_to_lowercase_addresses(self) -> None:
        for claim in JAREDBOT_ADDRESS_CLAIMS:
            assert claim.normalized_address == claim.address.lower()
            assert claim.normalized_address.startswith("0x")
            assert len(claim.normalized_address) == 42

    def test_invalid_address_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid ethereum address"):
            normalize_address("0x1234")


class TestPayloadBuilder:
    def test_builds_stable_eth_get_code_batch(self) -> None:
        payloads = build_eth_get_code_payloads(block_tag="0x123")

        assert len(payloads) == len(JAREDBOT_ADDRESS_CLAIMS)
        assert payloads[0] == {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getCode",
            "params": [
                "0x1f2f10d1c40777ae1da742455c65828ff36df387",
                "0x123",
            ],
        }
        assert [payload["id"] for payload in payloads] == [1, 2, 3, 4]


class TestChainIdParsing:
    def test_parses_ethereum_mainnet_chain_id(self) -> None:
        assert parse_chain_id_response({"jsonrpc": "2.0", "id": 1, "result": "0x1"}) == 1

    def test_parses_arbitrum_chain_id(self) -> None:
        assert parse_chain_id_response({"jsonrpc": "2.0", "id": 1, "result": "0xa4b1"}) == 42_161

    def test_rejects_invalid_chain_id_shape(self) -> None:
        with pytest.raises(ValueError, match="missing or invalid chain id result"):
            parse_chain_id_response({"jsonrpc": "2.0", "id": 1, "result": 42161})


class TestResponseParsing:
    def test_empty_code_classifies_as_empty_account(self) -> None:
        probe = parse_eth_get_code_response(
            JAREDBOT_ADDRESS_CLAIMS[0],
            {"jsonrpc": "2.0", "id": 1, "result": "0x"},
            block_tag="0x123",
        )

        assert probe.status == "empty"
        assert probe.code_size_bytes == 0
        assert probe.code_hash_keccak256 is None
        assert not probe.matches_expectation

    def test_contract_code_classifies_as_contract_and_hashes_code(self) -> None:
        probe = parse_eth_get_code_response(
            JAREDBOT_ADDRESS_CLAIMS[0],
            {"jsonrpc": "2.0", "id": 1, "result": "0x6001600055"},
            block_tag="latest",
        )

        assert probe.status == "contract"
        assert probe.code_size_bytes == 5
        assert probe.code_hash_keccak256 is not None
        assert probe.code_hash_keccak256.startswith("0x")
        assert probe.matches_expectation

    def test_rpc_error_classifies_as_error(self) -> None:
        probe = parse_eth_get_code_response(
            JAREDBOT_ADDRESS_CLAIMS[0],
            {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "bad block"}},
        )

        assert probe.status == "error"
        assert probe.error == "rpc error: bad block"
        assert not probe.matches_expectation

    def test_invalid_result_shape_classifies_as_error(self) -> None:
        probe = parse_eth_get_code_response(
            JAREDBOT_ADDRESS_CLAIMS[0],
            {"jsonrpc": "2.0", "id": 1, "result": 123},
        )

        assert probe.status == "error"
        assert probe.error == "missing or non-string result"


class TestReport:
    def test_report_summarizes_failures_without_rpc_url(self) -> None:
        probes = [
            parse_eth_get_code_response(
                JAREDBOT_ADDRESS_CLAIMS[0],
                {"jsonrpc": "2.0", "id": 1, "result": "0x6001"},
            ),
            parse_eth_get_code_response(
                JAREDBOT_ADDRESS_CLAIMS[1],
                {"jsonrpc": "2.0", "id": 2, "result": "0x"},
            ),
        ]

        report = report_to_dict(probes)

        assert report["summary"] == {
            "total": 2,
            "contracts": 1,
            "empty": 1,
            "errors": 0,
            "expectationFailures": 1,
        }
        assert "rpc" not in report
