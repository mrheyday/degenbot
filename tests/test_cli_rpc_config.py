from pathlib import Path

import pytest

from degenbot.cli import utils
from degenbot.provider.alchemy import AlchemyService


def test_get_rpc_endpoint_from_config_falls_back_to_alchemy(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(utils.settings, "rpc", {})
    monkeypatch.setenv("ALCHEMY_API_KEY", "test-key")

    endpoint = utils.get_rpc_endpoint_from_config(chain_id=8453)

    assert endpoint == "https://base-mainnet.g.alchemy.com/v2/test-key"


def test_get_rpc_endpoint_from_config_falls_back_to_alchemy_websocket(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(utils.settings, "rpc", {})
    monkeypatch.setenv("ALCHEMY_API_KEY", "test-key")

    endpoint = utils.get_rpc_endpoint_from_config(
        chain_id=8453,
        service=AlchemyService.WEBSOCKET,
    )

    assert endpoint == "wss://base-mainnet.g.alchemy.com/v2/test-key"


def test_get_rpc_endpoint_from_config_uses_configured_websocket_for_websocket_service(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(utils.settings, "rpc", {8453: "wss://configured.example"})
    monkeypatch.setenv("ALCHEMY_API_KEY", "test-key")

    endpoint = utils.get_rpc_endpoint_from_config(
        chain_id=8453,
        service="websocket",
    )

    assert endpoint == "wss://configured.example"


def test_get_rpc_endpoint_from_config_ignores_configured_ipc_for_websocket_service(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(utils.settings, "rpc", {8453: Path("/tmp/base.ipc")})
    monkeypatch.setenv("ALCHEMY_API_KEY", "test-key")

    endpoint = utils.get_rpc_endpoint_from_config(
        chain_id=8453,
        service=AlchemyService.WEBSOCKET,
    )

    assert endpoint == "wss://base-mainnet.g.alchemy.com/v2/test-key"


def test_get_rpc_endpoint_from_config_falls_back_to_alchemy_bundler(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(utils.settings, "rpc", {})
    monkeypatch.setenv("ALCHEMY_API_KEY", "test-key")

    endpoint = utils.get_rpc_endpoint_from_config(
        chain_id=42161,
        service=AlchemyService.BUNDLER,
    )

    assert endpoint == "https://arb-mainnet.g.alchemy.com/v2/test-key"


def test_get_rpc_endpoint_from_config_rejects_unsupported_alchemy_bundler_chain(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(utils.settings, "rpc", {})
    monkeypatch.setenv("ALCHEMY_API_KEY", "test-key")

    with pytest.raises(ValueError, match="Account Abstraction"):
        utils.get_rpc_endpoint_from_config(chain_id=1101, service=AlchemyService.BUNDLER)
