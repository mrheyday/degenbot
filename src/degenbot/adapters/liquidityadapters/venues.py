"""Read-side liquidity and LP-management adapter registry."""

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


LIQUIDITY_ADAPTERS: tuple[AdapterTemplate, ...] = (
    AdapterTemplate(
        venue="UniswapV3Liquidity",
        category=AdapterCategory.LIQUIDITY,
        status=AdapterStatus.READ_ONLY,
        contracts=bindings(
            ("UNIV3_POSITION_MANAGER", "position_manager"),
            ("UNIV3_FACTORY", "factory"),
            ("UNIV3_QUOTER_V2", "quoter"),
        ),
        registry_keys=(RegistryKey.FACTORY, RegistryKey.ADDRESS),
        execution_module="degenbot.uniswap.v3_liquidity_pool",
        notes="Degenbot SQLite-backed V3 liquidity snapshots are the read surface.",
    ),
    AdapterTemplate(
        venue="UniswapV4Liquidity",
        category=AdapterCategory.LIQUIDITY,
        status=AdapterStatus.READ_ONLY,
        contracts=bindings(
            ("UNIV4_POOL_MANAGER", "pool_manager"),
            ("UNIV4_POSITION_MANAGER", "position_manager"),
            ("UNIV4_STATE_VIEW", "state_view"),
        ),
        registry_keys=(RegistryKey.POOL_ID,),
        execution_module="degenbot.uniswap.v4_liquidity_pool",
        notes="PoolManager/StateView reads feed policy-gated Uniswap V4 LP mutation planning.",
    ),
    AdapterTemplate(
        venue="BalancerLiquidity",
        category=AdapterCategory.LIQUIDITY,
        status=AdapterStatus.READ_ONLY,
        contracts=bindings(
            ("BALANCER_V2_VAULT", "v2_vault"),
            ("BALANCER_V3_VAULT", "v3_vault"),
            ("BALANCER_V3_BUFFER_ROUTER", "buffer_router"),
        ),
        registry_keys=(RegistryKey.VAULT,),
        execution_module="driver.execution.balancer_v3_adapter",
        defillama=(dl("dexs/balancer-v3/index.ts", "dexs"),),
        notes="Vault and buffer metadata feed policy-gated Balancer LP mutation planning.",
    ),
    AdapterTemplate(
        venue="CurveLiquidity",
        category=AdapterCategory.LIQUIDITY,
        status=AdapterStatus.READ_ONLY,
        contracts=bindings(("CURVE_STABLESWAP_REGISTRY", "registry"), ("CURVE_ROUTER", "router")),
        registry_keys=(RegistryKey.ADDRESS,),
        execution_module="driver.execution.curve_ng_adapter",
        defillama=(dl("dexs/curve/index.ts", "dexs"),),
        notes="Registry and pool metadata for Curve legacy/NG liquidity discovery.",
    ),
    AdapterTemplate(
        venue="MorphoLiquidity",
        category=AdapterCategory.LIQUIDITY,
        status=AdapterStatus.ENABLED,
        contracts=bindings(
            ("MORPHO_SINGLETON", "singleton"),
            ("MORPHO_MARKET_V1_REGISTRY", "market_registry"),
            ("MORPHO_PRELIQUIDATION_FACTORY", "preliquidation_factory"),
        ),
        registry_keys=(RegistryKey.MARKET_ID,),
        execution_module="driver.execution.morpho_lp_adapter",
        ipc_recognized_kinds=("MorphoBlue",),
        defillama=(dl("fees/morpho/index.ts"),),
        notes="Morpho market/liquidation discovery is active; transaction construction is strategy-gated.",
    ),
    AdapterTemplate(
        venue="MetaMorphoVaults",
        category=AdapterCategory.LIQUIDITY,
        status=AdapterStatus.READ_ONLY,
        contracts=bindings(("MORPHO_SINGLETON", "singleton")),
        registry_keys=(RegistryKey.VAULT, RegistryKey.MARKET_ID),
        execution_module="driver.execution.metamorpho_v1_adapter",
        notes="Vault allocation and risk reads for liquidity ranking.",
    ),
    AdapterTemplate(
        venue="AaveLiquidity",
        category=AdapterCategory.LIQUIDITY,
        status=AdapterStatus.READ_ONLY,
        contracts=bindings(("AAVE_V3_POOL", "v3_pool")),
        registry_keys=(RegistryKey.ADDRESS,),
        execution_module="driver.execution.aave_v4_adapter",
        defillama=(dl("fees/aave-v3.ts"), dl("fees/aave-v4.ts")),
        notes="Aave V3 address is canonical for flash; V4 adapter remains read-side GraphQL.",
    ),
    AdapterTemplate(
        venue="NativeCreditLiquidity",
        category=AdapterCategory.LIQUIDITY,
        status=AdapterStatus.REFERENCE_ONLY,
        contracts=bindings(("NATIVE_CREDIT_VAULT", "credit_vault")),
        registry_keys=(RegistryKey.VAULT,),
        defillama=(dl("dexs/native/index.ts", "dexs"),),
        notes="Native Protocol credit vault is reference metadata until risk model is specified.",
    ),
)
