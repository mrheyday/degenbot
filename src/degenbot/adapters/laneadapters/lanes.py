"""Executor-lane plan over the venue adapter registry."""

from __future__ import annotations

from degenbot.adapters.templates import (
    AdapterCategory,
    AdapterStatus,
    ExecutionLane,
    ExecutionLaneTemplate,
)


def adapter_key(category: AdapterCategory, venue: str) -> tuple[AdapterCategory, str]:
    """Return a category-scoped adapter key."""
    return (category, venue)


EXECUTION_LANES: tuple[ExecutionLaneTemplate, ...] = (
    ExecutionLaneTemplate(
        lane=ExecutionLane.UNIVERSAL_FLASH_AGGREGATOR_ROUTER,
        status=AdapterStatus.ENABLED,
        description="Deterministic flash-source selector for zero-capital execution.",
        adapter_categories=(AdapterCategory.FLASH,),
        adapter_keys=(
            adapter_key(AdapterCategory.FLASH, "AaveV3Flash"),
            adapter_key(AdapterCategory.FLASH, "MorphoFlash"),
            adapter_key(AdapterCategory.FLASH, "BalancerV2Flash"),
            adapter_key(AdapterCategory.FLASH, "BalancerV3Flash"),
            adapter_key(AdapterCategory.FLASH, "CowFlashLoanRouter"),
            adapter_key(AdapterCategory.FLASH, "InstaDappFlashAggregator"),
        ),
        coordinator_modules=("coordinator/src/flash/source-router.ts",),
        solver_modules=(
            "driver.execution.aave_v3_flashloan_adapter",
            "driver.execution.morpho_flashloan_adapter",
        ),
        contract_modules=("contracts/src/Executor.sol",),
        policy_gates=(
            "borrow asset allowlist",
            "provider callback selector allowlist",
            "scoped Balancer callback lane evidence",
            "post-trade balance invariant",
            "profit-after-gas invariant",
        ),
        notes=(
            "Universal flash routing selects direct Executor callbacks where available and adapter-specific "
            "callback plans for Balancer V2/V3 when their scoped evidence gates pass."
        ),
    ),
    ExecutionLaneTemplate(
        lane=ExecutionLane.UNIVERSAL_SWAP_AGGREGATOR_ROUTER,
        status=AdapterStatus.ENABLED,
        description="Audited swap-routing lane for AMM pools and approved aggregators.",
        adapter_categories=(AdapterCategory.SWAP,),
        adapter_keys=(
            adapter_key(AdapterCategory.SWAP, "UniswapV2"),
            adapter_key(AdapterCategory.SWAP, "UniswapV3"),
            adapter_key(AdapterCategory.SWAP, "UniswapV4"),
            adapter_key(AdapterCategory.SWAP, "AggregatorV6"),
            adapter_key(AdapterCategory.SWAP, "SushiSwap"),
            adapter_key(AdapterCategory.SWAP, "PancakeSwapV3"),
            adapter_key(AdapterCategory.SWAP, "Camelot"),
            adapter_key(AdapterCategory.SWAP, "Curve"),
            adapter_key(AdapterCategory.SWAP, "CurveNG"),
            adapter_key(AdapterCategory.SWAP, "Balancer"),
            adapter_key(AdapterCategory.SWAP, "DodoPmm"),
            adapter_key(AdapterCategory.SWAP, "Solidly"),
        ),
        coordinator_modules=(
            "coordinator/src/router/index.ts",
            "coordinator/src/router/encode.ts",
            "coordinator/src/router/multi-hop.ts",
        ),
        solver_modules=(
            "driver.execution.degenbot_ipc",
            "driver.execution.aggregator_validator",
        ),
        contract_modules=("contracts/src/Executor.sol",),
        policy_gates=(
            "router address whitelist",
            "callee selector whitelist",
            "slippage bound",
            "token balance delta accounting",
        ),
        notes=(
            "Aggregator routes remain constrained to the ADR-016 router binding; Balancer V3 routes require "
            "canonical Balancer router-suite targets in coordinator/src/router/encode.ts."
        ),
    ),
    ExecutionLaneTemplate(
        lane=ExecutionLane.UNIVERSAL_PATHFINDER_QUOTER_ROUTER,
        status=AdapterStatus.ENABLED,
        description="Read-side quote and pathfinding layer before executable route sealing.",
        adapter_categories=(
            AdapterCategory.SWAP,
            AdapterCategory.QUOTE,
            AdapterCategory.PATHFINDER,
        ),
        adapter_keys=(
            adapter_key(AdapterCategory.SWAP, "UniswapV2"),
            adapter_key(AdapterCategory.SWAP, "UniswapV3"),
            adapter_key(AdapterCategory.SWAP, "UniswapV4"),
            adapter_key(AdapterCategory.SWAP, "AggregatorV6"),
            adapter_key(AdapterCategory.SWAP, "Curve"),
            adapter_key(AdapterCategory.SWAP, "CurveNG"),
            adapter_key(AdapterCategory.SWAP, "Balancer"),
            adapter_key(AdapterCategory.SWAP, "DodoPmm"),
            adapter_key(AdapterCategory.SWAP, "MaverickV2"),
            adapter_key(AdapterCategory.SWAP, "FluidDex"),
            adapter_key(AdapterCategory.SWAP, "RFQAndCrossChainAggregators"),
        ),
        coordinator_modules=(
            "coordinator/src/quotes/index.ts",
            "coordinator/src/quotes/execution-path.ts",
            "coordinator/src/strategies/route-comparator/index.ts",
        ),
        solver_modules=(
            "driver.quote_engine.http_client",
            "driver.execution.degenbot_ipc",
        ),
        policy_gates=(
            "pinned block state",
            "quote freshness window",
            "simulated route dominance",
            "no execution without sealed route hash",
        ),
        notes="This lane may reference read-only adapters because it does not build calldata.",
    ),
    ExecutionLaneTemplate(
        lane=ExecutionLane.UNIVERSAL_LIQUIDITY_AGGREGATOR_ROUTER,
        status=AdapterStatus.ENABLED,
        description="Liquidity-state aggregation plus policy-gated LP mutation planning.",
        adapter_categories=(AdapterCategory.LIQUIDITY,),
        adapter_keys=(
            adapter_key(AdapterCategory.LIQUIDITY, "UniswapV3Liquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "UniswapV4Liquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "BalancerLiquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "CurveLiquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "MorphoLiquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "MetaMorphoVaults"),
            adapter_key(AdapterCategory.LIQUIDITY, "AaveLiquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "NativeCreditLiquidity"),
        ),
        coordinator_modules=(
            "coordinator/src/strategies/v4-hooks.ts",
            "coordinator/src/strategies/liquidation/monitor.ts",
        ),
        solver_modules=(
            "driver.execution.morpho_lp_adapter",
            "driver.execution.metamorpho_v1_adapter",
        ),
        policy_gates=(
            "strategy-specific LP mutation allowlist",
            "per-token and per-pool exposure cap",
            "same-transaction unwind or explicit TTL close plan",
            "post-unwind inventory neutrality",
            "emergency revoke and withdraw path",
        ),
        notes=(
            "The universal lane may rank liquidity and emit bounded LP mutation intents; it does not "
            "emit executable LP mutation calldata unless a lower strategy lane attaches caps and unwind proofs."
        ),
    ),
    ExecutionLaneTemplate(
        lane=ExecutionLane.ARB_EXECUTOR,
        status=AdapterStatus.ENABLED,
        description="Native multi-hop arbitrage executor over sealed degenbot pool state.",
        adapter_categories=(
            AdapterCategory.SWAP,
            AdapterCategory.FLASH,
        ),
        adapter_keys=(
            adapter_key(AdapterCategory.SWAP, "UniswapV2"),
            adapter_key(AdapterCategory.SWAP, "UniswapV3"),
            adapter_key(AdapterCategory.SWAP, "Camelot"),
            adapter_key(AdapterCategory.SWAP, "CurveNG"),
            adapter_key(AdapterCategory.SWAP, "DodoPmm"),
            adapter_key(AdapterCategory.FLASH, "AaveV3Flash"),
            adapter_key(AdapterCategory.FLASH, "MorphoFlash"),
        ),
        coordinator_modules=(
            "coordinator/src/strategies/native-arb.ts",
            "coordinator/src/decision/engine.ts",
        ),
        solver_modules=("driver.execution.degenbot_ipc",),
        contract_modules=("contracts/src/Executor.sol",),
        policy_gates=(
            "state root provenance",
            "route hash sealing",
            "atomic profit invariant",
            "private submission preference",
        ),
    ),
    ExecutionLaneTemplate(
        lane=ExecutionLane.INTENT_EXECUTOR,
        status=AdapterStatus.ENABLED,
        description="Intent and solver-order lane for CoW, UniswapX, and private settlement feeds.",
        adapter_categories=(
            AdapterCategory.SWAP,
            AdapterCategory.FLASH,
        ),
        adapter_keys=(
            adapter_key(AdapterCategory.SWAP, "UniswapX"),
            adapter_key(AdapterCategory.SWAP, "AggregatorV6"),
            adapter_key(AdapterCategory.FLASH, "CowFlashLoanRouter"),
        ),
        coordinator_modules=(
            "coordinator/src/intent/flow.ts",
            "coordinator/src/feeds/cow-orderbook.ts",
            "coordinator/src/feeds/uniswapx-orders.ts",
        ),
        solver_modules=(
            "driver.orderbook.client",
            "driver.quote_engine.http_client",
        ),
        contract_modules=("contracts/src/Executor.sol",),
        policy_gates=(
            "solver competition bounds",
            "signature domain verification",
            "settlement receiver allowlist",
            "non-replayable settlement id",
            "CoW chained-hash replay root",
            "UniswapX reactor transient sender gate",
        ),
        notes="Scoped executable lane backed by CoW receiver/replay tests and UniswapX callback fork coverage.",
    ),
    ExecutionLaneTemplate(
        lane=ExecutionLane.JIT_EXECUTOR,
        status=AdapterStatus.ENABLED,
        description="Self-controlled JIT liquidity lane for concentrated-liquidity opportunities.",
        adapter_categories=(
            AdapterCategory.LIQUIDITY,
            AdapterCategory.SWAP,
        ),
        adapter_keys=(
            adapter_key(AdapterCategory.LIQUIDITY, "UniswapV3Liquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "UniswapV4Liquidity"),
            adapter_key(AdapterCategory.SWAP, "UniswapV3"),
            adapter_key(AdapterCategory.SWAP, "UniswapV4"),
            adapter_key(AdapterCategory.SWAP, "Camelot"),
        ),
        coordinator_modules=(
            "coordinator/src/strategies/v4-hooks.ts",
            "coordinator/src/strategies/amm-economics.ts",
            "coordinator/src/signals/detectors/sequencer-feed.ts",
        ),
        solver_modules=("driver.execution.degenbot_ipc",),
        contract_modules=("contracts/src/Executor.sol",),
        policy_gates=(
            "self-controlled or solver-owned trigger source",
            "external trigger ordering proof when trigger source is not solver-owned",
            "flash-funded mint/swap/burn/collect envelope",
            "inventory-neutral unwind",
            "bounded tick exposure",
            "private bundle only",
            "post-unwind inventory neutrality",
        ),
        notes=(
            "Enabled for self-controlled, solver-owned, and ordering-proofed external-trigger JIT under "
            "scoped readiness evidence."
        ),
    ),
    ExecutionLaneTemplate(
        lane=ExecutionLane.LIQUIDATION_EXECUTOR,
        status=AdapterStatus.ENABLED,
        description="Collateral/liability resolution lane with deterministic flash funding.",
        adapter_categories=(
            AdapterCategory.LIQUIDITY,
            AdapterCategory.FLASH,
            AdapterCategory.SWAP,
        ),
        adapter_keys=(
            adapter_key(AdapterCategory.LIQUIDITY, "MorphoLiquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "AaveLiquidity"),
            adapter_key(AdapterCategory.FLASH, "MorphoFlash"),
            adapter_key(AdapterCategory.FLASH, "AaveV3Flash"),
            adapter_key(AdapterCategory.SWAP, "AggregatorV6"),
        ),
        coordinator_modules=(
            "coordinator/src/strategies/liquidation/executor.ts",
            "coordinator/src/strategies/liquidation/simulator.ts",
            "coordinator/src/submission/liquidation-policy.ts",
        ),
        solver_modules=(
            "driver.execution.morpho_lp_adapter",
            "driver.execution.morpho_preliquidation_adapter",
            "driver.execution.aave_v3_flashloan_adapter",
        ),
        contract_modules=("contracts/src/Executor.sol",),
        policy_gates=(
            "health-factor proof",
            "oracle freshness proof",
            "flash repay invariant",
            "bad-debt avoidance",
        ),
    ),
    ExecutionLaneTemplate(
        lane=ExecutionLane.SANDWICH_EXECUTOR,
        status=AdapterStatus.ENABLED,
        description="Atomic oracle-update sandwich lane over flash-funded Executor.executeNativeArb.",
        adapter_categories=(AdapterCategory.SWAP,),
        adapter_keys=(
            adapter_key(AdapterCategory.SWAP, "UniswapV2"),
            adapter_key(AdapterCategory.SWAP, "UniswapV3"),
            adapter_key(AdapterCategory.SWAP, "Camelot"),
        ),
        coordinator_modules=(
            "coordinator/src/strategies/oracle-sandwich/orchestrator.ts",
            "coordinator/src/strategies/oracle-sandwich/leg-builder.ts",
            "coordinator/src/signals/actions/dispatch-oracle-sandwich.ts",
        ),
        solver_modules=("driver.execution.degenbot_ipc",),
        contract_modules=("contracts/src/Executor.sol",),
        policy_gates=(
            "offensive variant enable map defaults on",
            "flash-funded executeNativeArb envelope",
            "single-transaction round trip",
            "profit floor after flash premium",
            "private or Timeboost submission preference",
            "global pause kill switch",
        ),
        notes=(
            "Enabled for offensive S-1/S-2/S-3/S-4 variants and S-5 oracle-update flows when calldata "
            "targets executeNativeArb or a solver/filler atomic callback."
        ),
    ),
    ExecutionLaneTemplate(
        lane=ExecutionLane.MEV_PROTECTION_EXECUTOR,
        status=AdapterStatus.ENABLED,
        description="Private-routing, replay-defense, and adverse-selection guard lane.",
        adapter_categories=(AdapterCategory.SWAP,),
        adapter_keys=(
            adapter_key(AdapterCategory.SWAP, "AggregatorV6"),
            adapter_key(AdapterCategory.SWAP, "RFQAndCrossChainAggregators"),
        ),
        coordinator_modules=(
            "coordinator/src/strategies/mev-protection.ts",
            "coordinator/src/submission/dispatch.ts",
            "coordinator/src/submission/lane-router.ts",
        ),
        solver_modules=("driver.signing.eip712",),
        contract_modules=("contracts/src/Executor.sol",),
        policy_gates=(
            "private submission first",
            "replay domain separation",
            "route expiry",
            "divergence cutover",
        ),
    ),
)
