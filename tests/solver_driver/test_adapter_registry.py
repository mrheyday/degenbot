from __future__ import annotations

import importlib
import re
from itertools import starmap
from pathlib import Path

from degenbot.execution.degenbot_ipc import (
    ADDRESS_KEYED_DEGENBOT_DEX_KINDS as IPC_ADDRESS_KEYED_DEGENBOT_DEX_KINDS,
)
from degenbot.execution.degenbot_ipc import (
    POOL_ID_REQUIRED_DEX_KINDS as IPC_POOL_ID_REQUIRED_DEX_KINDS,
)
from degenbot.execution.degenbot_ipc import RECOGNIZED_DEX_KINDS as IPC_RECOGNIZED_DEX_KINDS

from degenbot.adapters import (
    ALL_ADAPTERS,
    EXECUTION_LANES,
    READINESS_EVIDENCE,
    AdapterCategory,
    AdapterStatus,
    ExecutionLane,
    adapter_for,
    adapters_by_category,
    adapters_by_status,
    evidence_for_adapter,
    evidence_for_lane,
    lane_for,
    lanes_by_status,
    parse_sourcify_status,
    readiness_evidence_for_id,
    source_verification_requests,
)
from degenbot.adapters.addresses import REGISTRY_ADDRESSES
from degenbot.adapters.ipc import (
    ADDRESS_KEYED_DEGENBOT_DEX_KINDS,
    POOL_ID_REQUIRED_DEX_KINDS,
    RECOGNIZED_DEX_KINDS,
)


def _find_root():
    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / "PROGRESS.md").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parents[4]


REPO_ROOT = _find_root()
TS_REGISTRY = REPO_ROOT / "coordinator/src/router/registry.ts"


# Addresses that registry.ts holds as static `export const ... satisfies Address`.
# AAVE_V3_POOL and MORPHO_SINGLETON are intentionally absent: ADR-027 migrated
# the deployment-specific Aave/Morpho addresses to `.env` sourcing on the TS
# side (registerDeploymentAddress at boot), so they are no longer direct TS
# exports. Aave-side conformance is covered by test_aave_v3_addresses.py.
DIRECT_TS_EXPORTS = {
    "BALANCER_V2_VAULT",
    "BALANCER_V3_VAULT",
    "BEBOP_SETTLEMENT",
    "CAMELOT_ALGEBRA_V4_SWAP_ROUTER",
    "CAMELOT_V2_ROUTER",
    "CAMELOT_V3_SWAP_ROUTER",
    "COW_FLASH_LOAN_ROUTER",
    "CURVE_ROUTER",
    "DODO_V2_PROXY02",
    "ENSO_ROUTER",
    "HASHFLOW_ROUTER",
    "INSTADAPP_FLASH_AGGREGATOR",
    "INSTADAPP_FLASH_RESOLVER",
    "LIFI_DIAMOND",
    "MAVERICK_V2_ROUTER",
    "NATIVE_CREDIT_VAULT",
    "ODOS_ROUTER_V2",
    "ONEINCH_AGG_V6",
    "PARASWAP_AUGUSTUS_V6",
    "RANGO_DIAMOND",
    "RUBIC_PROXY_V3",
    "WOOFI_ROUTER_V2",
    "ZEROX_EXCHANGE_PROXY",
}


def test_python_address_mirror_matches_direct_ts_registry_exports() -> None:
    registry_source = TS_REGISTRY.read_text()

    for export_name in DIRECT_TS_EXPORTS:
        match = re.search(
            rf"export const {export_name}\s*=\s*['\"]([^'\"]+)['\"]\s+as const satisfies Address",
            registry_source,
            flags=re.MULTILINE,
        )
        if match is None:
            match = re.search(
                rf"export const {export_name}\s*=\s*\n\s*['\"]([^'\"]+)['\"]\s+as const satisfies Address",
                registry_source,
                flags=re.MULTILINE,
            )

        assert match is not None, f"missing direct TS export for {export_name}"
        assert REGISTRY_ADDRESSES[export_name] == match.group(1)


def test_category_folders_expose_swap_flash_and_liquidity_adapters() -> None:
    assert len(adapters_by_category(AdapterCategory.SWAP)) >= 10
    assert len(adapters_by_category(AdapterCategory.FLASH)) >= 4
    assert len(adapters_by_category(AdapterCategory.LIQUIDITY)) >= 5


def test_lookup_returns_category_scoped_adapters() -> None:
    morpho_flash = adapter_for("flash", "MorphoFlash")
    morpho_liquidity = adapter_for("liquidity", "MorphoLiquidity")

    assert morpho_flash.category is AdapterCategory.FLASH
    assert morpho_flash.contract("MORPHO_SINGLETON").role == "singleton"
    assert morpho_liquidity.category is AdapterCategory.LIQUIDITY
    assert morpho_liquidity.execution_module == "degenbot.execution_adapters.morpho_lp_adapter"


def test_adapter_module_paths_resolve_inside_vendored_python_package() -> None:
    for adapter in ALL_ADAPTERS:
        for module_name in (adapter.execution_module, adapter.quote_module):
            if module_name is None or not module_name.startswith("degenbot."):
                continue
            importlib.import_module(module_name)


def test_execution_adapters_package_exports_calldata_encoders() -> None:
    from degenbot.execution_adapters import (
        encode_compose_four_leg_calldata,
        encode_match_internal_calldata,
        encode_native_arb_calldata,
    )

    assert callable(encode_native_arb_calldata)
    assert callable(encode_match_internal_calldata)
    assert callable(encode_compose_four_leg_calldata)


def test_enabled_adapters_have_contract_bindings_and_sourcify_urls() -> None:
    for adapter in adapters_by_status(AdapterStatus.ENABLED):
        assert adapter.contracts, adapter.venue
        for contract in adapter.contracts:
            assert (
                contract.source_ref == f"coordinator/src/router/registry.ts:{contract.export_name}"
            )
            assert contract.sourcify_url.startswith(
                "https://sourcify.dev/server/v2/contract/42161/0x"
            )


def test_reference_only_adapters_do_not_become_execution_enabled() -> None:
    reference_only = adapters_by_status(AdapterStatus.REFERENCE_ONLY)

    assert any(adapter.venue == "FluidDex" for adapter in reference_only)
    assert all(not adapter.enabled_for_execution for adapter in reference_only)


def test_defillama_references_are_pinned_to_commit() -> None:
    refs = [ref for adapter in ALL_ADAPTERS for ref in adapter.defillama]

    assert refs
    assert any(ref.path == "dexs/fluid-dex/index.ts" for ref in refs)
    assert any(ref.path == "aggregators/odos/index.ts" for ref in refs)
    for ref in refs:
        assert ref.commit == "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9"
        assert ref.github_url.startswith("https://github.com/DefiLlama/dimension-adapters/blob/")


def test_registry_poc_dex_lanes_have_defillama_discovery_refs() -> None:
    adapter = adapter_for("swap", "RegistryPocDexLanes")
    paths = {ref.path for ref in adapter.defillama}

    assert {
        "aggregators/joe-agg/index.ts",
        "aggregators/kyberswap/index.ts",
        "dexs/gmx-v2-gmx-v2-swap.ts",
        "dexs/wombat-exchange/index.ts",
    } <= paths
    assert all(ref.commit == "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9" for ref in adapter.defillama)
    assert not adapter.enabled_for_execution


def test_reference_only_flash_adapters_have_defillama_refs_without_execution() -> None:
    cow = adapter_for("flash", "CowFlashLoanRouter")
    instadapp = adapter_for("flash", "InstaDappFlashAggregator")

    assert {ref.path for ref in cow.defillama} == {
        "aggregators/cowswap/index.ts",
        "fees/cow-protocol.ts",
    }
    assert {ref.path for ref in instadapp.defillama} == {"fees/instadapp/index.ts"}
    assert all(
        ref.commit == "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9"
        for ref in (*cow.defillama, *instadapp.defillama)
    )
    assert not cow.enabled_for_execution
    assert not instadapp.enabled_for_execution


def test_enabled_flash_adapters_have_defillama_refs() -> None:
    expected_paths = {
        "AaveV3Flash": {"fees/aave-v3.ts"},
        "MorphoFlash": {"fees/morpho/index.ts"},
        "BalancerV2Flash": {"dexs/balancer-v2.ts"},
        "BalancerV3Flash": {"dexs/balancer-v3/index.ts"},
    }

    for venue, paths in expected_paths.items():
        adapter = adapter_for("flash", venue)
        assert paths <= {ref.path for ref in adapter.defillama}
        assert all(ref.commit == "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9" for ref in adapter.defillama)
        assert adapter.enabled_for_execution


def test_read_only_liquidity_adapters_have_defillama_refs() -> None:
    expected_paths = {
        "UniswapV3Liquidity": {"dexs/uniswap-v3.ts"},
        "UniswapV4Liquidity": {"dexs/uniswap-v4.ts"},
        "MetaMorphoVaults": {"fees/morpho/index.ts"},
    }

    for venue, paths in expected_paths.items():
        adapter = adapter_for("liquidity", venue)
        assert paths <= {ref.path for ref in adapter.defillama}
        assert all(ref.commit == "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9" for ref in adapter.defillama)
        assert not adapter.enabled_for_execution


def test_native_and_forked_swap_adapters_have_defillama_refs() -> None:
    expected_paths = {
        "UniswapV2": {"dexs/uniswap-v2.ts"},
        "UniswapV3": {"dexs/uniswap-v3.ts"},
        "UniswapV4": {"dexs/uniswap-v4.ts"},
        "SushiSwap": {"dexs/sushiswap-v3.ts", "aggregators/sushiswap-agg.ts"},
        "PancakeSwapV3": {"dexs/pancakeswap-v3.ts"},
        "Solidly": {
            "dexs/ramsesx-arb-legacy.ts",
            "dexs/ramsesx-arb-cl.ts",
            "dexs/solidly-v3/index.ts",
        },
    }

    for venue, paths in expected_paths.items():
        adapter = adapter_for("swap", venue)
        assert paths <= {ref.path for ref in adapter.defillama}
        assert all(ref.commit == "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9" for ref in adapter.defillama)


def test_adapter_ipc_sets_preserve_existing_degenbot_surface() -> None:
    assert (
        frozenset(
            {
                "Aerodrome",
                "BalancerV2",
                "CamelotV2",
                "CamelotV3",
                "Curve",
                "CurveNG",
                "DodoPmm",
                "PancakeSwapV2",
                "PancakeSwapV3",
                "Solidly",
                "SushiSwapV2",
                "SushiSwapV3",
                "UniswapV2",
                "UniswapV3",
            },
        )
        == ADDRESS_KEYED_DEGENBOT_DEX_KINDS
    )
    assert frozenset({"UniswapV4"}) == POOL_ID_REQUIRED_DEX_KINDS
    assert {
        "AggregatorV6",
        "MorphoBlue",
        "MaverickV2",
        "FluidDex",
        "LiFi",
        "Native",
    }.issubset(RECOGNIZED_DEX_KINDS)


def test_degenbot_ipc_imports_adapter_derived_sets() -> None:
    assert IPC_ADDRESS_KEYED_DEGENBOT_DEX_KINDS is ADDRESS_KEYED_DEGENBOT_DEX_KINDS
    assert IPC_POOL_ID_REQUIRED_DEX_KINDS is POOL_ID_REQUIRED_DEX_KINDS
    assert IPC_RECOGNIZED_DEX_KINDS is RECOGNIZED_DEX_KINDS


def test_source_verification_requests_use_contract_bindings() -> None:
    adapter = adapter_for("swap", "AggregatorV6")
    requests = source_verification_requests(adapter)

    assert requests[0].source_ref == "coordinator/src/router/registry.ts:ONEINCH_AGG_V6"
    assert requests[0].role == "1inch"
    assert requests[0].url.endswith("/v2/contract/42161/0x111111125421cA6dc452d289314280a0f8842A65")


def test_parse_sourcify_status_accepts_verified_and_unverified_payloads() -> None:
    verified = parse_sourcify_status(
        {
            "match": "match",
            "creationMatch": "partial_match",
            "runtimeMatch": "exact_match",
            "chainId": "42161",
            "address": REGISTRY_ADDRESSES["ONEINCH_AGG_V6"],
            "matchId": "123",
            "verifiedAt": "2026-05-14T00:00:00Z",
        },
    )
    unverified = parse_sourcify_status(
        {
            "match": None,
            "creationMatch": None,
            "runtimeMatch": None,
            "chainId": "42161",
            "address": REGISTRY_ADDRESSES["MORPHO_SINGLETON"],
        },
    )

    assert verified.verified is True
    assert verified.match_id == "123"
    assert unverified.verified is False


def test_execution_lane_registry_covers_universal_routers_and_strategy_splits() -> None:
    lanes = {lane.lane for lane in EXECUTION_LANES}

    assert ExecutionLane.UNIVERSAL_FLASH_AGGREGATOR_ROUTER in lanes
    assert ExecutionLane.UNIVERSAL_SWAP_AGGREGATOR_ROUTER in lanes
    assert ExecutionLane.UNIVERSAL_PATHFINDER_QUOTER_ROUTER in lanes
    assert ExecutionLane.UNIVERSAL_LIQUIDITY_AGGREGATOR_ROUTER in lanes
    assert ExecutionLane.ARB_EXECUTOR in lanes
    assert ExecutionLane.INTENT_EXECUTOR in lanes
    assert ExecutionLane.JIT_EXECUTOR in lanes
    assert ExecutionLane.LIQUIDATION_EXECUTOR in lanes
    assert ExecutionLane.SANDWICH_EXECUTOR in lanes


def test_execution_lane_adapter_keys_resolve_to_registered_adapters() -> None:
    adapter_keys = {adapter.key for adapter in ALL_ADAPTERS}

    for lane in EXECUTION_LANES:
        for adapter_key in lane.adapter_keys:
            assert adapter_key in adapter_keys, (
                f"{lane.lane.value} references missing {adapter_key}"
            )


def test_enabled_lanes_have_policy_gates_and_modules() -> None:
    for lane in lanes_by_status(AdapterStatus.ENABLED):
        assert lane.enabled_for_execution
        assert lane.policy_gates
        assert lane.coordinator_modules
        assert lane.adapter_categories


def test_universal_flash_lane_keeps_read_only_sources_from_auto_execution() -> None:
    lane = lane_for("universal_flash_aggregator_router")
    lane_adapters = list(starmap(adapter_for, lane.adapter_keys))

    assert adapter_for("flash", "AaveV3Flash").enabled_for_execution
    assert adapter_for("flash", "MorphoFlash").enabled_for_execution
    assert any(not adapter.enabled_for_execution for adapter in lane_adapters)
    assert lane.enabled_for_execution


def test_readiness_evidence_is_machine_readable_and_paths_exist() -> None:
    expected_ids = {
        "balancer-v2-flash-callback",
        "balancer-v3-transient-unlock",
        "balancer-v3-swap-preencoded-routing",
        "intent-settlement-receiver-replay",
        "universal-liquidity-mutation-policy",
        "jit-self-controlled-liquidity-lane",
        "oracle-sandwich-execution-lane",
    }

    assert {evidence.evidence_id for evidence in READINESS_EVIDENCE} == expected_ids
    for evidence in READINESS_EVIDENCE:
        assert evidence.approved_for_execution
        assert evidence.policy_gates
        assert evidence.scope
        for path in (*evidence.contracts, *evidence.coordinator_modules, *evidence.tests):
            assert (REPO_ROOT / path).exists(), f"{evidence.evidence_id} references missing {path}"


def test_balancer_readiness_promotes_universal_flash_adapter_surfaces() -> None:
    v2_flash = adapter_for("flash", "BalancerV2Flash")
    v3_flash = adapter_for("flash", "BalancerV3Flash")
    balancer_swap = adapter_for("swap", "Balancer")

    assert v2_flash.status is AdapterStatus.ENABLED
    assert v3_flash.status is AdapterStatus.ENABLED
    assert balancer_swap.status is AdapterStatus.ENABLED
    assert "Universal flash source" in v2_flash.notes
    assert "Universal flash source" in v3_flash.notes
    assert "not selectable by the generic Executor flash router" not in v2_flash.notes
    assert "not selectable by the generic Executor flash router" not in v3_flash.notes
    assert "pre-encoded calldata" in balancer_swap.notes

    assert readiness_evidence_for_id("balancer-v2-flash-callback") in evidence_for_adapter(
        "flash", "BalancerV2Flash"
    )
    assert readiness_evidence_for_id("balancer-v3-transient-unlock") in evidence_for_adapter(
        "flash", "BalancerV3Flash"
    )
    assert readiness_evidence_for_id("balancer-v3-swap-preencoded-routing") in evidence_for_adapter(
        "swap", "Balancer"
    )


def test_intent_and_liquidity_lanes_are_enabled_with_replay_and_unwind_gates() -> None:
    intent = lane_for(ExecutionLane.INTENT_EXECUTOR)
    liquidity = lane_for(ExecutionLane.UNIVERSAL_LIQUIDITY_AGGREGATOR_ROUTER)

    assert intent.status is AdapterStatus.ENABLED
    assert "CoW chained-hash replay root" in intent.policy_gates
    assert "UniswapX reactor transient sender gate" in intent.policy_gates
    assert readiness_evidence_for_id("intent-settlement-receiver-replay") in evidence_for_lane(
        intent.lane
    )

    assert liquidity.status is AdapterStatus.ENABLED
    assert "per-token and per-pool exposure cap" in liquidity.policy_gates
    assert "same-transaction unwind or explicit TTL close plan" in liquidity.policy_gates
    assert "post-unwind inventory neutrality" in liquidity.policy_gates
    assert readiness_evidence_for_id("universal-liquidity-mutation-policy") in evidence_for_lane(
        liquidity.lane
    )


def test_jit_and_sandwich_lanes_are_enabled_with_scoped_execution_gates() -> None:
    jit = lane_for(ExecutionLane.JIT_EXECUTOR)
    sandwich = lane_for(ExecutionLane.SANDWICH_EXECUTOR)

    assert jit.status is AdapterStatus.ENABLED
    assert jit.enabled_for_execution
    assert "flash-funded mint/swap/burn/collect envelope" in jit.policy_gates
    assert (
        "external trigger ordering proof when trigger source is not solver-owned"
        in jit.policy_gates
    )
    assert "post-unwind inventory neutrality" in jit.policy_gates
    assert readiness_evidence_for_id("jit-self-controlled-liquidity-lane") in evidence_for_lane(
        jit.lane
    )

    assert sandwich.status is AdapterStatus.ENABLED
    assert sandwich.enabled_for_execution
    assert "offensive variant enable map defaults on" in sandwich.policy_gates
    assert "flash-funded executeNativeArb envelope" in sandwich.policy_gates
    assert "single-transaction round trip" in sandwich.policy_gates
    assert readiness_evidence_for_id("oracle-sandwich-execution-lane") in evidence_for_lane(
        sandwich.lane
    )


def test_adapter_lane_plan_no_longer_has_unresolved_read_only_blockers() -> None:
    plan = (REPO_ROOT / "docs/architecture/adapter-execution-lane-plan.md").read_text()

    assert "## Current Blockers" not in plan
    assert "Balancer V2/V3 flash and Balancer V3 swap routing remain read-only" not in plan
    assert "Intent settlement remains read-only" not in plan
    assert "Universal liquidity routing is read-only" not in plan
    assert "JitExecutor | Read-only" not in plan
    assert "SandwichExecutor | Blocked" not in plan
    assert "generic Executor flash source router still selects only providers" not in plan
    assert "Balancer V2 and V3 flash remain dedicated callback lanes" not in plan
    assert "The Executor does not implement Balancer pool math or a Balancer callback" not in plan
    assert (
        "CoW solver competition onboarding and bond operations remain operational readiness tasks"
        not in plan
    )
    assert "Universal liquidity routing is not an autonomous LP manager" not in plan
    assert "External victim-trigger JIT still needs ordering proof" not in plan
    assert "Direct router calls and owned-inventory legs remain out of scope" not in plan
