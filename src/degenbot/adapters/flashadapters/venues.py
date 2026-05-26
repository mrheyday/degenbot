"""Flash-liquidity venue adapters."""

from __future__ import annotations

from degenbot.adapters.addresses import bindings
from degenbot.adapters.templates import (
    AdapterCategory,
    AdapterStatus,
    AdapterTemplate,
    DefiLlamaReference,
    RegistryKey,
)

DL_COMMIT = "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9"


def dl(path: str, dashboard: str = "fees", notes: str = "") -> DefiLlamaReference:
    """Create a DefiLlama dimension-adapter reference."""
    return DefiLlamaReference(path=path, dashboard=dashboard, commit=DL_COMMIT, notes=notes)


FLASH_ADAPTERS: tuple[AdapterTemplate, ...] = (
    AdapterTemplate(
        venue="AaveV3Flash",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.ENABLED,
        contracts=bindings(("AAVE_V3_POOL", "pool")),
        registry_keys=(RegistryKey.ADDRESS,),
        execution_module="degenbot.execution_adapters.aave_v3_flashloan_adapter",
        defillama=(dl("fees/aave-v3.ts"),),
        notes="Executor-compatible multi-asset flash-loan source; array form only.",
    ),
    AdapterTemplate(
        venue="MorphoFlash",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.ENABLED,
        contracts=bindings(("MORPHO_SINGLETON", "singleton")),
        registry_keys=(RegistryKey.ADDRESS,),
        execution_module="degenbot.execution_adapters.morpho_flashloan_adapter",
        defillama=(dl("fees/morpho/index.ts"),),
        notes="Zero-fee Morpho Blue flash source; callback data must include borrowed token.",
    ),
    AdapterTemplate(
        venue="BalancerV2Flash",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.ENABLED,
        contracts=bindings(("BALANCER_V2_VAULT", "vault")),
        registry_keys=(RegistryKey.VAULT,),
        defillama=(dl("dexs/balancer-v2.ts", "dexs"),),
        notes=(
            "Universal flash source via Balancer V2 callback plans for LiquidationExecutor or MevSafe."
        ),
    ),
    AdapterTemplate(
        venue="BalancerV3Flash",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.ENABLED,
        contracts=bindings(("BALANCER_V3_VAULT", "vault")),
        registry_keys=(RegistryKey.VAULT,),
        defillama=(dl("dexs/balancer-v3/index.ts", "dexs"),),
        notes=("Universal flash source via MevSafe.flashCollateralizeV3 transient-unlock plans."),
    ),
    AdapterTemplate(
        venue="CowFlashLoanRouter",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.REFERENCE_ONLY,
        contracts=bindings(("COW_FLASH_LOAN_ROUTER", "aave_borrower")),
        registry_keys=(RegistryKey.ADDRESS,),
        defillama=(
            dl("aggregators/cowswap/index.ts", "aggregators"),
            dl("fees/cow-protocol.ts"),
        ),
        notes="Pinned for attribution and future CoW-flash-router evaluation.",
    ),
    AdapterTemplate(
        venue="InstaDappFlashAggregator",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.REFERENCE_ONLY,
        contracts=bindings(
            ("INSTADAPP_FLASH_AGGREGATOR", "aggregator"),
            ("INSTADAPP_FLASH_RESOLVER", "resolver"),
        ),
        registry_keys=(RegistryKey.ADDRESS,),
        defillama=(dl("fees/instadapp/index.ts"),),
        notes="Monitor/reference only; not an Executor flash source.",
    ),
)
