"""Shared adapter templates for Python-side venue registration.

The adapter registry is metadata only. It does not grant execution permission
and it does not replace degenbot as the pool-state source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

ARBITRUM_ONE_CHAIN_ID = 42161
COORDINATOR_REGISTRY_SOURCE = "coordinator/src/router/registry.ts"
DEFILLAMA_DIMENSION_ADAPTERS_REPO = "DefiLlama/dimension-adapters"
DEFILLAMA_DIMENSION_ADAPTERS_BASE_URL = "https://github.com/DefiLlama/dimension-adapters/blob/master"
SOURCIFY_SERVER = "https://sourcify.dev/server"


class AdapterCategory(StrEnum):
    """High-level adapter domain."""

    SWAP = "swap"
    FLASH = "flash"
    LIQUIDITY = "liquidity"
    LIQUIDATION = "liquidation"
    QUOTE = "quote"
    PATHFINDER = "pathfinder"


class AdapterStatus(StrEnum):
    """Operational status for an adapter entry."""

    ENABLED = "enabled"
    READ_ONLY = "read_only"
    REFERENCE_ONLY = "reference_only"
    BLOCKED = "blocked"


class RegistryKey(StrEnum):
    """How the adapter resolves its canonical target."""

    ADDRESS = "address"
    FACTORY = "factory"
    POOL_ID = "pool_id"
    MARKET_ID = "market_id"
    ROUTER = "router"
    VAULT = "vault"
    EXTERNAL_API = "external_api"


class ExecutionLane(StrEnum):
    """Policy lane that consumes one or more adapter categories."""

    UNIVERSAL_FLASH_AGGREGATOR_ROUTER = "universal_flash_aggregator_router"
    UNIVERSAL_SWAP_AGGREGATOR_ROUTER = "universal_swap_aggregator_router"
    UNIVERSAL_PATHFINDER_QUOTER_ROUTER = "universal_pathfinder_quoter_aggregator_router"
    UNIVERSAL_LIQUIDITY_AGGREGATOR_ROUTER = "universal_liquidity_aggregator_router"
    ARB_EXECUTOR = "arb_executor"
    INTENT_EXECUTOR = "intent_executor"
    JIT_EXECUTOR = "jit_executor"
    LIQUIDATION_EXECUTOR = "liquidation_executor"
    SANDWICH_EXECUTOR = "sandwich_executor"
    MEV_PROTECTION_EXECUTOR = "mev_protection_executor"


@dataclass(frozen=True, slots=True)
class ContractBinding:
    """One canonical contract binding for an adapter."""

    export_name: str
    address: str
    role: str
    chain_id: int = ARBITRUM_ONE_CHAIN_ID
    source_file: str = COORDINATOR_REGISTRY_SOURCE

    @property
    def source_ref(self) -> str:
        """Return the TS registry export that sourced this address."""
        return f"{self.source_file}:{self.export_name}"

    @property
    def sourcify_url(self) -> str:
        """Return the Sourcify v2 status URL for this contract."""
        return f"{SOURCIFY_SERVER}/v2/contract/{self.chain_id}/{self.address}"


@dataclass(frozen=True, slots=True)
class DefiLlamaReference:
    """External DefiLlama adapter reference used for venue discovery."""

    path: str
    dashboard: str
    repo: str = DEFILLAMA_DIMENSION_ADAPTERS_REPO
    commit: str | None = None
    notes: str = ""

    @property
    def github_url(self) -> str:
        """Return a stable GitHub URL for the reference path."""
        ref = self.commit if self.commit is not None else "master"
        return f"https://github.com/{self.repo}/blob/{ref}/{self.path}"


@dataclass(frozen=True, slots=True)
class AdapterTemplate:
    """Canonical adapter metadata.

    Execution modules stay explicit. A venue being present here only means the
    solver knows how to classify the venue and where to find its canonical
    addresses and reference adapters.
    """

    venue: str
    category: AdapterCategory
    status: AdapterStatus
    contracts: tuple[ContractBinding, ...]
    registry_keys: tuple[RegistryKey, ...]
    execution_module: str | None = None
    quote_module: str | None = None
    defillama: tuple[DefiLlamaReference, ...] = ()
    ipc_address_keyed_kinds: tuple[str, ...] = ()
    ipc_pool_id_required_kinds: tuple[str, ...] = ()
    ipc_recognized_kinds: tuple[str, ...] = ()
    notes: str = ""

    @property
    def key(self) -> tuple[AdapterCategory, str]:
        """Stable lookup key."""
        return (self.category, self.venue)

    @property
    def enabled_for_execution(self) -> bool:
        """True only for adapters that can be used in production execution planning."""
        return self.status is AdapterStatus.ENABLED

    @property
    def contract_addresses(self) -> tuple[str, ...]:
        """Return all bound contract addresses."""
        return tuple(binding.address for binding in self.contracts)

    @property
    def ipc_kinds(self) -> tuple[str, ...]:
        """Return every IPC discriminator this adapter owns."""
        seen: set[str] = set()
        out: list[str] = []
        for kind in (
            *self.ipc_address_keyed_kinds,
            *self.ipc_pool_id_required_kinds,
            *self.ipc_recognized_kinds,
        ):
            if kind in seen:
                continue
            seen.add(kind)
            out.append(kind)
        return tuple(out)

    def contract(self, export_name: str) -> ContractBinding:
        """Return a named contract binding."""
        for binding in self.contracts:
            if binding.export_name == export_name:
                return binding
        raise KeyError(f"{self.venue} adapter has no contract binding {export_name!r}")


@dataclass(frozen=True, slots=True)
class ExecutionLaneTemplate:
    """Strategy/executor lane metadata.

    Lanes are policy surfaces. They bind strategy modules to adapter categories
    without implying that every referenced adapter is executable.
    """

    lane: ExecutionLane
    status: AdapterStatus
    description: str
    adapter_categories: tuple[AdapterCategory, ...]
    adapter_keys: tuple[tuple[AdapterCategory, str], ...]
    coordinator_modules: tuple[str, ...] = ()
    solver_modules: tuple[str, ...] = ()
    contract_modules: tuple[str, ...] = ()
    policy_gates: tuple[str, ...] = ()
    notes: str = ""

    @property
    def key(self) -> ExecutionLane:
        """Stable lookup key."""
        return self.lane

    @property
    def enabled_for_execution(self) -> bool:
        """True only when the lane may produce executable plans."""
        return self.status is AdapterStatus.ENABLED
