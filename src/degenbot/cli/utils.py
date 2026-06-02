import os
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import HttpUrl, WebsocketUrl
from web3 import HTTPProvider, IPCProvider, JSONBaseProvider, LegacyWebSocketProvider, Web3

from degenbot.config import CONFIG_FILE, settings
from degenbot.connection.connection_manager import _fast_decode_rpc_response
from degenbot.exceptions import DegenbotValueError
from degenbot.provider import AlloyProvider
from degenbot.provider.alchemy import (
    AlchemyService,
    alchemy_endpoint_url,
    normalize_alchemy_service,
)
from degenbot.provider.interface import ProviderAdapter

RpcEndpoint = HttpUrl | WebsocketUrl | Path | str


def _get_use_alloy_from_env() -> bool:
    env_value = os.getenv("DEGENBOT_USE_ALLOY_PROVIDER", "").lower()
    return env_value in {"true", "1", "yes", "on"}


def get_rpc_endpoint_from_config(
    *,
    chain_id: int,
    service: AlchemyService | str = AlchemyService.HTTP_RPC,
) -> RpcEndpoint:
    """Resolve a configured RPC-style endpoint for a chain, falling back to Alchemy."""
    service = normalize_alchemy_service(service)
    if endpoint := settings.rpc.get(chain_id):
        endpoint_text = str(endpoint)
        if service is AlchemyService.HTTP_RPC:
            return endpoint
        if service is AlchemyService.WEBSOCKET and endpoint_text.startswith(("ws://", "wss://")):
            return endpoint
        if service is AlchemyService.WEBSOCKET:
            return _alchemy_endpoint_from_env(chain_id=chain_id, service=service)
        if service in {AlchemyService.BUNDLER, AlchemyService.GAS_MANAGER}:
            return _alchemy_endpoint_from_env(chain_id=chain_id, service=service)
        return endpoint
    return _alchemy_endpoint_from_env(chain_id=chain_id, service=service)


def _alchemy_endpoint_from_env(*, chain_id: int, service: AlchemyService) -> str:
    try:
        return alchemy_endpoint_url(chain_id, service=service)
    except DegenbotValueError as exc:
        msg = (
            f"Chain ID {chain_id} does not have an RPC defined in config file {CONFIG_FILE}. "
            "Set [rpc] for the chain or export ALCHEMY_API_KEY / WEB3_ALCHEMY_API_KEY. "
            f"Alchemy fallback failed: {exc}"
        )
        raise ValueError(msg) from exc


def get_web3_from_config(
    *, chain_id: int, optimize: bool = True, use_alloy: bool | None = None
) -> ProviderAdapter:
    """Get a ProviderAdapter for the given chain ID.

    Args:
        chain_id: The chain ID to get a provider for
        optimize: Whether to optimize Web3 (removes middleware, uses fast JSON decoding)
        use_alloy: Force use of AlloyProvider (default: from env var DEGENBOT_USE_ALLOY_PROVIDER)

    Returns:
        A ProviderAdapter wrapping either Web3 or AlloyProvider
    """
    if use_alloy is None:
        use_alloy = _get_use_alloy_from_env()
    endpoint = get_rpc_endpoint_from_config(chain_id=chain_id)
    endpoint_text = str(endpoint)
    if isinstance(endpoint, Path):
        if use_alloy:
            alloy = AlloyProvider(endpoint_text)
            return ProviderAdapter.from_alloy(alloy)
        w3 = Web3(IPCProvider(endpoint_text))
    elif endpoint_text.startswith(("http://", "https://")):
        if use_alloy:
            alloy = AlloyProvider(endpoint_text)
            return ProviderAdapter.from_alloy(alloy)
        w3 = Web3(HTTPProvider(endpoint_text))
    elif endpoint_text.startswith(("ws://", "wss://")):
        if use_alloy:
            alloy = AlloyProvider(endpoint_text)
            return ProviderAdapter.from_alloy(alloy)
        w3 = Web3(LegacyWebSocketProvider(endpoint_text))
    else:
        msg = f"Unsupported RPC endpoint for chain ID {chain_id}: {endpoint_text}"
        raise ValueError(msg)

    if w3.eth.chain_id != chain_id:
        msg = (
            f"The chain ID ({w3.eth.chain_id}) at endpoint {endpoint} does not match "
            f"the chain ID ({chain_id}) defined in the config file."
        )
        raise ValueError(msg)

    if optimize:
        # Remove all middleware and monkey-patch the JSON decoding for RPC responses
        w3.middleware_onion.clear()
        if TYPE_CHECKING:
            assert isinstance(w3.provider, JSONBaseProvider)
        w3.provider.decode_rpc_response = _fast_decode_rpc_response  # type:ignore[method-assign]

    return ProviderAdapter.from_web3(w3)
