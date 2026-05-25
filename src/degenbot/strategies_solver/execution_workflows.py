"""Machine-readable strategy execution workflow catalog.

The catalog is intentionally descriptive rather than executable. It binds each
strategy name to the code modules that detect, plan, encode, submit, and realize
profit. Tests use it as a drift guard so a strategy cannot be called "enabled"
without documented callback encoding, stop policy, and validation coverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WorkflowStatus(StrEnum):
    """Operational status for a strategy workflow."""

    EXECUTABLE = "executable"
    EXTERNAL_FORWARD = "external_forward"
    GATED_EXPLICIT = "gated_explicit"


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """One ordered step in a strategy workflow."""

    order: int
    name: str
    code_refs: tuple[str, ...]
    validation: str


@dataclass(frozen=True, slots=True)
class StrategyExecutionWorkflow:
    """End-to-end execution workflow for one strategy or strategy lane."""

    workflow_id: str
    strategy_name: str
    status: WorkflowStatus
    decision_kinds: tuple[str, ...]
    signal_sources: tuple[str, ...]
    trigger_modules: tuple[str, ...]
    planner_modules: tuple[str, ...]
    calldata_builders: tuple[str, ...]
    submission_modules: tuple[str, ...]
    contract_entrypoints: tuple[str, ...]
    callback_entrypoints: tuple[str, ...]
    flash_callback_encoding: str
    profit_extraction: str
    no_silent_stop_policy: str
    happy_path_tests: tuple[str, ...]
    revert_guard_tests: tuple[str, ...]
    steps: tuple[WorkflowStep, ...]

    @property
    def is_live(self) -> bool:
        """True when the workflow can submit or forward executable work today."""
        return self.status in {WorkflowStatus.EXECUTABLE, WorkflowStatus.EXTERNAL_FORWARD}


EXECUTION_WORKFLOWS: tuple[StrategyExecutionWorkflow, ...] = (
    StrategyExecutionWorkflow(
        workflow_id="native_arb",
        strategy_name="Native arbitrage / Pick D3",
        status=WorkflowStatus.EXECUTABLE,
        decision_kinds=("native_arb",),
        signal_sources=("vendor/degenbot/rust/src/lib.rs", "vendor/degenbot/src/degenbot/connection/ipc.py"),
        trigger_modules=("coordinator/src/index.ts", "coordinator/src/decision/engine.ts"),
        planner_modules=("coordinator/src/strategies/native-arb.ts", "coordinator/src/router/encode.ts"),
        calldata_builders=("coordinator/src/strategies/native-arb.ts",),
        submission_modules=("coordinator/src/submission/submitter.ts",),
        contract_entrypoints=("contracts/src/executors/Executor.sol::executeNativeArb",),
        callback_entrypoints=(
            "contracts/src/executors/Executor.sol::executeOperation",
            "contracts/src/executors/Executor.sol::onMorphoFlashLoan",
            "contracts/src/executors/Executor.sol::onFlashLoan",
            "contracts/src/executors/Executor.sol::uniswapV3FlashCallback",
        ),
        flash_callback_encoding="Executor encodes userData as abi.encode(uint8(0), abi.encode(NativeArbParams)).",
        profit_extraction=(
            "Executor retains flashToken surplus after lender repayment; _handleNativeArb requires "
            "balanceAfter >= balanceBefore + premium + minProfit."
        ),
        no_silent_stop_policy=(
            "Decision pass reasons are explicit; buildParams throws on zero flash amount or invalid route; "
            "contract reverts on path, callback, profit, and whitelist failures."
        ),
        happy_path_tests=(
            "contracts/test/unit/ExecutorStrategies.t.sol",
            "coordinator/src/strategies/native-arb.test.ts",
        ),
        revert_guard_tests=(
            "contracts/test/unit/ExecutorStrategies.t.sol",
            "coordinator/src/flash/source-router.test.ts",
        ),
        steps=(
            WorkflowStep(
                1,
                "Detect degenbot opportunity",
                ("vendor/degenbot/rust/src/lib.rs", "vendor/degenbot/src/degenbot/connection/ipc.py"),
                "Opportunity carries flashToken, flashAmount, route, and estimated profit.",
            ),
            WorkflowStep(
                2,
                "Route by precedence",
                ("coordinator/src/index.ts", "coordinator/src/decision/engine.ts"),
                "Kill switch, zero-flash, quote superiority, and Sandoo gates produce a routed decision.",
            ),
            WorkflowStep(
                3,
                "Build Executor calldata",
                ("coordinator/src/strategies/native-arb.ts", "coordinator/src/router/encode.ts"),
                "Every swap step is encoded with router target, token deltas, deadline, and min-out.",
            ),
            WorkflowStep(
                4,
                "Submit transaction",
                ("coordinator/src/strategies/native-arb.ts", "coordinator/src/submission/submitter.ts"),
                "Submitter broadcasts a direct tx when MEV_EXECUTOR=ts; rust mode submits a Plan over IPC.",
            ),
            WorkflowStep(
                5,
                "Execute flash callback and extract profit",
                ("contracts/src/executors/Executor.sol",),
                "Strategy id 0 dispatches _handleNativeArb; profit is retained as flashToken surplus.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="internal_match",
        strategy_name="Internal match / Pick A",
        status=WorkflowStatus.EXECUTABLE,
        decision_kinds=("internal_match",),
        signal_sources=("coordinator/src/feeds/index.ts", "coordinator/src/matching/unified-queue.ts"),
        trigger_modules=("coordinator/src/index.ts", "coordinator/src/decision/engine.ts"),
        planner_modules=("coordinator/src/matching/internal-matcher.ts", "coordinator/src/matching/encoder.ts"),
        calldata_builders=("coordinator/src/strategies/internal-match.ts", "coordinator/src/matching/encoder.ts"),
        submission_modules=("coordinator/src/submission/submitter.ts",),
        contract_entrypoints=("contracts/src/executors/Executor.sol::matchInternal",),
        callback_entrypoints=(
            "contracts/src/executors/Executor.sol::executeOperation",
            "contracts/src/executors/Executor.sol::reactorCallback",
            "contracts/src/executors/Executor.sol::transferToSettlement",
        ),
        flash_callback_encoding="Executor encodes userData as abi.encode(uint8(1), abi.encode(MatchParams)).",
        profit_extraction=(
            "Executor checks expected inflows, pays Settlement through transferToSettlement, then retains "
            "flashToken surplus after lender repayment."
        ),
        no_silent_stop_policy=(
            "Missing source orders, encoder failures, and dispatch outcomes are logged and counted; "
            "contract reverts on bad inflows, wrong reactor, settlement failure, and insufficient profit."
        ),
        happy_path_tests=(
            "contracts/test/unit/ExecutorStrategies.t.sol",
            "coordinator/src/strategies/internal-match.test.ts",
            "coordinator/src/matching/encoder.test.ts",
        ),
        revert_guard_tests=(
            "contracts/test/unit/ExecutorStrategies.t.sol",
            "contracts/test/unit/Executor_TransferToSettlement.t.sol",
            "contracts/test/unit/ExecutorUniswapXFill.t.sol",
        ),
        steps=(
            WorkflowStep(
                1,
                "Detect intent candidates",
                ("coordinator/src/feeds/index.ts", "coordinator/src/feeds/sink.ts"),
                "CoW and UniswapX feed events are normalized into the unified matching queue.",
            ),
            WorkflowStep(
                2,
                "Select best match",
                ("coordinator/src/decision/engine.ts", "coordinator/src/matching/internal-matcher.ts"),
                "Internal match wins precedence when source orders and price compatibility are present.",
            ),
            WorkflowStep(
                3,
                "Encode CoW and UniswapX legs",
                ("coordinator/src/matching/encoder.ts",),
                "CoW settle includes transferToSettlement; UniswapX uses executeBatchWithCallback.",
            ),
            WorkflowStep(
                4,
                "Submit matchInternal",
                ("coordinator/src/strategies/internal-match.ts", "coordinator/src/submission/submitter.ts"),
                "Wrapper calldata targets Executor.matchInternal with non-zero flash amount.",
            ),
            WorkflowStep(
                5,
                "Settle and realize surplus",
                ("contracts/src/executors/Executor.sol",),
                "Strategy id 1 dispatches _handleMatchInternal; profit gate runs before repayment approval.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="four_leg",
        strategy_name="Four-leg composition / Pick B",
        status=WorkflowStatus.EXECUTABLE,
        decision_kinds=("four_leg",),
        signal_sources=("vendor/degenbot/rust/src/lib.rs", "coordinator/src/feeds/index.ts"),
        trigger_modules=("coordinator/src/index.ts", "coordinator/src/decision/engine.ts"),
        planner_modules=("coordinator/src/strategies/four-leg.ts",),
        calldata_builders=("coordinator/src/strategies/four-leg.ts", "coordinator/src/matching/encoder.ts"),
        submission_modules=("coordinator/src/submission/submitter.ts",),
        contract_entrypoints=("contracts/src/executors/Executor.sol::composeFourLeg",),
        callback_entrypoints=(
            "contracts/src/executors/Executor.sol::executeOperation",
            "contracts/src/executors/Executor.sol::onMorphoFlashLoan",
            "contracts/src/executors/Executor.sol::onFlashLoan",
            "contracts/src/executors/Executor.sol::reactorCallback",
            "contracts/src/executors/Executor.sol::transferToSettlement",
        ),
        flash_callback_encoding="Executor encodes userData as abi.encode(uint8(2), abi.encode(ComposeParams)).",
        profit_extraction=(
            "Executor runs Across, swap, CoW, and UniswapX legs, then retains flashToken surplus after "
            "premium and minProfit are covered."
        ),
        no_silent_stop_policy=(
            "Preflight rejects incomplete opaque legs and non-positive economics before a decision is emitted; "
            "contract wraps failed legs with leg numbers and reverts on profit shortfall."
        ),
        happy_path_tests=(
            "contracts/test/unit/ExecutorStrategies.t.sol",
            "contracts/test/fork/ExecutorFourLegFlashProviders.fork.t.sol",
            "coordinator/src/strategies/four-leg.test.ts",
        ),
        revert_guard_tests=(
            "contracts/test/unit/ExecutorStrategies.t.sol",
            "coordinator/src/strategies/four-leg.test.ts",
        ),
        steps=(
            WorkflowStep(
                1,
                "Detect composable opportunity",
                ("coordinator/src/decision/engine.ts", "coordinator/src/strategies/four-leg.ts"),
                "DecisionEngine asks FourLegStrategy.preflight for a complete plan.",
            ),
            WorkflowStep(
                2,
                "Validate all four legs",
                ("coordinator/src/strategies/four-leg.ts",),
                "Across, arb swaps, CoW, UniswapX, flash amount, and expected profit must be non-empty.",
            ),
            WorkflowStep(
                3,
                "Build ComposeParams",
                ("coordinator/src/strategies/four-leg.ts", "coordinator/src/flash/source-router.ts"),
                "Flash route is direct Executor-compatible Aave/Morpho/ERC3156/UniV3.",
            ),
            WorkflowStep(
                4,
                "Submit composeFourLeg",
                ("coordinator/src/strategies/four-leg.ts", "coordinator/src/submission/submitter.ts"),
                "Submitter sends one atomic transaction.",
            ),
            WorkflowStep(
                5,
                "Execute callback and settle profit",
                ("contracts/src/executors/Executor.sol",),
                "Strategy id 2 dispatches _handleComposeFourLeg; final balance delta pays premium and profit.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="uniswapx_filler",
        strategy_name="UniswapX filler",
        status=WorkflowStatus.EXECUTABLE,
        decision_kinds=(),
        signal_sources=("coordinator/src/feeds/uniswapx-orders.ts",),
        trigger_modules=("coordinator/src/index.ts",),
        planner_modules=("coordinator/src/strategies/filler-bid.ts", "coordinator/src/quotes/index.ts"),
        calldata_builders=("coordinator/src/strategies/filler-bid.ts",),
        submission_modules=("coordinator/src/submission/submitter.ts",),
        contract_entrypoints=("contracts/src/executors/Executor.sol::executeUniswapXFill",),
        callback_entrypoints=("contracts/src/executors/Executor.sol::reactorCallback",),
        flash_callback_encoding="No flash loan; callbackData is abi.encode(SwapStep[], expectedSelf, deadline).",
        profit_extraction=(
            "Quote surplus is carried as expectedProfitWei; Executor approves reactor outputs and the submitter "
            "records the direct transaction result."
        ),
        no_silent_stop_policy=(
            "Screening returns explicit reasons for unsupported chain, reactor, expiry, amounts, signature, "
            "or quote failure; dispatch throws on missing quote or unwhitelisted router."
        ),
        happy_path_tests=(
            "contracts/test/unit/ExecutorUniswapXFill.t.sol",
            "coordinator/src/strategies/filler-bid.test.ts",
        ),
        revert_guard_tests=(
            "contracts/test/unit/ExecutorUniswapXFill.t.sol",
            "coordinator/src/strategies/filler-bid.test.ts",
        ),
        steps=(
            WorkflowStep(
                1,
                "Detect UniswapX order",
                ("coordinator/src/feeds/uniswapx-orders.ts", "coordinator/src/index.ts"),
                "Feed sink screens orders when STRATEGY_FILLER_BID_ENABLED is set.",
            ),
            WorkflowStep(
                2,
                "Quote fill",
                ("coordinator/src/strategies/filler-bid.ts", "coordinator/src/quotes/index.ts"),
                "Best quote must exceed the order output floor.",
            ),
            WorkflowStep(
                3,
                "Encode reactor callback",
                ("coordinator/src/strategies/filler-bid.ts",),
                "executeBatchWithCallback and Executor.executeUniswapXFill are both encoded.",
            ),
            WorkflowStep(
                4,
                "Submit fill",
                ("coordinator/src/strategies/filler-bid.ts", "coordinator/src/submission/submitter.ts"),
                "Direct tx targets Executor.executeUniswapXFill.",
            ),
            WorkflowStep(
                5,
                "Approve outputs and record surplus",
                ("contracts/src/executors/Executor.sol",),
                "reactorCallback aggregates output approvals by token and emits UniswapXFillExecuted.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="liquidation",
        strategy_name="Aave liquidation through Balancer V2 flash",
        status=WorkflowStatus.EXECUTABLE,
        decision_kinds=(),
        signal_sources=("coordinator/src/strategies/liquidation/monitor.ts",),
        trigger_modules=("coordinator/src/strategies/liquidation/index.ts",),
        planner_modules=(
            "coordinator/src/strategies/liquidation/simulator.ts",
            "coordinator/src/strategies/liquidation/executor.ts",
        ),
        calldata_builders=("coordinator/src/strategies/liquidation/executor.ts",),
        submission_modules=("coordinator/src/strategies/liquidation/executor.ts",),
        contract_entrypoints=("contracts/src/executors/LiquidationExecutor.sol::liquidate",),
        callback_entrypoints=("contracts/src/executors/LiquidationExecutor.sol::receiveFlashLoan",),
        flash_callback_encoding=(
            "LiquidationExecutor encodes Balancer userData as "
            "abi.encode(collateral, debt, borrower, debtAmount, swapPath, amountOutMinimum, minNetProfit, deadline)."
        ),
        profit_extraction=(
            "Collateral is liquidated, swapped back to debt, Balancer is repaid, and netProfit is emitted in "
            "Liquidated for the post-mortem indexer."
        ),
        no_silent_stop_policy=(
            "Monitor, simulator, preflight, submit, and receipt outcomes are all explicit TickOutcome values; "
            "zero amountOutMinimum and expired deadlines are rejected before broadcast."
        ),
        happy_path_tests=(
            "contracts/test/unit/LiquidationExecutor.t.sol",
            "contracts/test/unit/LiquidationExecutor.delta.t.sol",
            "coordinator/src/strategies/liquidation/index.test.ts",
            "coordinator/src/strategies/liquidation/executor.test.ts",
        ),
        revert_guard_tests=(
            "contracts/test/unit/LiquidationExecutor.t.sol",
            "contracts/test/unit/LiquidationExecutor.delta.t.sol",
            "coordinator/src/strategies/liquidation/executor.test.ts",
        ),
        steps=(
            WorkflowStep(
                1,
                "Index borrower risk",
                ("coordinator/src/strategies/liquidation/monitor.ts",),
                "Borrow, repay, and liquidation logs update the position index.",
            ),
            WorkflowStep(
                2,
                "Simulate profitability",
                ("coordinator/src/strategies/liquidation/simulator.ts",),
                "Aave config, oracle prices, quoter output, gas, blob floor, and Kairos fee are included.",
            ),
            WorkflowStep(
                3,
                "Build and preflight calldata",
                ("coordinator/src/strategies/liquidation/executor.ts",),
                "liquidate(...) calldata is eth_call preflighted with a stable deadline.",
            ),
            WorkflowStep(
                4,
                "Submit liquidation",
                ("coordinator/src/strategies/liquidation/index.ts",),
                "Daemon submits once per in-flight borrower and waits for receipt.",
            ),
            WorkflowStep(
                5,
                "Run Balancer callback and emit profit",
                ("contracts/src/executors/LiquidationExecutor.sol",),
                "receiveFlashLoan validates lender and plan hash before Aave liquidation and swap.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="oracle_sandwich",
        strategy_name="Oracle-update sandwich S-1/S-2/S-3/S-4/S-5",
        status=WorkflowStatus.EXECUTABLE,
        decision_kinds=(),
        signal_sources=("engine/src/monitor/sequencer_feed.rs", "coordinator/src/signals/bus.ts"),
        trigger_modules=("coordinator/src/index.ts", "coordinator/src/strategies/oracle-sandwich/orchestrator.ts"),
        planner_modules=(
            "coordinator/src/strategies/oracle-sandwich/profit-estimator.ts",
            "coordinator/src/strategies/oracle-sandwich/leg-builder.ts",
            "coordinator/src/strategies/sandwich/offensive-policy.ts",
        ),
        calldata_builders=("coordinator/src/strategies/oracle-sandwich/leg-builder.ts",),
        submission_modules=("coordinator/src/signals/actions/dispatch-oracle-sandwich.ts",),
        contract_entrypoints=("contracts/src/executors/Executor.sol::executeNativeArb",),
        callback_entrypoints=(
            "contracts/src/executors/Executor.sol::executeOperation",
            "contracts/src/executors/Executor.sol::_handleNativeArb",
        ),
        flash_callback_encoding="Oracle sandwich uses executeNativeArb, therefore strategy id 0 callback encoding.",
        profit_extraction=(
            "The single atomic swap chain must end in flashToken and pass Executor's minProfit balance-delta gate."
        ),
        no_silent_stop_policy=(
            "Orchestrator skip reasons are explicit; legacy two-step sinks warn and count metrics; "
            "execution emits one direct tx or one Plan with requirePreflight=true."
        ),
        happy_path_tests=(
            "coordinator/src/strategies/oracle-sandwich/orchestrator.test.ts",
            "coordinator/src/strategies/oracle-sandwich/leg-builder.test.ts",
            "coordinator/src/signals/actions/dispatch-oracle-sandwich.test.ts",
        ),
        revert_guard_tests=(
            "coordinator/src/strategies/oracle-sandwich/leg-builder.test.ts",
            "contracts/test/unit/ExecutorStrategies.t.sol",
        ),
        steps=(
            WorkflowStep(
                1,
                "Detect timing signal",
                ("engine/src/monitor/sequencer_feed.rs", "coordinator/src/signals/bus.ts"),
                "Sequencer candidates and oracle gap signals are correlated by the orchestrator.",
            ),
            WorkflowStep(
                2,
                "Resolve pool and estimate edge",
                ("coordinator/src/strategies/oracle-sandwich/orchestrator.ts",),
                "Static pool mapping, reserves, gap, and timeboost inputs decide whether to build.",
            ),
            WorkflowStep(
                3,
                "Build atomic executeNativeArb",
                ("coordinator/src/strategies/oracle-sandwich/leg-builder.ts",),
                "Outer selector is Executor.executeNativeArb; inner router calls stay inside SwapStep[].",
            ),
            WorkflowStep(
                4,
                "Submit direct tx or engine Plan",
                ("coordinator/src/signals/actions/dispatch-oracle-sandwich.ts",),
                "MEV_EXECUTOR selects direct TS submit or Rust Plan with preflight required.",
            ),
            WorkflowStep(
                5,
                "Profit gate",
                ("contracts/src/executors/Executor.sol",),
                "The native-arb handler repays flash and retains surplus only if minProfit is met.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="cow_flash_router",
        strategy_name="CoW FlashLoanRouter chained settlement",
        status=WorkflowStatus.GATED_EXPLICIT,
        decision_kinds=(),
        signal_sources=("coordinator/src/feeds/cow-competition.ts",),
        trigger_modules=("contracts/src/executors/Executor.sol::triggerCoWFlashLoanRouter",),
        planner_modules=("vendor/degenbot/src/degenbot/auction_build.py", "coordinator/src/strategies/cow-quoter.ts"),
        calldata_builders=("contracts/src/interfaces/IExecutor.sol",),
        submission_modules=(),
        contract_entrypoints=("contracts/src/executors/Executor.sol::triggerCoWFlashLoanRouter",),
        callback_entrypoints=("contracts/src/executors/Executor.sol::borrowerCallBack",),
        flash_callback_encoding=(
            "Router rounds encode abi.encode(round, totalRounds, expectedRoot, nextLoanCalldata, "
            "settlementCalldata); final settlementCalldata is abi.encode(uint8(1|2), bytes params)."
        ),
        profit_extraction=(
            "Final round dispatches MatchInternal or ComposeFourLeg with synthetic zero flash arrays; "
            "profit is the post-settlement balance delta over p.minProfit."
        ),
        no_silent_stop_policy=(
            "No coordinator DecisionKind routes to this contract start today; a strategist-supplied trigger must "
            "provide root, round calldata, and deadline. Bad rounds, root mismatch, forward failure, and invalid "
            "strategy ids revert with typed errors."
        ),
        happy_path_tests=(
            "contracts/test/unit/ExecutorCoWFlashRouter.t.sol",
            "contracts/test/unit/ExecutorCoWFlashRouterStart.t.sol",
        ),
        revert_guard_tests=(
            "contracts/test/unit/ExecutorCoWFlashRouter.t.sol",
            "contracts/test/unit/ExecutorCoWFlashRouterStart.t.sol",
        ),
        steps=(
            WorkflowStep(
                1,
                "Detect auction",
                ("coordinator/src/feeds/cow-competition.ts", "coordinator/src/index.ts"),
                "CoW batch feed fans out orders and forwards quote-eligible batches.",
            ),
            WorkflowStep(
                2,
                "Build quote/provenance view",
                ("coordinator/src/strategies/cow-quoter.ts", "vendor/degenbot/src/degenbot/auction_build.py"),
                "TS prices eligible orders without signing a solver solution or posting capital.",
            ),
            WorkflowStep(
                3,
                "Commit router root",
                ("contracts/src/interfaces/IExecutor.sol",),
                "Strategist supplies expectedRoot, totalRounds, initialLoanCalldata, and deadline.",
            ),
            WorkflowStep(
                4,
                "Walk Router callbacks",
                ("contracts/src/executors/Executor.sol",),
                "borrowerCallBack advances cumulative hash once per round and forwards when needed.",
            ),
            WorkflowStep(
                5,
                "Dispatch final settlement",
                ("contracts/src/executors/Executor.sol",),
                "Final hash match dispatches strategy id 1 or 2; invalid ids and hash mismatch revert.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="d3_cow_quote",
        strategy_name="D3 CoW quote/provenance filter",
        status=WorkflowStatus.EXTERNAL_FORWARD,
        decision_kinds=(),
        signal_sources=("coordinator/src/feeds/cow-competition.ts",),
        trigger_modules=("coordinator/src/index.ts", "coordinator/src/strategies/d3-filter.ts"),
        planner_modules=("coordinator/src/strategies/d3-filter.ts", "coordinator/src/strategies/cow-quoter.ts"),
        calldata_builders=("vendor/degenbot/src/degenbot/auction_build.py",),
        submission_modules=("coordinator/src/strategies/cow-quoter.ts", "vendor/degenbot/src/degenbot/server.py"),
        contract_entrypoints=(),
        callback_entrypoints=(),
        flash_callback_encoding="No direct on-chain callback; CoW posture is quote-only with no bonded solver tx.",
        profit_extraction=(
            "No capital moves in this lane. Profit is downstream optionality from internal matching, "
            "user-intent flow, or UniswapX/native-arb routes that consume the quote/provenance signal."
        ),
        no_silent_stop_policy=(
            "Expired, invalid, peer-matchable, and AMM-routed orders receive explicit classifications; "
            "quote failures are surfaced as rejected quote results instead of silent solver non-submission."
        ),
        happy_path_tests=(
            "coordinator/src/strategies/d3-filter.test.ts",
            "coordinator/src/strategies/cow-quoter.test.ts",
            "solver/driver/tests/test_auction_build.py",
        ),
        revert_guard_tests=("coordinator/src/strategies/d3-filter.test.ts",),
        steps=(
            WorkflowStep(
                1,
                "Observe CoW batch",
                ("coordinator/src/index.ts", "coordinator/src/feeds/cow-competition.ts"),
                "Batch feed delivers orders to maybeRunCowAuctionStrategies.",
            ),
            WorkflowStep(
                2,
                "Classify order",
                ("coordinator/src/strategies/d3-filter.ts",),
                "Classifier distinguishes AMM-routed, CoW-matchable, expired, and invalid orders.",
            ),
            WorkflowStep(
                3,
                "Price quote-only flow",
                ("coordinator/src/strategies/cow-quoter.ts",),
                "Quote engine prices eligible orders without solver signing, bonds, or inventory.",
            ),
            WorkflowStep(
                4,
                "Record provenance",
                ("vendor/degenbot/src/degenbot/auction_build.py",),
                "Python analysis sidecar can retain auction provenance or reject explicitly; it does not submit "
                "a CoW solver solution.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="morpho_liquidation_decision",
        strategy_name="DecisionKind Morpho Blue liquidation",
        status=WorkflowStatus.EXECUTABLE,
        decision_kinds=("morpho_liquidation",),
        signal_sources=(
            "coordinator/src/decision/engine.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-daemon.ts",
        ),
        trigger_modules=("coordinator/src/index.ts",),
        planner_modules=(
            "coordinator/src/index.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-daemon.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-executor.ts",
        ),
        calldata_builders=(
            "coordinator/src/strategies/liquidation/morpho-blue-calldata.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-executor.ts",
        ),
        submission_modules=(
            "coordinator/src/index.ts",
            "coordinator/src/submission/submitter.ts",
        ),
        contract_entrypoints=("contracts/src/executors/AtomicExecutor.sol::execute",),
        callback_entrypoints=("contracts/src/executors/AtomicExecutor.sol::balancerV3UnlockCallback",),
        flash_callback_encoding=(
            "AtomicExecutor calldata encodes strategy 1, Balancer V3 flash source, loan-token flash amount, "
            "typed Morpho liquidate call, and SwapRouter02 exactInput call."
        ),
        profit_extraction=(
            "AtomicExecutor repays the flash lender, enforces minProfit in the loan token, and leaves surplus "
            "for owner-controlled sweeping."
        ),
        no_silent_stop_policy="dispatchOpportunity logs the Morpho liquidation dispatch explicitly.",
        happy_path_tests=(
            "coordinator/src/decision/engine.test.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-calldata.test.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-executor.test.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-daemon.test.ts",
        ),
        revert_guard_tests=(
            "coordinator/src/decision/engine.test.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-calldata.test.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-executor.test.ts",
            "contracts/test/fork/LiquidationExecutor.morpho.fork.t.sol",
        ),
        steps=(
            WorkflowStep(
                1,
                "Classify Morpho liquidation candidate",
                ("coordinator/src/decision/engine.ts",),
                "DecisionEngine routes MorphoLiquidation payloads to the liquidation decision kind.",
            ),
            WorkflowStep(
                2,
                "Refresh live Morpho state",
                (
                    "coordinator/src/index.ts",
                    "coordinator/src/strategies/liquidation/morpho-blue-daemon.ts",
                ),
                "Dispatcher re-reads pending Morpho market/position state and creates a sourced liquidation signal.",
            ),
            WorkflowStep(
                3,
                "Build AtomicExecutor calldata",
                (
                    "coordinator/src/strategies/liquidation/morpho-blue-calldata.ts",
                    "coordinator/src/strategies/liquidation/morpho-blue-executor.ts",
                ),
                "Calldata contains typed approvals plus exact Morpho Blue liquidation and collateral swap calls.",
            ),
            WorkflowStep(
                4,
                "Simulate exact pending-state calldata",
                ("coordinator/src/strategies/liquidation/morpho-blue-executor.ts",),
                "PendingStateCallSimulator must accept the same calldata that will be submitted.",
            ),
            WorkflowStep(
                5,
                "Submit direct transaction",
                ("coordinator/src/submission/submitter.ts",),
                "Submitter broadcasts the direct tx and records realized loan-token balance deltas.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="jit_liquidity",
        strategy_name="JIT liquidity policy lane",
        status=WorkflowStatus.GATED_EXPLICIT,
        decision_kinds=(),
        signal_sources=("docs/architecture/jit-lp-strategy-design.md",),
        trigger_modules=("solver/driver/adapters/laneadapters/lanes.py",),
        planner_modules=("coordinator/src/strategies/v4-hooks.ts",),
        calldata_builders=(),
        submission_modules=(),
        contract_entrypoints=(),
        callback_entrypoints=(),
        flash_callback_encoding=(
            "No production calldata builder is present; the lane is policy-gated until a JIT-specific "
            "mint/swap/burn/collect builder exists."
        ),
        profit_extraction=(
            "Required future gate: fee capture must exceed flash premium, gas, inventory loss, and minProfit floor."
        ),
        no_silent_stop_policy=(
            "No DecisionKind routes to this lane today; route builders must add tests before any dispatcher can "
            "select it."
        ),
        happy_path_tests=("coordinator/src/strategies/v4-hooks.test.ts",),
        revert_guard_tests=("solver/driver/tests/test_adapter_registry.py",),
        steps=(
            WorkflowStep(
                1,
                "Classify hook and trigger source",
                ("coordinator/src/strategies/v4-hooks.ts",),
                "Unclassified hooks and external triggers without ordering proof are denied.",
            ),
            WorkflowStep(
                2,
                "Stop before submission",
                ("solver/driver/adapters/laneadapters/lanes.py",),
                "No dispatcher owns this lane until executable JIT calldata builders land.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="universal_liquidity_mutation",
        strategy_name="Universal liquidity mutation policy",
        status=WorkflowStatus.GATED_EXPLICIT,
        decision_kinds=(),
        signal_sources=("solver/driver/adapters/liquidityadapters/venues.py",),
        trigger_modules=("solver/driver/adapters/laneadapters/lanes.py",),
        planner_modules=(
            "coordinator/src/strategies/liquidation/monitor.ts",
            "coordinator/src/strategies/v4-hooks.ts",
        ),
        calldata_builders=(),
        submission_modules=(),
        contract_entrypoints=(),
        callback_entrypoints=(),
        flash_callback_encoding="No generic LP mutation callback; lower strategy lane must own concrete calldata.",
        profit_extraction="Lower strategy must define the post-unwind inventory and realized-profit accounting.",
        no_silent_stop_policy=(
            "The universal lane can rank and plan, but cannot emit executable LP mutation calldata without a "
            "lower lane; no dispatcher may select it directly."
        ),
        happy_path_tests=("solver/driver/tests/test_adapter_registry.py",),
        revert_guard_tests=("solver/driver/tests/test_adapter_registry.py",),
        steps=(
            WorkflowStep(
                1,
                "Aggregate liquidity metadata",
                ("solver/driver/adapters/liquidityadapters/venues.py",),
                "Adapters collect venue state and canonical address bindings.",
            ),
            WorkflowStep(
                2,
                "Require lower-lane ownership",
                ("solver/driver/adapters/laneadapters/lanes.py",),
                "Executable LP mutation requires allowlist, caps, unwind plan, and emergency exit.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="cow_user_submit",
        strategy_name="CoW user submission",
        status=WorkflowStatus.GATED_EXPLICIT,
        decision_kinds=("cow_user_submit",),
        signal_sources=("coordinator/src/decision/engine.ts",),
        trigger_modules=("coordinator/src/index.ts",),
        planner_modules=(),
        calldata_builders=(),
        submission_modules=(),
        contract_entrypoints=(),
        callback_entrypoints=(),
        flash_callback_encoding="No executable workflow; DecisionEngine contains a disabled branch.",
        profit_extraction="None until outbound CoW submission pipeline lands.",
        no_silent_stop_policy="Branch is unreachable in DecisionEngine and logs explicitly if ever surfaced.",
        happy_path_tests=("coordinator/src/decision/engine.test.ts",),
        revert_guard_tests=("coordinator/src/decision/engine.test.ts",),
        steps=(
            WorkflowStep(
                1,
                "Stop before decision emission",
                ("coordinator/src/decision/engine.ts",),
                "The branch is hard-disabled; no transaction can be submitted accidentally.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="across_fill",
        strategy_name="Across fill",
        status=WorkflowStatus.GATED_EXPLICIT,
        decision_kinds=("across_fill",),
        signal_sources=("coordinator/src/feeds/index.ts",),
        trigger_modules=("coordinator/src/decision/engine.ts", "coordinator/src/index.ts"),
        planner_modules=("coordinator/src/strategies/four-leg.ts",),
        calldata_builders=(),
        submission_modules=(),
        contract_entrypoints=(),
        callback_entrypoints=(),
        flash_callback_encoding="Across is only executable as part of a complete composeFourLeg plan today.",
        profit_extraction="Standalone Across fill has no production profit extraction path.",
        no_silent_stop_policy="Feed sink and dispatch path log unsupported or gated Across decisions explicitly.",
        happy_path_tests=("coordinator/src/decision/engine.test.ts", "coordinator/src/strategies/four-leg.test.ts"),
        revert_guard_tests=("coordinator/src/decision/engine.test.ts",),
        steps=(
            WorkflowStep(
                1,
                "Receive Across intent",
                ("coordinator/src/feeds/sink.ts",),
                "Queue feed sink records unsupported until a lower strategy consumes the intent.",
            ),
            WorkflowStep(
                2,
                "Require four-leg plan",
                ("coordinator/src/strategies/four-leg.ts",),
                "Across calldata must be non-empty inside a complete ComposeParams plan.",
            ),
        ),
    ),
    StrategyExecutionWorkflow(
        workflow_id="launch_sniper",
        strategy_name="Launch sniper / JB daemon",
        status=WorkflowStatus.GATED_EXPLICIT,
        decision_kinds=("launch_sniper",),
        signal_sources=("docs/architecture/jaredbot-mev-playbook.md",),
        trigger_modules=("coordinator/src/index.ts",),
        planner_modules=(),
        calldata_builders=(),
        submission_modules=(),
        contract_entrypoints=(),
        callback_entrypoints=(),
        flash_callback_encoding="No production launch-sniper calldata is routed through Executor.",
        profit_extraction="None in this coordinator until a dedicated ADR and builder land.",
        no_silent_stop_policy="dispatchOpportunity logs launch_sniper as handled externally; no tx is emitted here.",
        happy_path_tests=("solver/driver/tests/test_adapter_registry.py",),
        revert_guard_tests=("solver/driver/tests/test_adapter_registry.py",),
        steps=(
            WorkflowStep(
                1,
                "Do not route through core coordinator",
                ("coordinator/src/index.ts",),
                "The core coordinator treats this as an external JB daemon surface.",
            ),
        ),
    ),
)


_WORKFLOWS_BY_ID = {workflow.workflow_id: workflow for workflow in EXECUTION_WORKFLOWS}


def workflow_for_id(workflow_id: str) -> StrategyExecutionWorkflow:
    """Return one workflow by id."""
    try:
        return _WORKFLOWS_BY_ID[workflow_id]
    except KeyError as exc:
        raise KeyError(f"unknown execution workflow {workflow_id!r}") from exc


def workflows_for_decision_kind(decision_kind: str) -> tuple[StrategyExecutionWorkflow, ...]:
    """Return all workflows that document one DecisionKind."""
    return tuple(workflow for workflow in EXECUTION_WORKFLOWS if decision_kind in workflow.decision_kinds)
