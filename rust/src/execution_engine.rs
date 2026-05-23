//! Deterministic execution-engine job composition.
//!
//! This module is the degenbot-owned Rust core for capital-moving execution
//! handoff. It composes live source artifacts, deterministic gates, simulation
//! output, calldata, and the broadcast lane into one hash-addressed job. The
//! side-effecting signing and broadcast adapters attach behind this accepted
//! degenbot dispatch envelope; they do not rebuild calldata.

use alloy::primitives::{keccak256, Address, Bytes, B256, U256};
use serde::Serialize;
use serde_json::Value;
use thiserror::Error;

/// Result alias for deterministic engine composition.
pub type EngineResult<T> = Result<T, EngineError>;

/// Errors raised before a plan may reach signing or broadcast code.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum EngineError {
    /// JSON input could not be parsed.
    #[error("invalid {field} json: {message}")]
    InvalidJson {
        /// Input label.
        field: &'static str,
        /// Parser error.
        message: String,
    },
    /// A required field was absent.
    #[error("{object} missing required field '{field}'")]
    MissingField {
        /// Object label.
        object: &'static str,
        /// Missing field name.
        field: &'static str,
    },
    /// A field had an invalid value.
    #[error("{object}.{field} invalid: {message}")]
    InvalidField {
        /// Object label.
        object: &'static str,
        /// Field name.
        field: &'static str,
        /// Validation message.
        message: String,
    },
    /// Runtime chain id did not match the policy.
    #[error("plan chain_id {actual} does not match policy expected_chain_id {expected}")]
    ChainMismatch {
        /// Plan chain id.
        actual: u64,
        /// Policy chain id.
        expected: u64,
    },
    /// The selected on-chain target is not in the allowed target set.
    #[error("target {target} is not policy-allowed")]
    TargetNotAllowed {
        /// Rejected target.
        target: Address,
    },
    /// The selected broadcast lane is not policy-allowed.
    #[error("broadcast lane {lane:?} is not policy-allowed")]
    LaneNotAllowed {
        /// Rejected lane.
        lane: BroadcastLane,
    },
    /// Deadline is too close or already expired.
    #[error("deadline {deadline_ms} is before required minimum {required_minimum_ms}")]
    DeadlineTooSoon {
        /// Plan deadline.
        deadline_ms: u64,
        /// Earliest acceptable deadline.
        required_minimum_ms: u64,
    },
    /// Gas limit is above the deterministic policy ceiling.
    #[error("gas_limit {gas_limit} exceeds max_gas_limit {max_gas_limit}")]
    GasLimitExceeded {
        /// Requested gas limit.
        gas_limit: u64,
        /// Policy maximum gas limit.
        max_gas_limit: u64,
    },
    /// Policy requires a REVM/fork preflight but the plan did not.
    #[error("policy requires preflight but plan.require_preflight=false")]
    PreflightRequired,
    /// Live source artifacts were required but absent.
    #[error("live source artifacts required but none were supplied")]
    MissingLiveSources,
    /// Not enough deterministic gates were supplied.
    #[error("gate count {actual} is below required minimum {required}")]
    GateCountTooLow {
        /// Supplied gate count.
        actual: usize,
        /// Required gate count.
        required: usize,
    },
    /// A deterministic gate rejected the plan.
    #[error("gate '{name}' rejected plan: {reason}")]
    GateRejected {
        /// Gate name.
        name: String,
        /// Rejection reason.
        reason: String,
    },
    /// Simulation/preflight result was not successful.
    #[error("simulation rejected plan: {reason}")]
    SimulationRejected {
        /// Rejection reason.
        reason: String,
    },
    /// Simulated profit did not meet the floor.
    #[error("simulation profit {actual} below required floor {required}")]
    ProfitBelowFloor {
        /// Simulated profit.
        actual: U256,
        /// Required floor.
        required: U256,
    },
}

/// Capital-moving strategy class.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StrategyKind {
    /// Same-chain atomic AMM arbitrage.
    NativeArb,
    /// CoW/UniswapX internal match.
    InternalMatch,
    /// Across/native-arb/CoW/UniswapX composition.
    FourLeg,
    /// `UniswapX` reactor callback flash fill.
    UniswapXFlashFill,
    /// Across/EIP-7683 destination intent fill.
    AcrossIntentFill,
    /// Morpho Blue liquidation route.
    MorphoLiquidation,
    /// Oracle-update sandwich / frontrun class.
    OracleUpdateSandwich,
    /// 1inch Fusion resolver-gap fill.
    OneInchFusionGap,
    /// Operator-defined strategy name.
    Custom(String),
}

impl StrategyKind {
    fn parse(value: &str) -> Self {
        match normalize_key(value).as_str() {
            "nativearb" | "native_arbitrage" => Self::NativeArb,
            "internalmatch" => Self::InternalMatch,
            "fourleg" | "fourlegcomposition" => Self::FourLeg,
            "uniswapx" | "uniswapxflashfill" => Self::UniswapXFlashFill,
            "across" | "acrossintentfill" => Self::AcrossIntentFill,
            "morpho" | "morpholiquidation" => Self::MorphoLiquidation,
            "oracleupdatesandwich" | "sandwich" => Self::OracleUpdateSandwich,
            "oneinchfusiongap" | "fusiongap" => Self::OneInchFusionGap,
            _ => Self::Custom(value.to_string()),
        }
    }

    fn as_wire(&self) -> &str {
        match self {
            Self::NativeArb => "native_arb",
            Self::InternalMatch => "internal_match",
            Self::FourLeg => "four_leg",
            Self::UniswapXFlashFill => "uniswapx_flash_fill",
            Self::AcrossIntentFill => "across_intent_fill",
            Self::MorphoLiquidation => "morpho_liquidation",
            Self::OracleUpdateSandwich => "oracle_update_sandwich",
            Self::OneInchFusionGap => "oneinch_fusion_gap",
            Self::Custom(value) => value,
        }
    }
}

/// Broadcast lane selected before signing.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BroadcastLane {
    /// Normal public RPC submission.
    PublicRpc,
    /// Private relay / protected transaction path.
    PrivateRelay,
    /// Arbitrum Kairos path.
    Kairos,
    /// Arbitrum Timeboost-aware path.
    Timeboost,
}

impl BroadcastLane {
    fn parse(value: &str) -> EngineResult<Self> {
        match normalize_key(value).as_str() {
            "public" | "publicrpc" | "rpc" => Ok(Self::PublicRpc),
            "private" | "privaterelay" => Ok(Self::PrivateRelay),
            "kairos" => Ok(Self::Kairos),
            "timeboost" => Ok(Self::Timeboost),
            _ => Err(EngineError::InvalidField {
                object: "plan",
                field: "broadcast_lane",
                message: format!("unknown lane '{value}'"),
            }),
        }
    }

    const fn as_wire(self) -> &'static str {
        match self {
            Self::PublicRpc => "public_rpc",
            Self::PrivateRelay => "private_relay",
            Self::Kairos => "kairos",
            Self::Timeboost => "timeboost",
        }
    }
}

/// One live source used to build the plan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceArtifact {
    /// Source label, e.g. `degenbot.uniswap_v3_pool`.
    pub name: String,
    /// Block number used for this source.
    pub block_number: u64,
    /// Wall-clock observation timestamp.
    pub observed_at_ns: u64,
}

/// One deterministic gate result.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GateArtifact {
    /// Gate name.
    pub name: String,
    /// Whether the gate admitted the plan.
    pub admitted: bool,
    /// Optional reason.
    pub reason: Option<String>,
}

/// Final simulation/preflight artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SimulationArtifact {
    /// Whether the simulation succeeded.
    pub success: bool,
    /// Expected profit in raw token units.
    pub expected_profit_wei: U256,
    /// Simulated gas used.
    pub gas_used: u64,
    /// Count of state reads used by the simulation layer.
    pub state_read_count: u64,
    /// Optional revert/rejection reason.
    pub revert_reason: Option<String>,
}

/// Deterministic policy applied before signing.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EnginePolicy {
    /// Required chain id.
    pub expected_chain_id: u64,
    /// Minimum profit floor in raw units.
    pub min_profit_wei: U256,
    /// Maximum gas limit.
    pub max_gas_limit: u64,
    /// Require REVM/fork preflight.
    pub require_preflight: bool,
    /// Require at least one live source artifact.
    pub require_live_sources: bool,
    /// Minimum deterministic gate count.
    pub min_gate_count: usize,
    /// Minimum time between now and deadline.
    pub min_deadline_ms_from_now: u64,
    /// Allowed execution targets. Empty means no target allow-list.
    pub allowed_targets: Vec<Address>,
    /// Allowed lanes. Empty means all lanes are allowed.
    pub allowed_lanes: Vec<BroadcastLane>,
}

/// Capital-moving transaction plan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExecutionPlan {
    /// Trace/correlation id.
    pub trace_id: String,
    /// Strategy class.
    pub strategy: StrategyKind,
    /// Chain id.
    pub chain_id: u64,
    /// On-chain execution target.
    pub target: Address,
    /// Calldata to submit.
    pub calldata: Bytes,
    /// Native value.
    pub value: U256,
    /// Gas limit.
    pub gas_limit: u64,
    /// Max fee per gas.
    pub max_fee_per_gas: U256,
    /// Max priority fee per gas.
    pub max_priority_fee_per_gas: U256,
    /// Deadline in unix milliseconds.
    pub deadline_ms: u64,
    /// Token used for profit measurement.
    pub profit_token: Address,
    /// Plan-level profit floor in raw units.
    pub min_profit_wei: U256,
    /// Whether preflight is required by the plan.
    pub require_preflight: bool,
    /// Dry-run plans stop after preflight.
    pub dry_run: bool,
    /// Selected lane for signing/broadcast.
    pub broadcast_lane: BroadcastLane,
}

/// Broadcast envelope derived from the plan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BroadcastEnvelope {
    /// Selected lane.
    pub lane: BroadcastLane,
    /// Whether this is allowed to reach broadcast.
    pub submit: bool,
    /// Whether private submission is selected.
    pub private_submission: bool,
    /// Whether preflight must run before signing.
    pub require_preflight: bool,
}

/// Composed job accepted by the deterministic engine boundary.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ComposedEngineJob {
    /// Stable hash over the plan and admission artifacts.
    pub plan_hash: B256,
    /// Original plan.
    pub plan: ExecutionPlan,
    /// Live source artifacts.
    pub sources: Vec<SourceArtifact>,
    /// Gate artifacts.
    pub gates: Vec<GateArtifact>,
    /// Simulation artifact.
    pub simulation: SimulationArtifact,
    /// Broadcast decision.
    pub broadcast: BroadcastEnvelope,
}

/// JSON-safe report returned to Python/control-plane code.
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[allow(clippy::struct_excessive_bools)]
pub struct EngineJobReport {
    /// Hex plan hash.
    pub plan_hash: String,
    /// Trace id.
    pub trace_id: String,
    /// Strategy class.
    pub strategy: String,
    /// Target address.
    pub target: String,
    /// Chain id.
    pub chain_id: u64,
    /// Broadcast lane.
    pub broadcast_lane: String,
    /// Broadcast enabled.
    pub submit: bool,
    /// Private submission selected.
    pub private_submission: bool,
    /// Preflight required.
    pub require_preflight: bool,
    /// Dry-run mode.
    pub dry_run: bool,
    /// Source artifact count.
    pub source_count: usize,
    /// Gate count.
    pub gate_count: usize,
    /// Expected profit in raw units.
    pub expected_profit_wei: String,
    /// Effective profit floor in raw units.
    pub required_profit_floor_wei: String,
    /// Gas limit.
    pub gas_limit: u64,
    /// Simulated gas used.
    pub simulated_gas_used: u64,
    /// Deadline in unix milliseconds.
    pub deadline_ms: u64,
    /// Calldata byte length.
    pub calldata_len: usize,
}

impl ComposedEngineJob {
    /// Convert to a JSON-safe report.
    #[must_use]
    pub fn to_report(&self, policy: &EnginePolicy) -> EngineJobReport {
        EngineJobReport {
            plan_hash: format!("{:#x}", self.plan_hash),
            trace_id: self.plan.trace_id.clone(),
            strategy: self.plan.strategy.as_wire().to_string(),
            target: format!("{:#x}", self.plan.target),
            chain_id: self.plan.chain_id,
            broadcast_lane: self.broadcast.lane.as_wire().to_string(),
            submit: self.broadcast.submit,
            private_submission: self.broadcast.private_submission,
            require_preflight: self.broadcast.require_preflight,
            dry_run: self.plan.dry_run,
            source_count: self.sources.len(),
            gate_count: self.gates.len(),
            expected_profit_wei: self.simulation.expected_profit_wei.to_string(),
            required_profit_floor_wei: required_profit_floor(&self.plan, policy).to_string(),
            gas_limit: self.plan.gas_limit,
            simulated_gas_used: self.simulation.gas_used,
            deadline_ms: self.plan.deadline_ms,
            calldata_len: self.plan.calldata.len(),
        }
    }
}

/// Compose and validate an execution job.
#[cfg_attr(feature = "hotpath", hotpath::measure)]
pub fn compose_engine_job(
    plan: ExecutionPlan,
    policy: &EnginePolicy,
    sources: Vec<SourceArtifact>,
    gates: Vec<GateArtifact>,
    simulation: SimulationArtifact,
    now_ms: u64,
) -> EngineResult<ComposedEngineJob> {
    validate_plan(&plan, policy, &sources, &gates, &simulation, now_ms)?;
    let broadcast = BroadcastEnvelope {
        lane: plan.broadcast_lane,
        submit: !plan.dry_run,
        private_submission: matches!(
            plan.broadcast_lane,
            BroadcastLane::PrivateRelay | BroadcastLane::Kairos | BroadcastLane::Timeboost
        ),
        require_preflight: plan.require_preflight || policy.require_preflight || plan.dry_run,
    };
    let plan_hash = compute_plan_hash(&plan, policy, &sources, &gates, &simulation, &broadcast);
    Ok(ComposedEngineJob {
        plan_hash,
        plan,
        sources,
        gates,
        simulation,
        broadcast,
    })
}

/// Compose an execution job from JSON strings and return a JSON report.
pub fn compose_engine_job_json(
    plan_json: &str,
    policy_json: &str,
    sources_json: &str,
    gates_json: &str,
    simulation_json: &str,
    now_ms: u64,
) -> EngineResult<String> {
    let plan = parse_plan(&parse_json("plan", plan_json)?)?;
    let policy = parse_policy(&parse_json("policy", policy_json)?)?;
    let sources = parse_sources(&parse_json("sources", sources_json)?)?;
    let gates = parse_gates(&parse_json("gates", gates_json)?)?;
    let simulation = parse_simulation(&parse_json("simulation", simulation_json)?)?;
    let job = compose_engine_job(plan, &policy, sources, gates, simulation, now_ms)?;
    serde_json::to_string(&job.to_report(&policy)).map_err(|err| EngineError::InvalidJson {
        field: "report",
        message: err.to_string(),
    })
}

fn validate_plan(
    plan: &ExecutionPlan,
    policy: &EnginePolicy,
    sources: &[SourceArtifact],
    gates: &[GateArtifact],
    simulation: &SimulationArtifact,
    now_ms: u64,
) -> EngineResult<()> {
    validate_plan_core(plan, policy, now_ms)?;
    validate_sources(policy, sources)?;
    validate_gates(policy, gates)?;
    validate_simulation(plan, policy, simulation)?;
    Ok(())
}

fn validate_plan_core(
    plan: &ExecutionPlan,
    policy: &EnginePolicy,
    now_ms: u64,
) -> EngineResult<()> {
    if plan.chain_id != policy.expected_chain_id {
        return Err(EngineError::ChainMismatch {
            actual: plan.chain_id,
            expected: policy.expected_chain_id,
        });
    }
    if plan.target == Address::ZERO {
        return Err(EngineError::InvalidField {
            object: "plan",
            field: "target",
            message: "zero address target".to_string(),
        });
    }
    if !policy.allowed_targets.is_empty() && !policy.allowed_targets.contains(&plan.target) {
        return Err(EngineError::TargetNotAllowed {
            target: plan.target,
        });
    }
    if !policy.allowed_lanes.is_empty() && !policy.allowed_lanes.contains(&plan.broadcast_lane) {
        return Err(EngineError::LaneNotAllowed {
            lane: plan.broadcast_lane,
        });
    }
    if plan.calldata.len() < 4 {
        return Err(EngineError::InvalidField {
            object: "plan",
            field: "calldata",
            message: "calldata must include a 4-byte selector".to_string(),
        });
    }
    if plan.gas_limit == 0 {
        return Err(EngineError::InvalidField {
            object: "plan",
            field: "gas_limit",
            message: "gas_limit must be positive".to_string(),
        });
    }
    if plan.gas_limit > policy.max_gas_limit {
        return Err(EngineError::GasLimitExceeded {
            gas_limit: plan.gas_limit,
            max_gas_limit: policy.max_gas_limit,
        });
    }
    let required_minimum_ms = now_ms.saturating_add(policy.min_deadline_ms_from_now);
    if plan.deadline_ms < required_minimum_ms {
        return Err(EngineError::DeadlineTooSoon {
            deadline_ms: plan.deadline_ms,
            required_minimum_ms,
        });
    }
    if policy.require_preflight && !plan.require_preflight {
        return Err(EngineError::PreflightRequired);
    }
    Ok(())
}

fn validate_sources(policy: &EnginePolicy, sources: &[SourceArtifact]) -> EngineResult<()> {
    if policy.require_live_sources && sources.is_empty() {
        return Err(EngineError::MissingLiveSources);
    }
    for source in sources {
        if source.name.trim().is_empty() {
            return Err(EngineError::InvalidField {
                object: "source",
                field: "name",
                message: "source name cannot be empty".to_string(),
            });
        }
        if source.observed_at_ns == 0 {
            return Err(EngineError::InvalidField {
                object: "source",
                field: "observed_at_ns",
                message: "source observation timestamp cannot be zero".to_string(),
            });
        }
    }
    Ok(())
}

fn validate_gates(policy: &EnginePolicy, gates: &[GateArtifact]) -> EngineResult<()> {
    if gates.len() < policy.min_gate_count {
        return Err(EngineError::GateCountTooLow {
            actual: gates.len(),
            required: policy.min_gate_count,
        });
    }
    for gate in gates {
        if gate.name.trim().is_empty() {
            return Err(EngineError::InvalidField {
                object: "gate",
                field: "name",
                message: "gate name cannot be empty".to_string(),
            });
        }
        if !gate.admitted {
            return Err(EngineError::GateRejected {
                name: gate.name.clone(),
                reason: gate
                    .reason
                    .clone()
                    .unwrap_or_else(|| "no reason supplied".to_string()),
            });
        }
    }
    Ok(())
}

fn validate_simulation(
    plan: &ExecutionPlan,
    policy: &EnginePolicy,
    simulation: &SimulationArtifact,
) -> EngineResult<()> {
    if !simulation.success {
        return Err(EngineError::SimulationRejected {
            reason: simulation
                .revert_reason
                .clone()
                .unwrap_or_else(|| "simulation success=false".to_string()),
        });
    }
    let floor = required_profit_floor(plan, policy);
    if simulation.expected_profit_wei < floor {
        return Err(EngineError::ProfitBelowFloor {
            actual: simulation.expected_profit_wei,
            required: floor,
        });
    }
    Ok(())
}

fn required_profit_floor(plan: &ExecutionPlan, policy: &EnginePolicy) -> U256 {
    if plan.min_profit_wei > policy.min_profit_wei {
        plan.min_profit_wei
    } else {
        policy.min_profit_wei
    }
}

fn compute_plan_hash(
    plan: &ExecutionPlan,
    policy: &EnginePolicy,
    sources: &[SourceArtifact],
    gates: &[GateArtifact],
    simulation: &SimulationArtifact,
    broadcast: &BroadcastEnvelope,
) -> B256 {
    let mut bytes = Vec::new();
    push_str(&mut bytes, "degenbot-engine-v1");
    push_str(&mut bytes, &plan.trace_id);
    push_str(&mut bytes, plan.strategy.as_wire());
    bytes.extend_from_slice(&plan.chain_id.to_be_bytes());
    bytes.extend_from_slice(plan.target.as_slice());
    push_bytes(&mut bytes, plan.calldata.as_ref());
    push_u256(&mut bytes, plan.value);
    bytes.extend_from_slice(&plan.gas_limit.to_be_bytes());
    push_u256(&mut bytes, plan.max_fee_per_gas);
    push_u256(&mut bytes, plan.max_priority_fee_per_gas);
    bytes.extend_from_slice(&plan.deadline_ms.to_be_bytes());
    bytes.extend_from_slice(plan.profit_token.as_slice());
    push_u256(&mut bytes, plan.min_profit_wei);
    bytes.push(u8::from(plan.require_preflight));
    bytes.push(u8::from(plan.dry_run));
    push_str(&mut bytes, plan.broadcast_lane.as_wire());
    bytes.extend_from_slice(&policy.expected_chain_id.to_be_bytes());
    push_u256(&mut bytes, policy.min_profit_wei);
    bytes.extend_from_slice(&policy.max_gas_limit.to_be_bytes());
    bytes.push(u8::from(policy.require_preflight));
    bytes.push(u8::from(policy.require_live_sources));
    bytes.extend_from_slice(&(policy.min_gate_count as u64).to_be_bytes());
    bytes.extend_from_slice(&policy.min_deadline_ms_from_now.to_be_bytes());
    for target in &policy.allowed_targets {
        bytes.extend_from_slice(target.as_slice());
    }
    for lane in &policy.allowed_lanes {
        push_str(&mut bytes, lane.as_wire());
    }
    for source in sources {
        push_str(&mut bytes, &source.name);
        bytes.extend_from_slice(&source.block_number.to_be_bytes());
        bytes.extend_from_slice(&source.observed_at_ns.to_be_bytes());
    }
    for gate in gates {
        push_str(&mut bytes, &gate.name);
        bytes.push(u8::from(gate.admitted));
        push_str(&mut bytes, gate.reason.as_deref().unwrap_or(""));
    }
    bytes.push(u8::from(simulation.success));
    push_u256(&mut bytes, simulation.expected_profit_wei);
    bytes.extend_from_slice(&simulation.gas_used.to_be_bytes());
    bytes.extend_from_slice(&simulation.state_read_count.to_be_bytes());
    push_str(
        &mut bytes,
        simulation.revert_reason.as_deref().unwrap_or(""),
    );
    push_str(&mut bytes, broadcast.lane.as_wire());
    bytes.push(u8::from(broadcast.submit));
    bytes.push(u8::from(broadcast.private_submission));
    bytes.push(u8::from(broadcast.require_preflight));
    keccak256(bytes)
}

fn push_bytes(out: &mut Vec<u8>, value: &[u8]) {
    out.extend_from_slice(&(value.len() as u64).to_be_bytes());
    out.extend_from_slice(value);
}

fn push_str(out: &mut Vec<u8>, value: &str) {
    push_bytes(out, value.as_bytes());
}

fn push_u256(out: &mut Vec<u8>, value: U256) {
    push_str(out, &value.to_string());
}

fn parse_json(field: &'static str, value: &str) -> EngineResult<Value> {
    serde_json::from_str(value).map_err(|err| EngineError::InvalidJson {
        field,
        message: err.to_string(),
    })
}

fn parse_plan(value: &Value) -> EngineResult<ExecutionPlan> {
    Ok(ExecutionPlan {
        trace_id: required_str(value, "plan", "trace_id")?.to_string(),
        strategy: StrategyKind::parse(required_str(value, "plan", "strategy")?),
        chain_id: required_u64(value, "plan", "chain_id")?,
        target: required_address(value, "plan", "target")?,
        calldata: required_bytes(value, "plan", "calldata")?,
        value: optional_u256(value, "plan", "value")?.unwrap_or(U256::ZERO),
        gas_limit: required_u64(value, "plan", "gas_limit")?,
        max_fee_per_gas: required_u256(value, "plan", "max_fee_per_gas")?,
        max_priority_fee_per_gas: required_u256(value, "plan", "max_priority_fee_per_gas")?,
        deadline_ms: required_u64(value, "plan", "deadline_ms")?,
        profit_token: required_address(value, "plan", "profit_token")?,
        min_profit_wei: required_u256(value, "plan", "min_profit_wei")?,
        require_preflight: required_bool(value, "plan", "require_preflight")?,
        dry_run: required_bool(value, "plan", "dry_run")?,
        broadcast_lane: BroadcastLane::parse(required_str(value, "plan", "broadcast_lane")?)?,
    })
}

fn parse_policy(value: &Value) -> EngineResult<EnginePolicy> {
    let min_gate_count = required_usize(value, "policy", "min_gate_count")?;
    Ok(EnginePolicy {
        expected_chain_id: required_u64(value, "policy", "expected_chain_id")?,
        min_profit_wei: required_u256(value, "policy", "min_profit_wei")?,
        max_gas_limit: required_u64(value, "policy", "max_gas_limit")?,
        require_preflight: required_bool(value, "policy", "require_preflight")?,
        require_live_sources: required_bool(value, "policy", "require_live_sources")?,
        min_gate_count,
        min_deadline_ms_from_now: required_u64(value, "policy", "min_deadline_ms_from_now")?,
        allowed_targets: optional_address_array(value, "policy", "allowed_targets")?,
        allowed_lanes: optional_lane_array(value, "policy", "allowed_lanes")?,
    })
}

fn parse_sources(value: &Value) -> EngineResult<Vec<SourceArtifact>> {
    let array = value.as_array().ok_or_else(|| EngineError::InvalidField {
        object: "sources",
        field: "root",
        message: "expected array".to_string(),
    })?;
    array
        .iter()
        .map(|source| {
            Ok(SourceArtifact {
                name: required_str(source, "source", "name")?.to_string(),
                block_number: required_u64(source, "source", "block_number")?,
                observed_at_ns: required_u64(source, "source", "observed_at_ns")?,
            })
        })
        .collect()
}

fn parse_gates(value: &Value) -> EngineResult<Vec<GateArtifact>> {
    let array = value.as_array().ok_or_else(|| EngineError::InvalidField {
        object: "gates",
        field: "root",
        message: "expected array".to_string(),
    })?;
    array
        .iter()
        .map(|gate| {
            Ok(GateArtifact {
                name: required_str(gate, "gate", "name")?.to_string(),
                admitted: required_bool(gate, "gate", "admitted")?,
                reason: optional_str(gate, "reason").map(ToString::to_string),
            })
        })
        .collect()
}

fn parse_simulation(value: &Value) -> EngineResult<SimulationArtifact> {
    Ok(SimulationArtifact {
        success: required_bool(value, "simulation", "success")?,
        expected_profit_wei: required_u256(value, "simulation", "expected_profit_wei")?,
        gas_used: required_u64(value, "simulation", "gas_used")?,
        state_read_count: required_u64(value, "simulation", "state_read_count")?,
        revert_reason: optional_str(value, "revert_reason").map(ToString::to_string),
    })
}

fn field<'a>(value: &'a Value, object: &'static str, key: &'static str) -> EngineResult<&'a Value> {
    value
        .get(key)
        .ok_or(EngineError::MissingField { object, field: key })
}

fn required_str<'a>(
    value: &'a Value,
    object: &'static str,
    key: &'static str,
) -> EngineResult<&'a str> {
    field(value, object, key)?
        .as_str()
        .ok_or_else(|| EngineError::InvalidField {
            object,
            field: key,
            message: "expected string".to_string(),
        })
}

fn optional_str<'a>(value: &'a Value, key: &'static str) -> Option<&'a str> {
    value.get(key).and_then(Value::as_str)
}

fn required_bool(value: &Value, object: &'static str, key: &'static str) -> EngineResult<bool> {
    field(value, object, key)?
        .as_bool()
        .ok_or_else(|| EngineError::InvalidField {
            object,
            field: key,
            message: "expected bool".to_string(),
        })
}

fn required_u64(value: &Value, object: &'static str, key: &'static str) -> EngineResult<u64> {
    let raw = field(value, object, key)?;
    if let Some(n) = raw.as_u64() {
        return Ok(n);
    }
    let text = raw.as_str().ok_or_else(|| EngineError::InvalidField {
        object,
        field: key,
        message: "expected u64 or decimal string".to_string(),
    })?;
    text.parse::<u64>()
        .map_err(|err| EngineError::InvalidField {
            object,
            field: key,
            message: err.to_string(),
        })
}

fn required_usize(value: &Value, object: &'static str, key: &'static str) -> EngineResult<usize> {
    let raw = required_u64(value, object, key)?;
    usize::try_from(raw).map_err(|err| EngineError::InvalidField {
        object,
        field: key,
        message: err.to_string(),
    })
}

fn required_u256(value: &Value, object: &'static str, key: &'static str) -> EngineResult<U256> {
    optional_u256(value, object, key)?.ok_or(EngineError::MissingField { object, field: key })
}

fn optional_u256(
    value: &Value,
    object: &'static str,
    key: &'static str,
) -> EngineResult<Option<U256>> {
    let Some(raw) = value.get(key) else {
        return Ok(None);
    };
    if let Some(n) = raw.as_u64() {
        return Ok(Some(U256::from(n)));
    }
    let Some(text) = raw.as_str() else {
        return Err(EngineError::InvalidField {
            object,
            field: key,
            message: "expected decimal string, hex string, or u64".to_string(),
        });
    };
    parse_u256(text, object, key).map(Some)
}

fn parse_u256(text: &str, object: &'static str, key: &'static str) -> EngineResult<U256> {
    text.strip_prefix("0x")
        .map_or_else(
            || U256::from_str_radix(text, 10),
            |hex| U256::from_str_radix(hex, 16),
        )
        .map_err(|err| EngineError::InvalidField {
            object,
            field: key,
            message: err.to_string(),
        })
}

fn required_address(
    value: &Value,
    object: &'static str,
    key: &'static str,
) -> EngineResult<Address> {
    let text = required_str(value, object, key)?;
    parse_address(text, object, key)
}

fn parse_address(text: &str, object: &'static str, key: &'static str) -> EngineResult<Address> {
    text.parse::<Address>()
        .map_err(|err| EngineError::InvalidField {
            object,
            field: key,
            message: err.to_string(),
        })
}

fn required_bytes(value: &Value, object: &'static str, key: &'static str) -> EngineResult<Bytes> {
    let text = required_str(value, object, key)?;
    let stripped = text.strip_prefix("0x").unwrap_or(text);
    let bytes = alloy::hex::decode(stripped).map_err(|err| EngineError::InvalidField {
        object,
        field: key,
        message: err.to_string(),
    })?;
    Ok(Bytes::from(bytes))
}

fn optional_address_array(
    value: &Value,
    object: &'static str,
    key: &'static str,
) -> EngineResult<Vec<Address>> {
    let Some(raw) = value.get(key) else {
        return Ok(Vec::new());
    };
    let array = raw.as_array().ok_or_else(|| EngineError::InvalidField {
        object,
        field: key,
        message: "expected array".to_string(),
    })?;
    array
        .iter()
        .map(|entry| {
            let text = entry.as_str().ok_or_else(|| EngineError::InvalidField {
                object,
                field: key,
                message: "expected address string".to_string(),
            })?;
            parse_address(text, object, key)
        })
        .collect()
}

fn optional_lane_array(
    value: &Value,
    object: &'static str,
    key: &'static str,
) -> EngineResult<Vec<BroadcastLane>> {
    let Some(raw) = value.get(key) else {
        return Ok(Vec::new());
    };
    let array = raw.as_array().ok_or_else(|| EngineError::InvalidField {
        object,
        field: key,
        message: "expected array".to_string(),
    })?;
    array
        .iter()
        .map(|entry| {
            let text = entry.as_str().ok_or_else(|| EngineError::InvalidField {
                object,
                field: key,
                message: "expected lane string".to_string(),
            })?;
            BroadcastLane::parse(text)
        })
        .collect()
}

fn normalize_key(value: &str) -> String {
    value
        .chars()
        .filter(|ch| *ch != '_' && *ch != '-' && *ch != ' ')
        .flat_map(char::to_lowercase)
        .collect()
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used, clippy::expect_used)]

    use super::*;

    fn address(byte: u8) -> Address {
        Address::repeat_byte(byte)
    }

    fn plan() -> ExecutionPlan {
        ExecutionPlan {
            trace_id: "trace-1".to_string(),
            strategy: StrategyKind::UniswapXFlashFill,
            chain_id: 42_161,
            target: address(0x11),
            calldata: Bytes::from_static(&[0x12, 0x34, 0x56, 0x78, 0xab]),
            value: U256::ZERO,
            gas_limit: 500_000,
            max_fee_per_gas: U256::from(100u64),
            max_priority_fee_per_gas: U256::from(1u64),
            deadline_ms: 10_000,
            profit_token: address(0x22),
            min_profit_wei: U256::from(100u64),
            require_preflight: true,
            dry_run: false,
            broadcast_lane: BroadcastLane::PrivateRelay,
        }
    }

    fn policy() -> EnginePolicy {
        EnginePolicy {
            expected_chain_id: 42_161,
            min_profit_wei: U256::from(50u64),
            max_gas_limit: 1_000_000,
            require_preflight: true,
            require_live_sources: true,
            min_gate_count: 2,
            min_deadline_ms_from_now: 1_000,
            allowed_targets: vec![address(0x11)],
            allowed_lanes: vec![BroadcastLane::PrivateRelay],
        }
    }

    fn sources() -> Vec<SourceArtifact> {
        vec![SourceArtifact {
            name: "degenbot.uniswapx.order".to_string(),
            block_number: 123,
            observed_at_ns: 1,
        }]
    }

    fn gates() -> Vec<GateArtifact> {
        vec![
            GateArtifact {
                name: "quote_gate".to_string(),
                admitted: true,
                reason: None,
            },
            GateArtifact {
                name: "simulation_gate".to_string(),
                admitted: true,
                reason: Some("profit floor met".to_string()),
            },
        ]
    }

    fn simulation() -> SimulationArtifact {
        SimulationArtifact {
            success: true,
            expected_profit_wei: U256::from(150u64),
            gas_used: 321_000,
            state_read_count: 12,
            revert_reason: None,
        }
    }

    #[test]
    fn composes_hash_addressed_job() {
        let policy = policy();
        let job =
            compose_engine_job(plan(), &policy, sources(), gates(), simulation(), 8_000).unwrap();
        assert_eq!(job.plan.strategy, StrategyKind::UniswapXFlashFill);
        assert_eq!(job.broadcast.lane, BroadcastLane::PrivateRelay);
        assert!(job.broadcast.private_submission);
        assert!(job.broadcast.require_preflight);
        assert_ne!(job.plan_hash, B256::ZERO);
    }

    #[test]
    fn rejects_gate_failure() {
        let mut gates = gates();
        gates[1].admitted = false;
        gates[1].reason = Some("sim below floor".to_string());
        let policy = policy();
        let err = compose_engine_job(plan(), &policy, sources(), gates, simulation(), 8_000)
            .expect_err("gate rejection must fail closed");
        assert!(matches!(err, EngineError::GateRejected { .. }));
    }

    #[test]
    fn rejects_profit_below_effective_floor() {
        let mut simulation = simulation();
        simulation.expected_profit_wei = U256::from(99u64);
        let policy = policy();
        let err = compose_engine_job(plan(), &policy, sources(), gates(), simulation, 8_000)
            .expect_err("low profit must fail closed");
        assert!(matches!(err, EngineError::ProfitBelowFloor { .. }));
    }

    #[test]
    fn json_composition_returns_report() {
        let plan_json = format!(
            r#"{{
                "trace_id":"trace-json",
                "strategy":"uniswapx_flash_fill",
                "chain_id":42161,
                "target":"{target:#x}",
                "calldata":"0x12345678aa",
                "value":"0",
                "gas_limit":500000,
                "max_fee_per_gas":"100",
                "max_priority_fee_per_gas":"1",
                "deadline_ms":10000,
                "profit_token":"{profit_token:#x}",
                "min_profit_wei":"100",
                "require_preflight":true,
                "dry_run":false,
                "broadcast_lane":"private_relay"
            }}"#,
            target = address(0x11),
            profit_token = address(0x22)
        );
        let policy_json = format!(
            r#"{{
                "expected_chain_id":42161,
                "min_profit_wei":"50",
                "max_gas_limit":1000000,
                "require_preflight":true,
                "require_live_sources":true,
                "min_gate_count":2,
                "min_deadline_ms_from_now":1000,
                "allowed_targets":["{target:#x}"],
                "allowed_lanes":["private_relay"]
            }}"#,
            target = address(0x11)
        );
        let sources_json =
            r#"[{"name":"degenbot.uniswapx.order","block_number":123,"observed_at_ns":1}]"#;
        let gates_json =
            r#"[{"name":"quote_gate","admitted":true},{"name":"simulation_gate","admitted":true}]"#;
        let simulation_json = r#"{"success":true,"expected_profit_wei":"150","gas_used":321000,"state_read_count":12}"#;
        let report_json = compose_engine_job_json(
            &plan_json,
            &policy_json,
            sources_json,
            gates_json,
            simulation_json,
            8_000,
        )
        .unwrap();
        let report: Value = serde_json::from_str(&report_json).unwrap();
        assert_eq!(report["strategy"], "uniswapx_flash_fill");
        assert_eq!(report["source_count"], 1);
        assert_eq!(report["gate_count"], 2);
        assert_eq!(report["submit"], true);
    }
}
