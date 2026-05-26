"""Strategy implementations for the coordinator dispatcher."""

from .types import (
    DEX_KIND as DEX_KIND,
)
from .types import (
    FLASH_PROTOCOL as FLASH_PROTOCOL,
)
from .types import (
    ComposeParams as ComposeParams,
)
from .types import (
    MatchParams as MatchParams,
)
from .types import (
    NativeArbParams as NativeArbParams,
)
from .types import (
    SwapStep as SwapStep,
)

__all__ = [
    "DEX_KIND",
    "FLASH_PROTOCOL",
    "ComposeParams",
    "FourLegPlan",  # noqa: F822
    "FourLegStrategy",  # noqa: F822
    "InternalMatchPlan",  # noqa: F822
    "InternalMatchStrategy",  # noqa: F822
    "MatchParams",
    "NativeArbParams",
    "NativeArbStrategy",  # noqa: F822
    "OracleSandwichPlan",  # noqa: F822
    "OracleSandwichStrategy",  # noqa: F822
    "SwapStep",
]


def __getattr__(name: str) -> object:
    """Lazily load strategy classes so type-only imports do not cycle."""

    if name in {"FourLegPlan", "FourLegStrategy"}:
        from .four_leg import FourLegPlan, FourLegStrategy

        return {"FourLegPlan": FourLegPlan, "FourLegStrategy": FourLegStrategy}[name]
    if name in {"InternalMatchPlan", "InternalMatchStrategy"}:
        from .internal_match import InternalMatchPlan, InternalMatchStrategy

        return {
            "InternalMatchPlan": InternalMatchPlan,
            "InternalMatchStrategy": InternalMatchStrategy,
        }[name]
    if name in {"OracleSandwichPlan", "OracleSandwichStrategy"}:
        from .oracle_sandwich import OracleSandwichPlan, OracleSandwichStrategy

        return {
            "OracleSandwichPlan": OracleSandwichPlan,
            "OracleSandwichStrategy": OracleSandwichStrategy,
        }[name]
    if name == "NativeArbStrategy":
        from .native_arb import NativeArbStrategy

        return NativeArbStrategy
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
