"""Competitive strategy intelligence profiles.

The profiles complement ``execution_workflows.py``. Execution workflows prove
how a route runs; these profiles explain why the route exists, which resources
it consumes, where the edge comes from, and which blockers still prevent
production routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BlockerStatus(StrEnum):
    """Readiness state for competitive strategy execution."""

    NONE = "none"
    EXPLICIT_GATE = "explicit_gate"


@dataclass(frozen=True, slots=True)
class StrategyBlocker:
    """A blocker with concrete remediation and proof anchors."""

    description: str
    remediation: str
    owner_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    blocks_mainnet: bool = False


@dataclass(frozen=True, slots=True)
class StrategyIntelligenceProfile:
    """Objective, mechanics, edge, latency, and resource plan for one workflow."""

    workflow_id: str
    objective: str
    execution_choice: str
    logic: str
    mechanics: tuple[str, ...]
    competitive_advantage: tuple[str, ...]
    latency_posture: str
    resource_utilization: tuple[str, ...]
    profitability_controls: tuple[str, ...]
    proof_refs: tuple[str, ...]
    blocker_status: BlockerStatus
    blockers: tuple[StrategyBlocker, ...] = ()

    @property
    def production_ready(self) -> bool:
        """True when no explicit blocker remains for this workflow."""
        return self.blocker_status is BlockerStatus.NONE and not self.blockers


STRATEGY_INTELLIGENCE_PROFILES: tuple[StrategyIntelligenceProfile, ...] = (
    StrategyIntelligenceProfile(
        workflow_id="native_arb",
        objective="Capture AMM price dislocations with zero working capital and one atomic repayment envelope.",
        execution_choice=(
            "Direct Executor.executeNativeArb is chosen after Pick A/Pick B fail because it avoids solver-auction "
            "latency and keeps the entire route in one flash-funded transaction."
        ),
        logic=(
            "Degenbot/Rust opportunity state enters the coordinator, DecisionEngine enforces precedence, "
            "NativeArbStrategy resolves a direct callback flash provider, and Executor strategy id 0 runs "
            "the sealed swap chain."
        ),
        mechanics=(
            "Aave V3, Morpho, ERC-3156, or Uniswap V3 flash source selected only when Executor can authenticate "
            "the callback.",
            "SwapStep calldata binds router target, tokens, expected deltas, min-out, and deadline.",
            "Executor retains surplus only after premium and minProfit are covered.",
        ),
        competitive_advantage=(
            "No inventory funding delay; execution is flash-funded and atomic.",
            "Degenbot pool intelligence plus TypeScript route sealing reduces stale-route submission.",
            "Direct path avoids CoW solver competition when no stronger internal match or composition exists.",
        ),
        latency_posture=(
            "Latency-sensitive direct lane. It has no batch-auction wait and is selected only after higher-edge "
            "internal/composition opportunities are unavailable."
        ),
        resource_utilization=(
            "Rust/Python degenbot state for discovery.",
            "TypeScript coordinator for route policy and calldata sealing.",
            "Solidity Executor for callback authentication, whitelists, repayment, and profit gate.",
        ),
        profitability_controls=(
            "Decision pass reasons and zero-flash guards before calldata build.",
            "Router whitelist and token-path validation on-chain.",
            "Post-swap balance delta must cover premium plus minProfit.",
        ),
        proof_refs=(
            "engine/src/lib.rs",
            "solver/driver/execution/degenbot_ipc.py",
            "coordinator/src/strategies/native-arb.ts",
            "contracts/test/unit/ExecutorStrategies.t.sol",
        ),
        blocker_status=BlockerStatus.NONE,
    ),
    StrategyIntelligenceProfile(
        workflow_id="internal_match",
        objective=(
            "Internalize spread between compatible intent/order flows before exposing the opportunity externally."
        ),
        execution_choice=(
            "Executor.matchInternal has first strategy precedence because matching in-process is faster and less "
            "leaky than routing both sides through public AMMs or external solvers."
        ),
        logic=(
            "Feed adapters normalize CoW and UniswapX candidates, the matcher selects compatible opposing flow, "
            "the encoder builds CoW and reactor legs, and Executor strategy id 1 settles the pair atomically."
        ),
        mechanics=(
            "Flash principal is mandatory; direct/no-flash inventory fallback is disabled.",
            "CoW settlement payout is constrained to transferToSettlement.",
            "UniswapX callback is transiently pinned to the expected reactor.",
        ),
        competitive_advantage=(
            "Locked precedence target is under 50 ms p99, giving this lane first claim on internal flow.",
            "Captures spread before an auction or AMM route reveals the edge.",
            "Reduces adverse selection by requiring exact expected inflows and receiver authentication.",
        ),
        latency_posture="Highest-priority low-latency lane with the locked Pick A target of <50 ms p99.",
        resource_utilization=(
            "CoW and UniswapX feeds for intent supply.",
            "Unified in-memory queue and matcher for fast compatibility checks.",
            "Executor receiver gates for settlement safety.",
        ),
        profitability_controls=(
            "Missing source orders stop before dispatch.",
            "Minimum expected inflows are enforced.",
            "Flash-token surplus must exceed premium plus minProfit.",
        ),
        proof_refs=(
            "coordinator/src/matching/internal-matcher.ts",
            "coordinator/src/matching/encoder.ts",
            "coordinator/src/strategies/internal-match.ts",
            "contracts/test/unit/ExecutorStrategies.t.sol",
        ),
        blocker_status=BlockerStatus.NONE,
    ),
    StrategyIntelligenceProfile(
        workflow_id="four_leg",
        objective="Compose bridge, native arb, CoW intent, and UniswapX rebalance legs into one higher-value route.",
        execution_choice=(
            "Executor.composeFourLeg is chosen when preflight proves the full composition is complete and more "
            "valuable than a single native route."
        ),
        logic=(
            "DecisionEngine asks FourLegStrategy for a typed plan, the strategy validates all opaque and swap "
            "legs, selects a direct flash source, and Executor strategy id 2 executes the atomic composition."
        ),
        mechanics=(
            "Across, arb, CoW, and UniswapX legs must all be explicitly supplied or derived.",
            "Each failed leg is wrapped with leg-level revert context.",
            "Direct callback flash providers are used; Balancer callback lanes remain separate adapters.",
        ),
        competitive_advantage=(
            "Combines surplus pockets that competitors may evaluate independently.",
            "Locked Pick B target is <1500 ms p99, appropriate for multi-venue route construction.",
            "Atomic execution prevents partial route exposure.",
        ),
        latency_posture="Composition lane with the locked Pick B target of <1500 ms p99.",
        resource_utilization=(
            "Intent feeds, degenbot route state, Across calldata, and quote adapters.",
            "TS preflight prevents incomplete route submission.",
            "Executor enforces leg completion and profit floor.",
        ),
        profitability_controls=(
            "Positive flash principal and expected profit required.",
            "Incomplete opaque leg calldata is rejected before dispatch.",
            "Final balance delta must pay premium plus minProfit.",
        ),
        proof_refs=(
            "coordinator/src/strategies/four-leg.ts",
            "coordinator/src/flash/source-router.ts",
            "contracts/test/unit/ExecutorStrategies.t.sol",
            "contracts/test/fork/ExecutorFourLegFlashProviders.fork.t.sol",
        ),
        blocker_status=BlockerStatus.NONE,
    ),
    StrategyIntelligenceProfile(
        workflow_id="uniswapx_filler",
        objective="Fill profitable UniswapX orders when quote surplus exceeds obligations and execution risk.",
        execution_choice=(
            "Executor.executeUniswapXFill is chosen because reactor callbacks must be authenticated on-chain while "
            "quote and order-screening logic stays off-chain."
        ),
        logic=(
            "The UniswapX feed screens orders, FillerBidStrategy quotes the fill, builds reactor callback calldata, "
            "and Executor pins the expected reactor for the synchronous callback."
        ),
        mechanics=(
            "No flash loan is used by this lane.",
            "Callback data is abi.encode(SwapStep[], expectedSelf, deadline).",
            "Reactor output obligations are aggregated by token before approval.",
        ),
        competitive_advantage=(
            "Direct order feed avoids waiting for DecisionKind dispatch.",
            "Quote screening rejects unsupported or stale orders before gas is spent.",
            "Transient reactor pinning reduces callback spoofing risk.",
        ),
        latency_posture="Feed-driven direct fill lane; priority is fast screening plus immediate direct submission.",
        resource_utilization=(
            "UniswapX feed for order discovery.",
            "Quote adapters for route profitability.",
            "Executor reactor callback for authenticated settlement.",
        ),
        profitability_controls=(
            "Chain, reactor, expiry, amount, signature, and quote checks.",
            "Missing quote and unwhitelisted router throw before dispatch.",
            "Realized-delta accounting records post-fill surplus.",
        ),
        proof_refs=(
            "coordinator/src/feeds/uniswapx-orders.ts",
            "coordinator/src/strategies/filler-bid.ts",
            "contracts/test/unit/ExecutorUniswapXFill.t.sol",
        ),
        blocker_status=BlockerStatus.NONE,
    ),
    StrategyIntelligenceProfile(
        workflow_id="liquidation",
        objective="Liquidate unhealthy Aave positions with Balancer V2 flash liquidity and no working capital.",
        execution_choice=(
            "A dedicated LiquidationExecutor is used instead of the generic Executor because Balancer V2 flash "
            "requires a dedicated receiveFlashLoan callback and plan-hash authentication."
        ),
        logic=(
            "The liquidation monitor indexes borrower risk, the simulator prices repay/collateral/gas/fees, "
            "the executor client eth_call preflights calldata, and LiquidationExecutor performs the flash "
            "liquidation plus collateral swap."
        ),
        mechanics=(
            "Balancer userData commits collateral, debt, borrower, debt amount, swap path, min-out, min-profit, "
            "and deadline.",
            "receiveFlashLoan verifies the active Vault and plan hash.",
            "Net debt-token surplus is emitted for reconciliation.",
        ),
        competitive_advantage=(
            "Dedicated daemon tracks borrower state continuously instead of waiting for generic arb signals.",
            "Flash funding allows larger liquidation sizing without idle inventory.",
            "Preflight and in-flight borrower controls reduce duplicate or reverting submissions.",
        ),
        latency_posture=(
            "Event-driven liquidation daemon; latency is bounded by monitor freshness, simulation, preflight, "
            "and RPC submission."
        ),
        resource_utilization=(
            "Aave reserve and position log monitor.",
            "Oracle, quoter, gas, blob floor, and Kairos fee simulation.",
            "Balancer V2 Vault flash liquidity and dedicated callback executor.",
        ),
        profitability_controls=(
            "Health factor threshold before simulation.",
            "Nonzero amountOutMinimum and deadline guard.",
            "Net profit must exceed minNetProfit after repayment.",
        ),
        proof_refs=(
            "coordinator/src/strategies/liquidation/monitor.ts",
            "coordinator/src/strategies/liquidation/simulator.ts",
            "coordinator/src/strategies/liquidation/executor.ts",
            "contracts/test/unit/LiquidationExecutor.t.sol",
        ),
        blocker_status=BlockerStatus.NONE,
    ),
    StrategyIntelligenceProfile(
        workflow_id="oracle_sandwich",
        objective="Capture deterministic oracle-update timing edge inside a flash-funded native-arb envelope.",
        execution_choice=(
            "The route reuses Executor.executeNativeArb because the profitable action must close atomically, "
            "repay flash liquidity, and pass the same minProfit balance-delta gate as native arb."
        ),
        logic=(
            "Signal bus and sequencer/oracle feeds identify timing candidates, the orchestrator verifies pool and "
            "edge inputs, offensive policy selects the permitted variant, and the leg builder emits one native-arb "
            "calldata package."
        ),
        mechanics=(
            "S-1/S-2/S-3/S-4/S-5 variants are policy-gated.",
            "Execution is one direct tx or one Rust Plan with requirePreflight=true.",
            "External victim-trigger JIT is not selected without strategy-layer ordering proof.",
        ),
        competitive_advantage=(
            "Uses sequencer/oracle signal awareness instead of generic public mempool assumptions.",
            "Private or Timeboost-aware submission can reduce observability and copy risk.",
            "Atomic native-arb envelope avoids persistent inventory exposure.",
        ),
        latency_posture=(
            "Timing-sensitive signal lane; execution must be immediate after signal correlation and preflight."
        ),
        resource_utilization=(
            "Rust sequencer feed and TS signal bus.",
            "Oracle-sandwich orchestrator, estimator, and leg builder.",
            "Executor native-arb callback and profit gate.",
        ),
        profitability_controls=(
            "Variant enable map and global pause policy.",
            "Estimator must approve the edge before calldata build.",
            "Native-arb minProfit gate after flash premium.",
        ),
        proof_refs=(
            "engine/src/monitor/sequencer_feed.rs",
            "coordinator/src/strategies/oracle-sandwich/orchestrator.ts",
            "coordinator/src/strategies/sandwich/offensive-policy.ts",
            "coordinator/src/signals/actions/dispatch-oracle-sandwich.ts",
        ),
        blocker_status=BlockerStatus.NONE,
    ),
    StrategyIntelligenceProfile(
        workflow_id="d3_cow_quote",
        objective=(
            "Price CoW flow without bond, solver capital, or solver submissions, and preserve provenance for "
            "downstream routes."
        ),
        execution_choice=(
            "The D3 filter and CowQuoterStrategy keep CoW feed handling quote-only because the current posture "
            "has no COW bond and no solver working capital."
        ),
        logic=(
            "The CoW competition feed emits batches, D3 classifies each order, and eligible AMM-routed payloads "
            "are priced through the coordinator quote engine for quote/provenance analysis."
        ),
        mechanics=(
            "Expired, invalid, peer-matchable, and AMM-routed classifications are explicit.",
            "Quote requests are JSON-safe and contain only sell/buy token, amount, side, and route constraints.",
            "No CoW solver solution is signed or submitted from this workflow.",
        ),
        competitive_advantage=(
            "Conserves cash and avoids bond/slashing exposure while retaining CoW order-flow intelligence.",
            "Avoids bidding where opposing CoW intent likely eliminates the spread.",
            "Feeds user-intent, internal-match, UniswapX, and native-arb decisions without inventory exposure.",
        ),
        latency_posture=(
            "Batch-aware quote lane; fast enough for CoW auction intake but intentionally not a solver tx path."
        ),
        resource_utilization=(
            "CoW competition feed.",
            "TS D3 classifier and CowQuoterStrategy.",
            "Python analysis driver when provenance retention is useful.",
        ),
        profitability_controls=(
            "Classification rejects invalid or peer-matchable orders.",
            "Quote failures return explicit rejected quote results.",
            "Downstream executable lanes must still pass their own atomic simulation and profit gates.",
        ),
        proof_refs=(
            "coordinator/src/feeds/cow-competition.ts",
            "coordinator/src/strategies/d3-filter.ts",
            "coordinator/src/strategies/cow-quoter.ts",
            "solver/driver/auction_build.py",
            "solver/driver/tests/test_auction_build.py",
        ),
        blocker_status=BlockerStatus.NONE,
    ),
    StrategyIntelligenceProfile(
        workflow_id="cow_flash_router",
        objective="Support chained CoW FlashLoanRouter settlement with replay-root verification.",
        execution_choice=(
            "The contract entry is kept gated because the upstream Router trigger must be strategist-encoded and "
            "no coordinator builder currently submits initialLoanCalldata end-to-end."
        ),
        logic=(
            "triggerCoWFlashLoanRouter seeds the flow, borrowerCallBack authenticates the Router, each round "
            "advances a chained hash, and the final round dispatches strategy id 1 or 2."
        ),
        mechanics=(
            "Round payload is abi.encode(round, totalRounds, expectedRoot, nextLoanCalldata, settlementCalldata).",
            "Final settlement payload is abi.encode(uint8(1|2), bytes params).",
            "Root mismatch, invalid strategy id, and forward failure are typed reverts.",
        ),
        competitive_advantage=(
            "Enables multi-round solver settlement without trusting intermediate callback data.",
            "Replay root gives deterministic provenance for audit and solver reconciliation.",
            "Keeps CoW-specific callback semantics outside the generic direct flash router.",
        ),
        latency_posture=(
            "Contract path is callback-chain ready; production latency cannot be claimed until the coordinator "
            "builder exists."
        ),
        resource_utilization=(
            "Executor transient flow id and cumulative hash slots.",
            "CoW FlashLoanRouter callback authentication.",
            "Existing MatchInternal and ComposeFourLeg final handlers.",
        ),
        profitability_controls=(
            "Expected root must match the full round chain.",
            "Only strategy id 1 or 2 can dispatch.",
            "Final handler retains the same minProfit balance-delta gate.",
        ),
        proof_refs=(
            "contracts/src/executors/Executor.sol",
            "contracts/test/unit/ExecutorCoWFlashRouter.t.sol",
            "contracts/test/unit/ExecutorCoWFlashRouterStart.t.sol",
        ),
        blocker_status=BlockerStatus.EXPLICIT_GATE,
        blockers=(
            StrategyBlocker(
                description=(
                    "No coordinator builder constructs and submits initialLoanCalldata for the upstream Router."
                ),
                remediation=(
                    "Only revive this as an explicitly approved bonded/user-intent settlement path; otherwise "
                    "keep CoW feed handling quote-only and use UniswapX/native-arb atomic execution for capital "
                    "movement."
                ),
                owner_refs=("coordinator/src/strategies/cow-quoter.ts", "contracts/src/interfaces/IExecutor.sol"),
                proof_refs=("contracts/test/unit/ExecutorCoWFlashRouterStart.t.sol",),
            ),
        ),
    ),
    StrategyIntelligenceProfile(
        workflow_id="morpho_liquidation_decision",
        objective="Capture liquidation bonuses from unhealthy Morpho Blue positions using zero-capital atomic flow.",
        execution_choice="Autonomous flash-borrowed liquidation via AtomicExecutor generic settlement calldata.",
        logic=(
            "Coordinator consumes Morpho liquidation opportunities, refreshes live pending state, prices the "
            "collateral swap and gas in loan-token units, simulates exact calldata, then dispatches through "
            "Submitter.sendDirect."
        ),
        mechanics=(
            "AtomicExecutor flash-borrows the Morpho loan asset through the configured flash source.",
            "Strategy data contains typed approvals plus Morpho Blue `liquidate` and SwapRouter02 `exactInput` calls.",
            "The executor repays the flash source and retains only loan-token surplus above minProfit.",
        ),
        competitive_advantage=(
            "Live pending-state refresh avoids stale borrower snapshots before broadcast.",
            "Same-calldata simulation reduces reverted liquidation submissions.",
            "Atomic generic-call settlement can reuse the hardened AtomicExecutor whitelist surface.",
        ),
        latency_posture="Latency-sensitive liquidation lane gated by source freshness and pending-state simulation.",
        resource_utilization=(
            "DecisionEngine Morpho payloads, live Morpho watchlist tick, route fee extraction, gas/quote sources, "
            "PendingStateCallSimulator, and Submitter direct broadcast."
        ),
        profitability_controls=(
            "Fresh sourced market and position reads.",
            "Expected swap output must cover repaid assets, flash fee, gas in loan-token units, and minNetProfit.",
            "Exact pending-state simulation must succeed before broadcast.",
            "AtomicExecutor enforces minProfit after flash repayment.",
        ),
        proof_refs=(
            "coordinator/src/decision/engine.ts",
            "coordinator/src/index.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-daemon.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-executor.ts",
            "coordinator/src/strategies/liquidation/morpho-blue-calldata.ts",
        ),
        blocker_status=BlockerStatus.NONE,
        blockers=(),
    ),
    StrategyIntelligenceProfile(
        workflow_id="jit_liquidity",
        objective=(
            "Capture concentrated-liquidity fee edge only when liquidity can be minted, used, unwound, and audited."
        ),
        execution_choice="Keep JIT policy gated until a concrete mint/swap/burn/collect builder exists.",
        logic="V4 hook classification can deny unsafe triggers, but no production LP lifecycle transaction is wired.",
        mechanics=(
            "Self-controlled or solver-owned triggers are the intended safe scope.",
            "External triggers require ordering proof.",
            "LP lifecycle must be same-transaction or have a bounded TTL unwind plan.",
        ),
        competitive_advantage=(
            "JIT can monetize fee bursts without idle LP inventory when the lifecycle is flash-funded.",
            "Ordering-proof requirement avoids selecting blind external-trigger opportunities.",
        ),
        latency_posture="Gated timing-sensitive lane; production latency cannot be claimed without a builder.",
        resource_utilization=(
            "V4 hook classifier.",
            "Universal liquidity metadata adapters.",
            "Future LP lifecycle executor lane.",
        ),
        profitability_controls=(
            "Fee capture must exceed premium, gas, inventory loss, and minProfit.",
            "Tick exposure must be bounded.",
            "Unwind and emergency exit must be explicit.",
        ),
        proof_refs=("coordinator/src/strategies/v4-hooks.ts", "docs/architecture/jit-lp-strategy-design.md"),
        blocker_status=BlockerStatus.EXPLICIT_GATE,
        blockers=(
            StrategyBlocker(
                description="No production JIT mint/swap/burn/collect calldata builder or fork test exists.",
                remediation=(
                    "Implement a JIT-specific builder, exposure caps, unwind invariant tests, and a fork test "
                    "covering fee capture and emergency exit."
                ),
                owner_refs=("coordinator/src/strategies/v4-hooks.ts", "docs/architecture/jit-lp-strategy-design.md"),
                proof_refs=("coordinator/src/strategies/v4-hooks.test.ts",),
            ),
        ),
    ),
    StrategyIntelligenceProfile(
        workflow_id="universal_liquidity_mutation",
        objective=(
            "Use liquidity adapters for intelligence while preventing autonomous LP mutation without a lower lane."
        ),
        execution_choice="Keep universal liquidity routing as policy and metadata, not a capital-moving executor.",
        logic="Adapters collect venue state; lower strategy lanes must own any executable LP mutation.",
        mechanics=(
            "Universal lane can rank and plan.",
            "Mutation requires strategy allowlist, caps, unwind plan, and emergency exit.",
            "No dispatcher can select this lane directly.",
        ),
        competitive_advantage=(
            "Centralizes liquidity intelligence for route ranking.",
            "Avoids broad autonomous LP mutation surface that competitors or adversaries could exploit.",
        ),
        latency_posture="Read/planning lane; production execution latency belongs to the lower strategy lane.",
        resource_utilization=(
            "Liquidity adapter registry.",
            "Canonical address registry.",
            "Lane policy gates.",
        ),
        profitability_controls=(
            "Lower lane must define realized-profit accounting.",
            "Exposure caps and unwind invariants required before mutation.",
        ),
        proof_refs=(
            "solver/driver/adapters/liquidityadapters/venues.py",
            "solver/driver/adapters/laneadapters/lanes.py",
        ),
        blocker_status=BlockerStatus.EXPLICIT_GATE,
        blockers=(
            StrategyBlocker(
                description="No lower strategy owns autonomous LP mutation calldata and unwind invariants.",
                remediation=(
                    "Bind LP mutation to a named strategy lane with exposure caps, unwind tests, and exit path."
                ),
                owner_refs=("solver/driver/adapters/laneadapters/lanes.py",),
                proof_refs=("solver/driver/tests/test_adapter_registry.py",),
            ),
        ),
    ),
    StrategyIntelligenceProfile(
        workflow_id="cow_user_submit",
        objective="Reserve a future outbound CoW user-submission lane without accidental capital movement.",
        execution_choice="Hard-disable until outbound CoW submission, signing, replay, and receiver paths exist.",
        logic="DecisionEngine branch is documented; dispatcher logs if it ever surfaces.",
        mechanics=("No planner, calldata builder, or submission module is attached.",),
        competitive_advantage=(
            "Preserves optionality for private CoW settlement without weakening current deterministic routing.",
        ),
        latency_posture="Disabled branch; latency is not claimed.",
        resource_utilization=("DecisionEngine gate and dispatcher logging.",),
        profitability_controls=("No transaction can be emitted from this branch today.",),
        proof_refs=("coordinator/src/decision/engine.ts", "coordinator/src/index.ts"),
        blocker_status=BlockerStatus.EXPLICIT_GATE,
        blockers=(
            StrategyBlocker(
                description="Outbound CoW user submission pipeline is absent.",
                remediation=(
                    "Add order signing, replay protection, receiver auth, settlement tests, and private routing."
                ),
                owner_refs=("coordinator/src/index.ts",),
                proof_refs=("coordinator/src/decision/engine.test.ts",),
            ),
        ),
    ),
    StrategyIntelligenceProfile(
        workflow_id="across_fill",
        objective="Use Across as a composition leg without exposing a standalone unprofitable bridge-fill lane.",
        execution_choice="Keep standalone Across gated; execute Across only inside complete composeFourLeg plans.",
        logic="Across calldata is valid only when FourLegStrategy includes it in a profitable atomic route.",
        mechanics=(
            "No standalone submission module.",
            "Four-leg preflight rejects incomplete Across calldata.",
        ),
        competitive_advantage=(
            "Avoids isolated bridge fills where profit source and unwind are undefined.",
            "Keeps bridge edge tied to multi-leg route surplus.",
        ),
        latency_posture="Standalone branch gated; four-leg latency target applies when included in Pick B.",
        resource_utilization=("Across intent feed inputs and FourLegStrategy preflight.",),
        profitability_controls=("Standalone branch emits no tx; composeFourLeg enforces premium plus minProfit.",),
        proof_refs=("coordinator/src/strategies/four-leg.ts", "coordinator/src/decision/engine.ts"),
        blocker_status=BlockerStatus.EXPLICIT_GATE,
        blockers=(
            StrategyBlocker(
                description="Standalone Across profit model, repayment source, and unwind are undefined.",
                remediation=(
                    "Keep standalone gated or define a dedicated bridge-fill strategy with preflight and tests."
                ),
                owner_refs=("coordinator/src/strategies/four-leg.ts",),
                proof_refs=("coordinator/src/strategies/four-leg.test.ts",),
            ),
        ),
    ),
    StrategyIntelligenceProfile(
        workflow_id="launch_sniper",
        objective="Keep launch-sniper/JB daemon scope outside the core coordinator until a dedicated safe lane exists.",
        execution_choice="Do not route launch-sniper through Executor or coordinator direct tx paths today.",
        logic="dispatchOpportunity logs the route as external; core strategy workflows do not emit calldata.",
        mechanics=("No planner, calldata builder, callback, or profit extraction path is wired.",),
        competitive_advantage=(
            "Avoids contaminating deterministic institutional routes with an unreviewed daemon strategy.",
        ),
        latency_posture="External branch; core coordinator latency is not claimed.",
        resource_utilization=("Jaredbot research docs and dispatcher gate.",),
        profitability_controls=("No core tx can be emitted from this branch.",),
        proof_refs=("docs/architecture/jaredbot-mev-playbook.md", "coordinator/src/index.ts"),
        blocker_status=BlockerStatus.EXPLICIT_GATE,
        blockers=(
            StrategyBlocker(
                description=(
                    "No audited launch-sniper calldata builder, replay policy, or profit extraction path exists."
                ),
                remediation="Add a dedicated ADR, builder, private submission policy, and fork tests before enabling.",
                owner_refs=("docs/architecture/jaredbot-mev-playbook.md",),
                proof_refs=("solver/driver/tests/test_adapter_registry.py",),
            ),
        ),
    ),
)


_PROFILES_BY_WORKFLOW_ID = {profile.workflow_id: profile for profile in STRATEGY_INTELLIGENCE_PROFILES}


def profile_for_workflow(workflow_id: str) -> StrategyIntelligenceProfile:
    """Return the competitive intelligence profile for one workflow."""
    try:
        return _PROFILES_BY_WORKFLOW_ID[workflow_id]
    except KeyError as exc:
        raise KeyError(f"unknown strategy intelligence profile {workflow_id!r}") from exc
