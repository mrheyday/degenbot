from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from urllib.parse import quote

from degenbot.exceptions import DegenbotValueError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from degenbot.types.aliases import ChainId

_ALCHEMY_NETWORK_IDENTIFIER_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ALCHEMY_API_KEY_ENV_VARS = ("ALCHEMY_API_KEY", "WEB3_ALCHEMY_API_KEY")
_TRUE_ENV_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_ENV_VALUES = frozenset({"0", "false", "no", "off"})


class AlchemyService(StrEnum):
    """Alchemy service surfaces backed by chain-specific `/v2/{apiKey}` endpoints."""

    HTTP_RPC = "http_rpc"
    WEBSOCKET = "websocket"
    BUNDLER = "bundler"
    GAS_MANAGER = "gas_manager"


@dataclass(frozen=True, slots=True)
class AlchemyEndpointBundle:
    """Resolved Alchemy endpoints for one EVM chain."""

    chain_id: ChainId
    network_identifier: str
    rpc_http: str
    rpc_ws: str
    bundler: str | None
    gas_manager: str | None
    account_abstraction_supported: bool


ALCHEMY_NETWORK_IDENTIFIERS: Mapping[ChainId, str] = {
    1: "eth-mainnet",
    10: "opt-mainnet",
    30: "rootstock-mainnet",
    31: "rootstock-testnet",
    56: "bnb-mainnet",
    97: "bnb-testnet",
    100: "gnosis-mainnet",
    130: "unichain-mainnet",
    143: "monad-mainnet",
    196: "xlayer-mainnet",
    204: "opbnb-mainnet",
    137: "polygon-mainnet",
    250: "fantom-mainnet",
    252: "frax-mainnet",
    288: "boba-mainnet",
    300: "zksync-sepolia",
    324: "zksync-mainnet",
    360: "shape-mainnet",
    480: "worldchain-mainnet",
    592: "astar-mainnet",
    869: "worldmobilechain-mainnet",
    919: "mode-sepolia",
    988: "stable-mainnet",
    998: "hyperliquid-testnet",
    999: "hyperliquid-mainnet",
    1101: "polygonzkevm-mainnet",
    1301: "unichain-sepolia",
    1315: "story-aeneid",
    1514: "story-mainnet",
    1868: "soneium-mainnet",
    1946: "soneium-minato",
    1952: "xlayer-testnet",
    2201: "stable-testnet",
    2442: "polygonzkevm-cardona",
    2522: "frax-hoodi",
    2741: "abstract-mainnet",
    4153: "rise-mainnet",
    4326: "megaeth-mainnet",
    4663: "robinhood-mainnet",
    4801: "worldchain-sepolia",
    5000: "mantle-mainnet",
    5003: "mantle-sepolia",
    5611: "opbnb-testnet",
    6343: "megaeth-testnet",
    6805: "race-mainnet",
    6806: "race-sepolia",
    6900: "anime-sepolia",
    7000: "zetachain-mainnet",
    7001: "zetachain-testnet",
    8008: "polynomial-mainnet",
    8009: "polynomial-sepolia",
    8453: "base-mainnet",
    9745: "plasma-mainnet",
    9746: "plasma-testnet",
    10143: "monad-testnet",
    10200: "gnosis-chiado",
    10218: "tea-sepolia",
    11011: "shape-sepolia",
    17000: "eth-holesky",
    33111: "apechain-curtis",
    33139: "apechain-mainnet",
    34443: "mode-mainnet",
    42018: "mythos-mainnet",
    42161: "arb-mainnet",
    42170: "arbnova-mainnet",
    42220: "celo-mainnet",
    43113: "avax-fuji",
    43114: "avax-mainnet",
    46630: "robinhood-testnet",
    57073: "ink-mainnet",
    59144: "linea-mainnet",
    59141: "linea-sepolia",
    69000: "anime-mainnet",
    80069: "berachain-bepolia",
    80094: "berachain-mainnet",
    763373: "ink-sepolia",
    80002: "polygon-amoy",
    81457: "blast-mainnet",
    84532: "base-sepolia",
    28882: "boba-sepolia",
    421614: "arb-sepolia",
    510525: "clankermon-mainnet",
    534351: "scroll-sepolia",
    534352: "scroll-mainnet",
    560048: "eth-hoodi",
    685685: "gensyn-testnet",
    685689: "gensyn-mainnet",
    737373: "katana-bokuto",
    747474: "katana-mainnet",
    905905: "openloot-sepolia",
    5042002: "arc-testnet",
    7777777: "zora-mainnet",
    11155111: "eth-sepolia",
    11155420: "opt-sepolia",
    11142220: "celo-sepolia",
    11155931: "rise-testnet",
    168587773: "blast-sepolia",
    666666666: "degen-mainnet",
    999999999: "zora-sepolia",
}

ALCHEMY_ACCOUNT_ABSTRACTION_CHAIN_IDS: frozenset[ChainId] = frozenset({
    1,
    10,
    56,
    97,
    130,
    137,
    143,
    196,
    204,
    252,
    360,
    480,
    869,
    988,
    998,
    999,
    1301,
    1315,
    1514,
    1868,
    1946,
    1952,
    2201,
    4153,
    4326,
    4663,
    4801,
    5611,
    6343,
    6900,
    8453,
    9745,
    9746,
    10143,
    11011,
    33111,
    33139,
    42018,
    42161,
    42220,
    46630,
    57073,
    69000,
    80002,
    80069,
    80094,
    84532,
    421614,
    510525,
    560048,
    685685,
    685689,
    737373,
    747474,
    763373,
    5042002,
    7777777,
    11155111,
    11155420,
    11142220,
    11155931,
    999999999,
})


def resolve_alchemy_api_key(
    *,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve the operator's Alchemy API key from supported environment variables."""
    environ = os.environ if environ is None else environ
    for env_var in _ALCHEMY_API_KEY_ENV_VARS:
        if api_key := environ.get(env_var, "").strip():
            return api_key
    return None


def alchemy_network_identifier(
    chain_id: int,
    *,
    network_identifier: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve the Alchemy network identifier for an EVM chain ID."""
    chain_id_value = int(chain_id)
    environ = os.environ if environ is None else environ
    resolved_identifier = (
        network_identifier
        or environ.get(f"ALCHEMY_CHAIN_{chain_id_value}_NETWORK", "").strip()
        or environ.get(f"ALCHEMY_NETWORK_{chain_id_value}", "").strip()
        or ALCHEMY_NETWORK_IDENTIFIERS.get(chain_id_value)
    )
    if not resolved_identifier:
        msg = (
            f"Chain ID {chain_id_value} is not in the built-in Alchemy registry. "
            f"Set ALCHEMY_CHAIN_{chain_id_value}_NETWORK to the Alchemy network identifier."
        )
        raise DegenbotValueError(msg)
    if not _ALCHEMY_NETWORK_IDENTIFIER_RE.fullmatch(resolved_identifier):
        msg = f"Invalid Alchemy network identifier: {resolved_identifier!r}"
        raise DegenbotValueError(msg)
    return resolved_identifier


def alchemy_account_abstraction_supported(
    chain_id: int,
    *,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether Alchemy's current SDK registry lists AA support for a chain."""
    chain_id_value = int(chain_id)
    environ = os.environ if environ is None else environ
    for env_var in (
        f"ALCHEMY_CHAIN_{chain_id_value}_ACCOUNT_ABSTRACTION",
        f"ALCHEMY_CHAIN_{chain_id_value}_AA",
        f"ALCHEMY_ACCOUNT_ABSTRACTION_{chain_id_value}",
    ):
        env_value = environ.get(env_var, "").strip().lower()
        if env_value in _TRUE_ENV_VALUES:
            return True
        if env_value in _FALSE_ENV_VALUES:
            return False
        if env_value:
            msg = f"Invalid boolean value for {env_var}: {env_value!r}"
            raise DegenbotValueError(msg)
    return chain_id_value in ALCHEMY_ACCOUNT_ABSTRACTION_CHAIN_IDS


def alchemy_endpoint_url(
    chain_id: int,
    *,
    service: AlchemyService | str = AlchemyService.HTTP_RPC,
    api_key: str | None = None,
    network_identifier: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Build an Alchemy endpoint URL for one service and chain."""
    service = normalize_alchemy_service(service)
    api_key = (api_key or resolve_alchemy_api_key(environ=environ) or "").strip()
    if not api_key:
        msg = "Alchemy endpoint construction requires ALCHEMY_API_KEY or WEB3_ALCHEMY_API_KEY."
        raise DegenbotValueError(msg)

    identifier = alchemy_network_identifier(
        chain_id,
        network_identifier=network_identifier,
        environ=environ,
    )
    aa_supported = alchemy_account_abstraction_supported(chain_id, environ=environ)
    if service in {AlchemyService.BUNDLER, AlchemyService.GAS_MANAGER} and not aa_supported:
        msg = (
            f"Account Abstraction service {service.value!r} is not supported for chain ID "
            f"{int(chain_id)} in the built-in Alchemy registry. Set "
            f"ALCHEMY_CHAIN_{int(chain_id)}_ACCOUNT_ABSTRACTION=true only after confirming "
            "Alchemy supports it."
        )
        raise DegenbotValueError(msg)
    scheme = "wss" if service is AlchemyService.WEBSOCKET else "https"
    return f"{scheme}://{identifier}.g.alchemy.com/v2/{quote(api_key, safe='')}"


def alchemy_endpoint_bundle(
    chain_id: int,
    *,
    api_key: str | None = None,
    network_identifier: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> AlchemyEndpointBundle:
    """Build HTTP RPC, WebSocket, Bundler, and Gas Manager endpoints for one chain."""
    identifier = alchemy_network_identifier(
        chain_id,
        network_identifier=network_identifier,
        environ=environ,
    )
    rpc_http = alchemy_endpoint_url(
        chain_id,
        service=AlchemyService.HTTP_RPC,
        api_key=api_key,
        network_identifier=identifier,
        environ=environ,
    )
    rpc_ws = alchemy_endpoint_url(
        chain_id,
        service=AlchemyService.WEBSOCKET,
        api_key=api_key,
        network_identifier=identifier,
        environ=environ,
    )
    aa_supported = alchemy_account_abstraction_supported(
        chain_id,
        environ=environ,
    )
    aa_endpoint = rpc_http if aa_supported else None
    return AlchemyEndpointBundle(
        chain_id=int(chain_id),
        network_identifier=identifier,
        rpc_http=rpc_http,
        rpc_ws=rpc_ws,
        bundler=aa_endpoint,
        gas_manager=aa_endpoint,
        account_abstraction_supported=aa_supported,
    )


def normalize_alchemy_service(service: AlchemyService | str) -> AlchemyService:
    """Normalize an Alchemy service label."""
    if isinstance(service, AlchemyService):
        return service
    match service.strip().lower().replace("-", "_"):
        case "http" | "https" | "rpc" | "http_rpc" | "rpc_http":
            return AlchemyService.HTTP_RPC
        case "ws" | "wss" | "websocket":
            return AlchemyService.WEBSOCKET
        case "bundler" | "account_abstraction":
            return AlchemyService.BUNDLER
        case "gas" | "gas_manager" | "paymaster":
            return AlchemyService.GAS_MANAGER
        case _:
            msg = f"Unsupported Alchemy service: {service!r}"
            raise DegenbotValueError(msg)
