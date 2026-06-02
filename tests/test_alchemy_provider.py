import importlib.util
from pathlib import Path

import pytest

from degenbot.exceptions import DegenbotValueError
from degenbot.provider.alchemy import (
    AlchemyService,
    alchemy_account_abstraction_supported,
    alchemy_endpoint_bundle,
    alchemy_endpoint_url,
    alchemy_network_identifier,
    resolve_alchemy_api_key,
)


def _load_aave_debug_helper():
    helper_path = Path(__file__).resolve().parents[1] / "scripts" / "aave_debug_helper.py"
    spec = importlib.util.spec_from_file_location("aave_debug_helper", helper_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_alchemy_endpoint_bundle_uses_one_key_for_rpc_wss_and_bundler():
    endpoints = alchemy_endpoint_bundle(42161, api_key="test-key")

    assert endpoints.network_identifier == "arb-mainnet"
    assert endpoints.account_abstraction_supported is True
    assert endpoints.rpc_http == "https://arb-mainnet.g.alchemy.com/v2/test-key"
    assert endpoints.rpc_ws == "wss://arb-mainnet.g.alchemy.com/v2/test-key"
    assert endpoints.bundler == endpoints.rpc_http
    assert endpoints.gas_manager == endpoints.rpc_http


@pytest.mark.parametrize(
    ("chain_id", "network_identifier"),
    [
        (30, "rootstock-mainnet"),
        (130, "unichain-mainnet"),
        (480, "worldchain-mainnet"),
        (919, "mode-sepolia"),
        (1101, "polygonzkevm-mainnet"),
        (1301, "unichain-sepolia"),
        (1868, "soneium-mainnet"),
        (2741, "abstract-mainnet"),
        (5000, "mantle-mainnet"),
        (81457, "blast-mainnet"),
        (168587773, "blast-sepolia"),
        (534352, "scroll-mainnet"),
    ],
)
def test_alchemy_network_identifier_covers_major_supported_evm_chains(
    chain_id,
    network_identifier,
):
    assert alchemy_network_identifier(chain_id) == network_identifier


@pytest.mark.parametrize(
    ("chain_id", "network_identifier"),
    [
        (196, "xlayer-mainnet"),
        (988, "stable-mainnet"),
        (4153, "rise-mainnet"),
        (4326, "megaeth-mainnet"),
        (4801, "worldchain-sepolia"),
        (9745, "plasma-mainnet"),
        (33139, "apechain-mainnet"),
        (80069, "berachain-bepolia"),
        (80094, "berachain-mainnet"),
        (11142220, "celo-sepolia"),
    ],
)
def test_alchemy_network_identifier_covers_account_abstraction_registry(
    chain_id,
    network_identifier,
):
    assert alchemy_network_identifier(chain_id) == network_identifier
    assert alchemy_account_abstraction_supported(chain_id) is True


def test_alchemy_account_abstraction_support_is_not_implied_by_node_rpc_support():
    assert alchemy_network_identifier(1101) == "polygonzkevm-mainnet"
    assert alchemy_account_abstraction_supported(1101) is False


def test_alchemy_endpoint_bundle_marks_node_only_chains_as_not_aa_supported():
    endpoints = alchemy_endpoint_bundle(1101, api_key="test-key")

    assert endpoints.network_identifier == "polygonzkevm-mainnet"
    assert endpoints.account_abstraction_supported is False
    assert endpoints.bundler is None
    assert endpoints.gas_manager is None


@pytest.mark.parametrize("service", [AlchemyService.BUNDLER, AlchemyService.GAS_MANAGER])
def test_alchemy_endpoint_url_rejects_account_abstraction_service_on_node_only_chain(
    service,
):
    with pytest.raises(DegenbotValueError, match="Account Abstraction"):
        alchemy_endpoint_url(1101, service=service, api_key="test-key")


@pytest.mark.parametrize("service", [AlchemyService.BUNDLER, AlchemyService.GAS_MANAGER])
def test_alchemy_endpoint_url_allows_account_abstraction_service_on_supported_chain(
    service,
):
    endpoint = alchemy_endpoint_url(42161, service=service, api_key="test-key")

    assert endpoint == "https://arb-mainnet.g.alchemy.com/v2/test-key"


def test_alchemy_account_abstraction_support_can_be_operator_enabled_for_new_chain():
    environ = {
        "ALCHEMY_CHAIN_999999_NETWORK": "custom-rollup-mainnet",
        "ALCHEMY_CHAIN_999999_ACCOUNT_ABSTRACTION": "true",
    }

    assert alchemy_account_abstraction_supported(999999, environ=environ) is True
    endpoint = alchemy_endpoint_url(
        999999,
        service=AlchemyService.BUNDLER,
        api_key="test-key",
        environ=environ,
    )

    assert endpoint == "https://custom-rollup-mainnet.g.alchemy.com/v2/test-key"


def test_alchemy_endpoint_url_supports_custom_network_identifiers_for_new_chains():
    endpoint = alchemy_endpoint_url(
        999999,
        service=AlchemyService.WEBSOCKET,
        api_key="test-key",
        network_identifier="custom-rollup-mainnet",
    )

    assert endpoint == "wss://custom-rollup-mainnet.g.alchemy.com/v2/test-key"


def test_resolve_alchemy_api_key_prefers_primary_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WEB3_ALCHEMY_API_KEY", "ape-key")
    monkeypatch.setenv("ALCHEMY_API_KEY", "primary-key")

    assert resolve_alchemy_api_key() == "primary-key"


def test_alchemy_endpoint_url_requires_key_from_argument_or_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("ALCHEMY_API_KEY", raising=False)
    monkeypatch.delenv("WEB3_ALCHEMY_API_KEY", raising=False)

    with pytest.raises(DegenbotValueError, match="ALCHEMY_API_KEY"):
        alchemy_endpoint_url(42161)


def test_aave_debug_rpc_config_falls_back_to_alchemy(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ALCHEMY_API_KEY", "test-key")

    helper = _load_aave_debug_helper()
    rpc_url = helper.get_rpc_url(42161, config_path=tmp_path / "missing-rpc-config.json")

    assert rpc_url == "https://arb-mainnet.g.alchemy.com/v2/test-key"
