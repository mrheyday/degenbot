# F822: symbols in __all__ are resolved through __getattr__ below.
# ruff: noqa: F822
"""Execution adapter modules for flash, swap, liquidation, and verification lanes."""

from __future__ import annotations

from importlib import import_module

_EXPORTS: dict[str, str] = {
    "AaveV3FlashLoanBuilder": "aave_v3_flashloan_adapter",
    "AaveV3FlashLoanRequest": "aave_v3_flashloan_adapter",
    "AaveV4Client": "aave_v4_adapter",
    "AaveV4Reserve": "aave_v4_adapter",
    "AaveV4SwapQuote": "aave_v4_adapter",
    "AaveV4UserHealth": "aave_v4_adapter",
    "BalancerV3Client": "balancer_v3_adapter",
    "BalancerV3Pool": "balancer_v3_adapter",
    "BalancerV3PoolType": "balancer_v3_adapter",
    "CamelotV3Pool": "camelot_v3_adapter",
    "CamelotV3PoolState": "camelot_v3_adapter",
    "CurveNGPool": "curve_ng_adapter",
    "CurveNGPoolState": "curve_ng_adapter",
    "DodoPmmPool": "dodo_pmm_adapter",
    "DodoPmmPoolState": "dodo_pmm_adapter",
    "FluidDexClient": "fluid_dex_adapter",
    "FluidPool": "fluid_dex_adapter",
    "MaverickV2Client": "maverick_v2_adapter",
    "MaverickV2Pool": "maverick_v2_adapter",
    "MetaMorphoV1Client": "metamorpho_v1_adapter",
    "MorphoFlashLoanBuilder": "morpho_flashloan_adapter",
    "MorphoFlashLoanRequest": "morpho_flashloan_adapter",
    "MorphoLpClient": "morpho_lp_adapter",
    "MorphoMarket": "morpho_lp_adapter",
    "MorphoPosition": "morpho_lp_adapter",
    "MultiTickCrossingNotSupportedError": "camelot_v3_adapter",
    "SolidlyV1Pool": "solidly_adapter",
    "SolidlyV1PoolState": "solidly_adapter",
}

__all__ = [
    "AaveV3FlashLoanBuilder",
    "AaveV3FlashLoanRequest",
    "AaveV4Client",
    "AaveV4Reserve",
    "AaveV4SwapQuote",
    "AaveV4UserHealth",
    "BalancerV3Client",
    "BalancerV3Pool",
    "BalancerV3PoolType",
    "CamelotV3Pool",
    "CamelotV3PoolState",
    "CurveNGPool",
    "CurveNGPoolState",
    "DodoPmmPool",
    "DodoPmmPoolState",
    "FluidDexClient",
    "FluidPool",
    "MaverickV2Client",
    "MaverickV2Pool",
    "MetaMorphoV1Client",
    "MorphoFlashLoanBuilder",
    "MorphoFlashLoanRequest",
    "MorphoLpClient",
    "MorphoMarket",
    "MorphoPosition",
    "MultiTickCrossingNotSupportedError",
    "SolidlyV1Pool",
    "SolidlyV1PoolState",
]


def __getattr__(name: str) -> object:
    """Resolve adapter symbols lazily so one venue cannot break package import."""

    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(name)
    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
