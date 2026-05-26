"""Flash-liquidity venue adapters."""

from __future__ import annotations

from degenbot.adapters.addresses import bindings
from degenbot.adapters.templates import (
    AdapterCategory,
    AdapterStatus,
    AdapterTemplate,
    RegistryKey,
)

FLASH_ADAPTERS: tuple[AdapterTemplate, ...] = (
    AdapterTemplate(
        venue="AaveV3Flash",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.ENABLED,
        contracts=bindings(("AAVE_V3_POOL", "pool")),
        registry_keys=(RegistryKey.ADDRESS,),
        execution_module="degenbot.execution_adapters.aave_v3_flashloan_adapter",
        notes="Executor-compatible multi-asset flash-loan source; array form only.",
    ),
    AdapterTemplate(
        venue="MorphoFlash",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.ENABLED,
        contracts=bindings(("MORPHO_SINGLETON", "singleton")),
        registry_keys=(RegistryKey.ADDRESS,),
        execution_module="degenbot.execution_adapters.morpho_flashloan_adapter",
        notes="Zero-fee Morpho Blue flash source; callback data must include borrowed token.",
    ),
    AdapterTemplate(
        venue="BalancerV2Flash",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.ENABLED,
        contracts=bindings(("BALANCER_V2_VAULT", "vault")),
        registry_keys=(RegistryKey.VAULT,),
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
        notes=("Universal flash source via MevSafe.flashCollateralizeV3 transient-unlock plans."),
    ),
    AdapterTemplate(
        venue="CowFlashLoanRouter",
        category=AdapterCategory.FLASH,
        status=AdapterStatus.REFERENCE_ONLY,
        contracts=bindings(("COW_FLASH_LOAN_ROUTER", "aave_borrower")),
        registry_keys=(RegistryKey.ADDRESS,),
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
        notes="Monitor/reference only; not an Executor flash source.",
    ),
)
