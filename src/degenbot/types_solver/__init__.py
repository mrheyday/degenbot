"""Phase F (Python) — canonical mirror of `IExecutor.sol` strategy structs.

This package holds the Python-side ABI-encoding mirror of the Executor
strategy entry points (``executeNativeArb``, ``matchInternal``,
``composeFourLeg``). Every field name, ordering, and wire type matches the
on-chain interface verbatim — reordering or renaming a field will silently
break ABI parity with the contract.

Cross-language lock
-------------------
The single source of truth for byte-level calldata equivalence is
``coordinator/src/types/fixtures.json``. TypeScript (viem) emits the
fixtures, and the Python encoders here MUST reproduce each fixture's
``calldata`` field byte-identically. The regression test
``test_fixtures_lock.py`` enforces that property.

Modules
-------
- :mod:`driver.types.executor` — frozen dataclasses + ``IntEnum`` ordinals
  for ``FlashProtocol`` / ``DexKind`` / ``SwapStep`` / ``NativeArbParams`` /
  ``MatchParams`` / ``ComposeParams``.
- :mod:`driver.types.wire` — JSON parsers that hydrate the dataclasses
  from the cross-language fixtures wire format (camelCase keys, decimal
  string ``bigint``).
- :mod:`driver.types.codec` — ABI-encoding helpers built on ``eth_abi``.
  Produces 0x-prefixed lowercase hex calldata identical to viem's
  ``encodeFunctionData`` against ``executorAbi``.

Spec pointers
-------------
- ``contracts/src/interfaces/IExecutor.sol``  (struct shapes)
- ``contracts/src/interfaces/IFlashLoanInterfaces.sol``  (``FlashProtocol`` enum)
- ``coordinator/src/types/README.md``  (cross-language wire-format invariants)
"""

from __future__ import annotations

from degenbot.types_solver.codec import (
    COMPOSE_FOUR_LEG_SELECTOR,
    EXECUTE_NATIVE_ARB_SELECTOR,
    MATCH_INTERNAL_SELECTOR,
    encode_compose_four_leg,
    encode_match_internal,
    encode_native_arb,
)
from degenbot.types_solver.executor import (
    ZERO_ADDRESS,
    ComposeParams,
    DexKind,
    FlashProtocol,
    MatchParams,
    NativeArbParams,
    SwapStep,
)
from degenbot.types_solver.wire import (
    Opportunity,
    compose_params_from_wire,
    from_wire_json,
    match_params_from_wire,
    native_arb_from_wire,
)

__all__ = [
    "COMPOSE_FOUR_LEG_SELECTOR",
    "EXECUTE_NATIVE_ARB_SELECTOR",
    "MATCH_INTERNAL_SELECTOR",
    "ZERO_ADDRESS",
    "ComposeParams",
    "DexKind",
    "FlashProtocol",
    "MatchParams",
    "NativeArbParams",
    "Opportunity",
    "SwapStep",
    "compose_params_from_wire",
    "encode_compose_four_leg",
    "encode_match_internal",
    "encode_native_arb",
    "from_wire_json",
    "match_params_from_wire",
    "native_arb_from_wire",
]
