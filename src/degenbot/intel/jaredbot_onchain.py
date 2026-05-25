"""Read-only verifier for public JaredFromSubway address claims.

The imported `jaredbot-onchain-intel` skill intentionally treats the site
claims as unverified until independently checked. This module is that first
gate: it probes only `eth_getCode` for the public addresses harvested from the
Jaredbot corpus and classifies each as contract, empty account, or RPC error.

No transaction submission, signing, calldata execution, archive tracing, or
disallowed site API interaction is performed here.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Final, Literal, cast

import httpx
from web3 import Web3

if TYPE_CHECKING:
    from collections.abc import Sequence

JAREDBOT_CHAIN_ID: Final[int] = 1
JAREDBOT_SOURCE_NOTE: Final[str] = "docs/research/jaredbot-mev-site-probe-2026-05-07.md"

_ADDRESS_RE: Final[re.Pattern[str]] = re.compile(r"^0x[a-fA-F0-9]{40}$")

ProbeStatus = Literal["contract", "empty", "error"]
JsonObject = dict[str, Any]


@dataclass(frozen=True)
class JaredbotAddressClaim:
    """One public address claim from the Jaredbot source map."""

    label: str
    address: str
    claimed_role: str
    source: str = JAREDBOT_SOURCE_NOTE
    expected_contract: bool = True

    @property
    def normalized_address(self) -> str:
        return normalize_address(self.address)


@dataclass(frozen=True)
class CodeProbe:
    """Result of one `eth_getCode` address probe."""

    label: str
    address: str
    claimed_role: str
    expected_contract: bool
    block_tag: str
    status: ProbeStatus
    code_size_bytes: int
    code_hash_keccak256: str | None
    error: str | None = None

    @property
    def matches_expectation(self) -> bool:
        if self.status == "error":
            return False
        if self.expected_contract:
            return self.status == "contract"
        return True


JAREDBOT_ADDRESS_CLAIMS: Final[tuple[JaredbotAddressClaim, ...]] = (
    JaredbotAddressClaim(
        label="claimed_bot_contract",
        address="0x1f2F10D1C40777AE1Da742455c65828FF36Df387",
        claimed_role="Jaredbot site-claimed bot contract",
    ),
    JaredbotAddressClaim(
        label="claimed_executor",
        address="0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13",
        claimed_role="Jaredbot site-claimed executor",
    ),
    JaredbotAddressClaim(
        label="public_etherscan_link_1",
        address="0x0B3dA2ae835d25127AD31Ee9115b6BC84f7F3c83",
        claimed_role="Additional Etherscan-linked address observed on public pages",
    ),
    JaredbotAddressClaim(
        label="public_etherscan_link_2",
        address="0xa8bbbbdb3e53d24fa9741601018a9804095c4517",
        claimed_role="Additional Etherscan-linked address observed on public pages",
    ),
)


def normalize_address(address: str) -> str:
    """Normalize a hex Ethereum address for comparisons and RPC calls."""

    if not _ADDRESS_RE.fullmatch(address):
        raise ValueError(f"invalid ethereum address: {address}")
    return "0x" + address[2:].lower()


def build_eth_get_code_payloads(
    claims: Sequence[JaredbotAddressClaim] = JAREDBOT_ADDRESS_CLAIMS,
    *,
    block_tag: str = "latest",
) -> list[JsonObject]:
    """Build a JSON-RPC batch payload for `eth_getCode`."""

    return [
        {
            "jsonrpc": "2.0",
            "id": index,
            "method": "eth_getCode",
            "params": [claim.normalized_address, block_tag],
        }
        for index, claim in enumerate(claims, start=1)
    ]


def parse_eth_get_code_response(
    claim: JaredbotAddressClaim,
    response: JsonObject,
    *,
    block_tag: str = "latest",
) -> CodeProbe:
    """Parse one JSON-RPC `eth_getCode` response into a stable probe result."""

    if "error" in response:
        error = response["error"]
        return _error_probe(claim, block_tag, f"rpc error: {_stringify_error(error)}")

    result = response.get("result")
    if not isinstance(result, str):
        return _error_probe(claim, block_tag, "missing or non-string result")

    if not result.startswith("0x") or len(result) % 2 != 0:
        return _error_probe(claim, block_tag, "invalid hex code result")

    if result == "0x":
        return CodeProbe(
            label=claim.label,
            address=claim.normalized_address,
            claimed_role=claim.claimed_role,
            expected_contract=claim.expected_contract,
            block_tag=block_tag,
            status="empty",
            code_size_bytes=0,
            code_hash_keccak256=None,
        )

    code_size = (len(result) - 2) // 2
    return CodeProbe(
        label=claim.label,
        address=claim.normalized_address,
        claimed_role=claim.claimed_role,
        expected_contract=claim.expected_contract,
        block_tag=block_tag,
        status="contract",
        code_size_bytes=code_size,
        code_hash_keccak256=_keccak_hex(result),
    )


def fetch_chain_id(rpc_url: str, *, timeout_sec: float = 10.0) -> int:
    """Read `eth_chainId` from a JSON-RPC endpoint."""

    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}
    with httpx.Client(timeout=timeout_sec) as client:
        response = client.post(rpc_url, json=payload)
        response.raise_for_status()
        body = response.json()

    if not isinstance(body, dict):
        raise ValueError("expected JSON-RPC chain id response object")
    return parse_chain_id_response(cast("JsonObject", body))


def parse_chain_id_response(response: JsonObject) -> int:
    """Parse one JSON-RPC `eth_chainId` response."""

    if "error" in response:
        raise ValueError(f"rpc error: {_stringify_error(response['error'])}")
    result = response.get("result")
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("missing or invalid chain id result")
    return int(result, 16)


def fetch_code_probes(
    rpc_url: str,
    *,
    claims: Sequence[JaredbotAddressClaim] = JAREDBOT_ADDRESS_CLAIMS,
    block_tag: str = "latest",
    timeout_sec: float = 10.0,
) -> tuple[int, list[CodeProbe]]:
    """Fetch code probes from an Ethereum JSON-RPC endpoint.

    The RPC URL is deliberately not included in returned report data to avoid
    leaking provider credentials into logs or artifacts.
    """

    chain_id = fetch_chain_id(rpc_url, timeout_sec=timeout_sec)
    if chain_id != JAREDBOT_CHAIN_ID:
        raise ValueError(
            f"chain id mismatch: Jaredbot claims are for chain {JAREDBOT_CHAIN_ID}, but RPC returned {chain_id}",
        )

    payload = build_eth_get_code_payloads(claims, block_tag=block_tag)
    with httpx.Client(timeout=timeout_sec) as client:
        response = client.post(rpc_url, json=payload)
        response.raise_for_status()
        body = response.json()

    if not isinstance(body, list):
        raise ValueError("expected JSON-RPC batch response list")

    by_id: dict[int, JsonObject] = {}
    for item in body:
        if not isinstance(item, dict):
            raise ValueError("expected JSON-RPC response objects")
        response_id = item.get("id")
        if not isinstance(response_id, int):
            raise ValueError("expected integer JSON-RPC response id")
        by_id[response_id] = cast("JsonObject", item)

    probes: list[CodeProbe] = []
    for index, claim in enumerate(claims, start=1):
        item = by_id.get(index)
        if item is None:
            probes.append(_error_probe(claim, block_tag, "missing batch response"))
        else:
            probes.append(parse_eth_get_code_response(claim, item, block_tag=block_tag))
    return chain_id, probes


def report_to_dict(probes: Sequence[CodeProbe], *, chain_id: int = JAREDBOT_CHAIN_ID) -> JsonObject:
    """Serialize probes into a deterministic JSON-friendly report."""

    failures = [probe for probe in probes if not probe.matches_expectation]
    return {
        "source": JAREDBOT_SOURCE_NOTE,
        "chainId": chain_id,
        "summary": {
            "total": len(probes),
            "contracts": sum(1 for probe in probes if probe.status == "contract"),
            "empty": sum(1 for probe in probes if probe.status == "empty"),
            "errors": sum(1 for probe in probes if probe.status == "error"),
            "expectationFailures": len(failures),
        },
        "probes": [asdict(probe) for probe in probes],
    }


def run(argv: Sequence[str] | None = None) -> None:
    """Console entry point."""

    parser = argparse.ArgumentParser(
        description="Read-only eth_getCode verifier for public Jaredbot address claims",
    )
    parser.add_argument(
        "--rpc-url",
        default=os.getenv("ETH_RPC_HTTP"),
        help="Ethereum mainnet JSON-RPC URL; defaults to ETH_RPC_HTTP",
    )
    parser.add_argument("--block-tag", default="latest", help="JSON-RPC block tag or hex block number")
    parser.add_argument("--timeout-sec", type=float, default=10.0)
    args = parser.parse_args(argv)

    rpc_url = args.rpc_url
    if not rpc_url:
        parser.error("--rpc-url or ETH_RPC_HTTP is required")

    chain_id, probes = fetch_code_probes(
        rpc_url=rpc_url,
        block_tag=args.block_tag,
        timeout_sec=args.timeout_sec,
    )
    print(json.dumps(report_to_dict(probes, chain_id=chain_id), indent=2, sort_keys=True))


def _error_probe(claim: JaredbotAddressClaim, block_tag: str, error: str) -> CodeProbe:
    return CodeProbe(
        label=claim.label,
        address=claim.normalized_address,
        claimed_role=claim.claimed_role,
        expected_contract=claim.expected_contract,
        block_tag=block_tag,
        status="error",
        code_size_bytes=0,
        code_hash_keccak256=None,
        error=error,
    )


def _stringify_error(error: object) -> str:
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    return str(error)


def _keccak_hex(hex_code: str) -> str:
    code_hash = Web3.keccak(hexstr=hex_code).hex()
    if code_hash.startswith("0x"):
        return code_hash
    return f"0x{code_hash}"


if __name__ == "__main__":
    run()
