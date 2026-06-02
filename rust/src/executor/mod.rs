//! Executor — the Rust-side broadcasting layer of ADR-026.
//!
//! Sole owner of `PRIVATE_KEY` (per the three-layer split). Receives `Plan`s
//! from the TypeScript coordinator over the existing UDS, runs a mandatory
//! REVM pre-flight when `Plan.require_preflight` is true, signs and broadcasts
//! through the configured lane (default RPC / Kairos / Timeboost), watches
//! inclusion, and emits `Settlement`s back to the coordinator.
//!
//! Current implementation: `MockBackend` keeps the actor state machine
//! unit-testable; `LiveBackend` owns the signer, per-lane Alloy providers,
//! pending nonce cache, pre/post balance accounting, and inclusion watcher.
//! `serve_message_bus` routes `Message::Plan` envelopes from the coordinator
//! bus into the executor queue and mirrors `Message::Settlement` back out.

pub mod gas;
pub mod inclusion;
pub mod lane;
pub mod nonce;
pub mod preflight;
pub mod signer;
pub mod tx_builder;

use std::num::NonZeroU32;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use alloy::network::{Ethereum, EthereumWallet, TransactionBuilder};
use alloy::primitives::{Address, Bytes, B256, I256, U256};
use alloy::providers::{DynProvider, Provider, ProviderBuilder};
use alloy::rpc::types::TransactionRequest;
use alloy::sol;
use alloy::sol_types::SolCall;
use dashmap::DashMap;
use governor::{DefaultDirectRateLimiter, Quota, RateLimiter};
use thiserror::Error;
use tokio::sync::{broadcast, mpsc};
use tracing::{debug, error, info, warn};

use crate::monitor::{Lane, Message, Plan, Settlement, SettlementStatus, Timestamps};

use self::lane::LaneEndpoints;
use self::nonce::PendingNonceCache;
use self::signer::ExecutorSigner;

sol! {
    #[allow(missing_docs)]
    interface IERC20Balance {
        function balanceOf(address owner) external view returns (uint256);
    }
}

const NONCE_CACHE_TTL_MS: u64 = 1_000;

/// Bag of side-effects the actor depends on. The trait carves the boundary
/// between the actor's deterministic state machine and the live blockchain
/// integrations (RPC, signer, REVM) so we can test the former without the
/// latter. `LiveBackend` (Phase 1b) and `MockBackend` (this module) both
/// implement it.
#[async_trait::async_trait]
pub trait ExecutorBackend: Send + Sync + 'static {
    /// REVM pre-flight. Returns the simulated balance delta on
    /// `plan.profit_token` after executing `plan.calldata` against
    /// `plan.target` from a forked-state snapshot at the latest block.
    async fn preflight(&self, plan: &Plan) -> Result<I256, PreflightError>;

    /// Sign and submit the Plan as an EIP-1559 transaction through the
    /// configured lane. Returns the tx hash on success.
    async fn sign_and_submit(&self, plan: &Plan) -> Result<B256, SubmitError>;

    /// Wait for the tx to be mined OR the deadline to elapse. Returns the
    /// inclusion receipt, or signals replacement / drop / timeout.
    async fn await_inclusion(
        &self,
        tx_hash: B256,
        deadline_ms: u64,
    ) -> Result<InclusionOutcome, InclusionError>;
}

#[derive(Debug, Clone)]
pub struct InclusionReceipt {
    pub block_number: u64,
    pub gas_used: u64,
    pub effective_gas_price_wei: U256,
    pub realized_balance_delta: I256,
    pub status: bool,
    pub revert_reason: Option<String>,
}

/// Three terminal outcomes of `await_inclusion`. Mirrors the relevant
/// `SettlementStatus` variants.
#[derive(Debug, Clone)]
pub enum InclusionOutcome {
    Mined(InclusionReceipt),
    /// A different tx with the same nonce was mined first.
    Replaced,
    /// `deadline_ms` elapsed; the pending tx was never mined.
    Dropped,
}

#[derive(Debug, Error)]
pub enum PreflightError {
    #[error("simulated balance delta {actual} below floor {floor} on profit_token")]
    DeltaBelowFloor { actual: I256, floor: I256 },
    #[error("simulated tx reverted: {0}")]
    SimulationReverted(String),
    #[error("REVM fork failed: {0}")]
    ForkFailed(String),
    #[error("preflight backend unavailable: {0}")]
    Unavailable(String),
}

#[derive(Debug, Error)]
pub enum SubmitError {
    #[error("RPC submission failed: {0}")]
    Rpc(String),
    #[error("tx signing failed: {0}")]
    Signer(String),
    #[error("nonce error: {0}")]
    Nonce(String),
    #[error("gas error: {0}")]
    Gas(String),
}

#[derive(Debug, Error)]
pub enum InclusionError {
    #[error("RPC error while polling: {0}")]
    Rpc(String),
}

// ---------------------------------------------------------------------------
// Actor loop
// ---------------------------------------------------------------------------

/// Drive the executor state machine.
///
/// One Plan pulled off `plan_rx` produces one or more `Settlement`s on
/// `settlement_tx`, terminating in either Included / Reverted / Replaced /
/// Dropped / PreflightFailed / BroadcastFailed. The function returns when
/// `plan_rx` is closed.
///
/// `settlement_tx` is the engine's existing outbound broadcast bus (per
/// `engine/src/main.rs`). We push `Message::Settlement(_)` onto it; the IPC
/// server fans those out to every connected coordinator subscriber.
pub async fn serve<B: ExecutorBackend>(
    backend: B,
    plan_rx: mpsc::Receiver<Plan>,
    settlement_tx: broadcast::Sender<Message>,
) {
    serve_with_rate_ceiling(backend, plan_rx, settlement_tx, 0).await;
}

/// Bridge the coordinator broadcast bus into the executor actor.
///
/// The IPC layer publishes heterogeneous [`Message`] envelopes. This bridge
/// filters only `Message::Plan` into the executor's private `mpsc` queue and
/// reuses the same settlement broadcast bus for `Message::Settlement` output.
pub async fn serve_message_bus<B: ExecutorBackend>(
    backend: B,
    mut inbound_rx: broadcast::Receiver<Message>,
    settlement_tx: broadcast::Sender<Message>,
    tx_rate_ceiling_per_min: u32,
) {
    let (plan_tx, plan_rx) = mpsc::channel::<Plan>(1024);
    let executor = tokio::spawn(serve_with_rate_ceiling(
        backend,
        plan_rx,
        settlement_tx,
        tx_rate_ceiling_per_min,
    ));

    loop {
        match inbound_rx.recv().await {
            Ok(Message::Plan(plan)) => {
                if let Err(err) = plan_tx.send(plan).await {
                    warn!(
                        target: "engine::executor",
                        error = %err,
                        "executor plan channel closed while routing bus message"
                    );
                    break;
                }
            }
            Ok(_) => {}
            Err(broadcast::error::RecvError::Lagged(skipped)) => {
                warn!(
                    target: "engine::executor",
                    skipped,
                    "executor inbound bus lagged; continuing with latest messages"
                );
            }
            Err(broadcast::error::RecvError::Closed) => break,
        }
    }

    drop(plan_tx);
    if let Err(err) = executor.await {
        error!(
            target: "engine::executor",
            error = %err,
            "executor actor task failed while draining message bus"
        );
    }
}

/// Drive the executor with a tx-rate ceiling (CLAUDE.md submitter
/// kill-switch). A plan whose broadcast would exceed `tx_rate_ceiling_per_min`
/// transactions per minute is blocked and emitted as `Dropped` rather than
/// broadcast. `tx_rate_ceiling_per_min == 0` disables the ceiling.
pub async fn serve_with_rate_ceiling<B: ExecutorBackend>(
    backend: B,
    mut plan_rx: mpsc::Receiver<Plan>,
    settlement_tx: broadcast::Sender<Message>,
    tx_rate_ceiling_per_min: u32,
) {
    let ceiling = NonZeroU32::new(tx_rate_ceiling_per_min);
    let rate_limiter = ceiling.map(|n| RateLimiter::direct(Quota::per_minute(n)));
    match ceiling {
        Some(n) => info!(
            target: "engine::executor",
            ceiling_per_min = n.get(),
            "executor actor started (tx-rate ceiling active)"
        ),
        None => info!(
            target: "engine::executor",
            "executor actor started (no tx-rate ceiling)"
        ),
    }
    while let Some(plan) = plan_rx.recv().await {
        let trace_id = plan.trace_id.clone();
        debug!(target: "engine::executor", trace_id = %trace_id, "received plan");
        run_one_plan(&backend, plan, &settlement_tx, rate_limiter.as_ref()).await;
    }
    info!(target: "engine::executor", "executor actor shutting down (plan channel closed)");
}

#[cfg_attr(feature = "hotpath", hotpath::measure)]
async fn run_one_plan<B: ExecutorBackend>(
    backend: &B,
    plan: Plan,
    settlement_tx: &broadcast::Sender<Message>,
    rate_limiter: Option<&DefaultDirectRateLimiter>,
) {
    let trace_id = plan.trace_id.clone();
    let dry_run = plan.dry_run;
    let received_ns = ts_now_ns();
    let mut timestamps = Timestamps {
        received_ns,
        ..Default::default()
    };

    // Builder for a Settlement that propagates trace_id + dry_run + the
    // current timestamps clone — keeps the per-stage emissions readable.
    let mk = |status: SettlementStatus,
              tx_hash: Option<B256>,
              ts: Timestamps,
              extras: SettlementExtras|
     -> Settlement {
        Settlement {
            trace_id: trace_id.clone(),
            status,
            tx_hash,
            block_number: extras.block_number,
            effective_gas_price_wei: extras.effective_gas_price_wei,
            gas_used: extras.gas_used,
            realized_balance_delta: extras.realized_balance_delta,
            revert_reason: extras.revert_reason,
            timestamps: ts,
            dry_run,
        }
    };

    // 1. Deadline check before doing anything else.
    let now_ms = received_ns / 1_000_000;
    if plan.deadline_ms < now_ms {
        warn!(
            target: "engine::executor",
            trace_id = %trace_id,
            deadline_ms = plan.deadline_ms,
            now_ms,
            "plan deadline already passed; emitting Dropped"
        );
        emit(
            settlement_tx,
            mk(
                SettlementStatus::Dropped,
                None,
                timestamps,
                SettlementExtras {
                    revert_reason: Some("deadline expired before broadcast".to_string()),
                    ..Default::default()
                },
            ),
        );
        return;
    }

    // 1.5 Admission/provenance and lane-economics gate. Dry runs may omit
    // admission artifacts because they never sign or broadcast.
    if let Err(reason) = validate_submission_policy(&plan) {
        warn!(
            target: "engine::executor",
            trace_id = %trace_id,
            reason = %reason,
            "plan rejected by submission policy"
        );
        emit(
            settlement_tx,
            mk(
                SettlementStatus::Dropped,
                None,
                timestamps,
                SettlementExtras {
                    revert_reason: Some(reason),
                    ..Default::default()
                },
            ),
        );
        return;
    }

    // 2. Pre-flight. Always runs when dry_run=true (the whole point) or
    //    when require_preflight=true. Otherwise skipped.
    let preflight_required = plan.dry_run || plan.require_preflight;
    if preflight_required {
        match backend.preflight(&plan).await {
            Ok(delta) => {
                timestamps.preflight_ns = Some(ts_now_ns());
                if delta < plan.expected_balance_delta_floor {
                    let err = PreflightError::DeltaBelowFloor {
                        actual: delta,
                        floor: plan.expected_balance_delta_floor,
                    };
                    warn!(
                        target: "engine::executor",
                        trace_id = %trace_id,
                        error = %err,
                        "preflight delta below declared floor"
                    );
                    emit(
                        settlement_tx,
                        mk(
                            SettlementStatus::PreflightFailed,
                            None,
                            timestamps,
                            SettlementExtras {
                                revert_reason: Some(err.to_string()),
                                ..Default::default()
                            },
                        ),
                    );
                    return;
                }
                debug!(
                    target: "engine::executor",
                    trace_id = %trace_id,
                    delta = ?delta,
                    "preflight passed"
                );
            }
            Err(err) => {
                warn!(
                    target: "engine::executor",
                    trace_id = %trace_id,
                    error = %err,
                    "preflight rejected"
                );
                timestamps.preflight_ns = Some(ts_now_ns());
                emit(
                    settlement_tx,
                    mk(
                        SettlementStatus::PreflightFailed,
                        None,
                        timestamps,
                        SettlementExtras {
                            revert_reason: Some(err.to_string()),
                            ..Default::default()
                        },
                    ),
                );
                return;
            }
        }
    }

    // 2.5 Dry-run early exit — no broadcast, no inclusion watch.
    if plan.dry_run {
        debug!(
            target: "engine::executor",
            trace_id = %trace_id,
            "dry_run=true; emitting PreflightPassed without broadcast"
        );
        emit(
            settlement_tx,
            mk(
                SettlementStatus::PreflightPassed,
                None,
                timestamps,
                SettlementExtras::default(),
            ),
        );
        return;
    }

    // 2.6 tx-rate ceiling — CLAUDE.md submitter kill-switch. A would-be
    //     broadcast over the configured per-minute ceiling is blocked and
    //     the Plan is Dropped. Dry runs return above, so they cost no
    //     budget; only real broadcast attempts draw on the ceiling.
    if let Some(limiter) = rate_limiter {
        if limiter.check().is_err() {
            warn!(
                target: "engine::executor",
                trace_id = %trace_id,
                "tx-rate ceiling exceeded; blocking broadcast"
            );
            emit(
                settlement_tx,
                mk(
                    SettlementStatus::Dropped,
                    None,
                    timestamps,
                    SettlementExtras {
                        revert_reason: Some(
                            "tx-rate ceiling exceeded; submission blocked by kill-switch"
                                .to_string(),
                        ),
                        ..Default::default()
                    },
                ),
            );
            return;
        }
    }

    // 3. Sign + submit.
    let tx_hash = match backend.sign_and_submit(&plan).await {
        Ok(h) => {
            timestamps.broadcast_ns = Some(ts_now_ns());
            h
        }
        Err(err) => {
            error!(
                target: "engine::executor",
                trace_id = %trace_id,
                error = %err,
                "broadcast failed"
            );
            emit(
                settlement_tx,
                mk(
                    SettlementStatus::BroadcastFailed,
                    None,
                    timestamps,
                    SettlementExtras {
                        revert_reason: Some(err.to_string()),
                        ..Default::default()
                    },
                ),
            );
            return;
        }
    };

    // 4. Submitted Settlement (intermediate; not terminal).
    emit(
        settlement_tx,
        mk(
            SettlementStatus::Submitted,
            Some(tx_hash),
            timestamps.clone(),
            SettlementExtras::default(),
        ),
    );

    // 5. Await inclusion.
    match backend.await_inclusion(tx_hash, plan.deadline_ms).await {
        Ok(InclusionOutcome::Mined(receipt)) => {
            timestamps.included_ns = Some(ts_now_ns());
            let status = if receipt.status {
                SettlementStatus::Included
            } else {
                SettlementStatus::Reverted
            };
            emit(
                settlement_tx,
                mk(
                    status,
                    Some(tx_hash),
                    timestamps,
                    SettlementExtras {
                        block_number: Some(receipt.block_number),
                        effective_gas_price_wei: Some(receipt.effective_gas_price_wei),
                        gas_used: Some(receipt.gas_used),
                        realized_balance_delta: Some(receipt.realized_balance_delta),
                        revert_reason: receipt.revert_reason,
                    },
                ),
            );
        }
        Ok(InclusionOutcome::Replaced) => {
            emit(
                settlement_tx,
                mk(
                    SettlementStatus::Replaced,
                    Some(tx_hash),
                    timestamps,
                    SettlementExtras::default(),
                ),
            );
        }
        Ok(InclusionOutcome::Dropped) => {
            emit(
                settlement_tx,
                mk(
                    SettlementStatus::Dropped,
                    Some(tx_hash),
                    timestamps,
                    SettlementExtras {
                        revert_reason: Some("deadline elapsed without inclusion".to_string()),
                        ..Default::default()
                    },
                ),
            );
        }
        Err(err) => {
            error!(
                target: "engine::executor",
                trace_id = %trace_id,
                error = %err,
                "inclusion-watch failed"
            );
            emit(
                settlement_tx,
                mk(
                    SettlementStatus::BroadcastFailed,
                    Some(tx_hash),
                    timestamps,
                    SettlementExtras {
                        revert_reason: Some(format!("inclusion watch error: {err}")),
                        ..Default::default()
                    },
                ),
            );
        }
    }
}

/// Bundle of optional Settlement fields used by the `mk` builder closure
/// in `run_one_plan`. Each per-stage emission populates only the fields
/// relevant to that stage; the rest default to `None`.
#[derive(Default)]
struct SettlementExtras {
    block_number: Option<u64>,
    effective_gas_price_wei: Option<U256>,
    gas_used: Option<u64>,
    realized_balance_delta: Option<I256>,
    revert_reason: Option<String>,
}

fn emit(tx: &broadcast::Sender<Message>, s: Settlement) {
    // `send` returns Err iff there are no receivers — common before any
    // coordinator connects. Trace and continue.
    if let Err(err) = tx.send(Message::Settlement(s)) {
        tracing::trace!(target: "engine::executor", err = ?err, "no subscribers for settlement");
    }
}

fn ts_now_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0)
}

fn validate_submission_policy(plan: &Plan) -> Result<(), String> {
    if plan.dry_run {
        return Ok(());
    }

    match plan.admission_hash {
        Some(hash) if hash != B256::ZERO => {}
        _ => {
            return Err(
                "missing or zero admission_hash; non-dry-run execution requires sealed provenance"
                    .to_string(),
            );
        }
    }

    let timeboost_bid = plan.timeboost_bid_wei.unwrap_or(U256::ZERO);
    match plan.submission_lane {
        Lane::Timeboost => {
            if timeboost_bid == U256::ZERO {
                return Err(
                    "timeboost_bid_wei must be positive when submission_lane=Timeboost".to_string(),
                );
            }
            if !plan.expected_balance_delta_floor.is_positive() {
                return Err("Timeboost bid requires a positive expected profit floor".to_string());
            }
            let profit_floor = plan.expected_balance_delta_floor.into_raw();
            if timeboost_bid >= profit_floor {
                return Err(format!(
                    "timeboost_bid_wei {timeboost_bid} must stay below profit floor {profit_floor}"
                ));
            }
        }
        _ if timeboost_bid > U256::ZERO => {
            return Err("timeboost_bid_wei is only valid on the Timeboost lane".to_string());
        }
        _ => {}
    }

    Ok(())
}

// ---------------------------------------------------------------------------
// MockBackend — used by both the unit tests below and by future integration
// harnesses that want to exercise the actor without a live RPC.
// ---------------------------------------------------------------------------

/// Test/integration backend with knobs for each phase. Each closure-typed
/// field is invoked when the corresponding actor stage runs.
type PreflightFn = std::sync::Arc<dyn Fn(&Plan) -> Result<I256, PreflightError> + Send + Sync>;
type SubmitFn = std::sync::Arc<dyn Fn(&Plan) -> Result<B256, SubmitError> + Send + Sync>;
type InclusionFn =
    std::sync::Arc<dyn Fn(B256) -> Result<InclusionOutcome, InclusionError> + Send + Sync>;

#[derive(Clone)]
pub struct MockBackend {
    pub preflight_result: PreflightFn,
    pub submit_result: SubmitFn,
    pub inclusion_result: InclusionFn,
}

impl MockBackend {
    /// Default happy-path: preflight returns `floor + 1`, submit returns a
    /// deterministic hash, inclusion mines at block 0xDEAD with a
    /// realized-delta matching the floor.
    pub fn happy() -> Self {
        Self {
            preflight_result: std::sync::Arc::new(|plan| {
                Ok(plan.expected_balance_delta_floor + I256::ONE)
            }),
            submit_result: std::sync::Arc::new(|plan| {
                let mut bytes = [0u8; 32];
                bytes[..plan.trace_id.len().min(32)]
                    .copy_from_slice(&plan.trace_id.as_bytes()[..plan.trace_id.len().min(32)]);
                Ok(B256::from(bytes))
            }),
            inclusion_result: std::sync::Arc::new(|_h| {
                Ok(InclusionOutcome::Mined(InclusionReceipt {
                    block_number: 0xDEAD,
                    gas_used: 100_000,
                    effective_gas_price_wei: U256::from(1_500_000_000_u64),
                    realized_balance_delta: I256::from_raw(U256::from(1_000_000_000_000_000_u64)),
                    status: true,
                    revert_reason: None,
                }))
            }),
        }
    }
}

#[async_trait::async_trait]
impl ExecutorBackend for MockBackend {
    async fn preflight(&self, plan: &Plan) -> Result<I256, PreflightError> {
        (self.preflight_result)(plan)
    }
    async fn sign_and_submit(&self, plan: &Plan) -> Result<B256, SubmitError> {
        (self.submit_result)(plan)
    }
    async fn await_inclusion(
        &self,
        tx_hash: B256,
        _deadline_ms: u64,
    ) -> Result<InclusionOutcome, InclusionError> {
        (self.inclusion_result)(tx_hash)
    }
}

// ---------------------------------------------------------------------------
// LiveBackend — production implementation (Phase 1b)
// ---------------------------------------------------------------------------

/// Production executor backend: real `PrivateKeySigner` + real Alloy provider
/// + per-lane RPC dispatch + pending-nonce cache. Owns the sole copy of the
///   signing key in this process.
///
/// Construction takes the default-lane RPC URL and (optionally) Kairos /
/// Timeboost overrides. Each configured lane gets its own provider so
/// `Plan.submission_lane` is honored at submission and inclusion-watch time.
#[derive(Clone)]
pub struct LiveBackend {
    signer: ExecutorSigner,
    providers: LaneProviderSet,
    lane_endpoints: LaneEndpoints,
    nonce: PendingNonceCache,
    nonce_refresh: Arc<tokio::sync::Mutex<()>>,
    submitted: Arc<DashMap<B256, SubmittedTxContext>>,
}

impl LiveBackend {
    /// Build a LiveBackend pointing at the supplied default-lane HTTP RPC.
    /// Reads `PRIVATE_KEY` from env via `ExecutorSigner::from_env`.
    pub async fn from_env(lane_endpoints: LaneEndpoints) -> Result<Self, SubmitError> {
        let signer = ExecutorSigner::from_env()?;
        Self::with_signer(signer, lane_endpoints).await
    }

    /// Build with an explicit signer. Tests use this to inject anvil's
    /// pre-funded test account without touching process env.
    pub async fn with_signer(
        signer: ExecutorSigner,
        lane_endpoints: LaneEndpoints,
    ) -> Result<Self, SubmitError> {
        let wallet = EthereumWallet::from(signer.inner().clone());
        let providers = LaneProviderSet::connect(wallet, &lane_endpoints).await?;

        Ok(Self {
            signer,
            providers,
            lane_endpoints,
            nonce: PendingNonceCache::new(),
            nonce_refresh: Arc::new(tokio::sync::Mutex::new(())),
            submitted: Arc::new(DashMap::new()),
        })
    }

    /// Address the executor signs from.
    pub fn address(&self) -> alloy::primitives::Address {
        self.signer.address()
    }

    /// Underlying provider — exposed for the integration test to query state
    /// directly. Production callers should not need this.
    pub fn provider(&self) -> &DynProvider {
        self.providers.default()
    }

    /// Configured lane endpoints.
    pub fn lane_endpoints(&self) -> &LaneEndpoints {
        &self.lane_endpoints
    }

    fn provider_for_lane(&self, lane: &Lane) -> &DynProvider {
        self.providers.provider_for(lane)
    }

    async fn next_nonce(&self, provider: &DynProvider) -> Result<u64, SubmitError> {
        if let Some(nonce) = self
            .nonce
            .take_and_increment_if_fresh(ts_now_ms(), NONCE_CACHE_TTL_MS)
        {
            return Ok(nonce);
        }

        let _guard = self.nonce_refresh.lock().await;
        if let Some(nonce) = self
            .nonce
            .take_and_increment_if_fresh(ts_now_ms(), NONCE_CACHE_TTL_MS)
        {
            return Ok(nonce);
        }

        let refreshed_at = ts_now_ms();
        let pending = provider
            .get_transaction_count(self.signer.address())
            .pending()
            .await
            .map_err(|e| SubmitError::Nonce(format!("get pending nonce: {e}")))?;
        self.nonce.prime(pending, refreshed_at);
        self.nonce
            .take_and_increment_if_fresh(ts_now_ms(), NONCE_CACHE_TTL_MS)
            .ok_or_else(|| SubmitError::Nonce("pending nonce cache did not prime".to_string()))
    }
}

#[derive(Clone)]
struct LaneProviderSet {
    default: DynProvider,
    private_relay: Option<DynProvider>,
    kairos: Option<DynProvider>,
    timeboost: Option<DynProvider>,
}

impl LaneProviderSet {
    async fn connect(
        wallet: EthereumWallet,
        endpoints: &LaneEndpoints,
    ) -> Result<Self, SubmitError> {
        let default = connect_wallet_provider(&wallet, "default", &endpoints.default_http).await?;
        let private_relay = connect_optional_wallet_provider(
            &wallet,
            "private_relay",
            endpoints.private_relay_http.as_deref(),
        )
        .await?;
        let kairos =
            connect_optional_wallet_provider(&wallet, "kairos", endpoints.kairos_http.as_deref())
                .await?;
        let timeboost = connect_optional_wallet_provider(
            &wallet,
            "timeboost",
            endpoints.timeboost_http.as_deref(),
        )
        .await?;

        Ok(Self {
            default,
            private_relay,
            kairos,
            timeboost,
        })
    }

    fn default(&self) -> &DynProvider {
        &self.default
    }

    fn provider_for(&self, lane: &Lane) -> &DynProvider {
        match lane {
            Lane::Default => &self.default,
            Lane::PrivateRelay => self.private_relay.as_ref().unwrap_or(&self.default),
            Lane::Kairos => self.kairos.as_ref().unwrap_or(&self.default),
            Lane::Timeboost => self.timeboost.as_ref().unwrap_or(&self.default),
        }
    }
}

#[derive(Debug, Clone)]
struct SubmittedTxContext {
    from: Address,
    nonce: u64,
    profit_token: Address,
    lane: Lane,
    pre_submit_balance: U256,
}

async fn connect_optional_wallet_provider(
    wallet: &EthereumWallet,
    lane_name: &str,
    endpoint: Option<&str>,
) -> Result<Option<DynProvider>, SubmitError> {
    match endpoint {
        Some(url) => Ok(Some(connect_wallet_provider(wallet, lane_name, url).await?)),
        None => Ok(None),
    }
}

async fn connect_wallet_provider(
    wallet: &EthereumWallet,
    lane_name: &str,
    endpoint: &str,
) -> Result<DynProvider, SubmitError> {
    let provider = ProviderBuilder::new()
        .wallet(wallet.clone())
        .connect(endpoint)
        .await
        .map_err(|e| SubmitError::Rpc(format!("connect {lane_name} {endpoint}: {e}")))?;
    Ok(provider.erased())
}

async fn read_profit_balance<P>(
    provider: &P,
    token: Address,
    owner: Address,
) -> Result<U256, String>
where
    P: Provider<Ethereum>,
{
    if token == Address::ZERO {
        return provider
            .get_balance(owner)
            .await
            .map_err(|e| format!("native balance {owner}: {e}"));
    }

    let calldata = IERC20Balance::balanceOfCall { owner }.abi_encode();
    let tx = TransactionRequest::default()
        .with_to(token)
        .with_input(Bytes::from(calldata));
    let out = provider
        .call(tx)
        .await
        .map_err(|e| format!("balanceOf {token} owner {owner}: {e}"))?;
    <IERC20Balance::balanceOfCall as SolCall>::abi_decode_returns(&out)
        .map_err(|e| format!("balanceOf decode {token} owner {owner}: {e}"))
}

fn u256_diff_to_i256(post: U256, pre: U256) -> I256 {
    if post >= pre {
        I256::try_from(post - pre).unwrap_or(I256::MAX)
    } else {
        let signed = I256::try_from(pre - post).unwrap_or(I256::MAX);
        signed.checked_neg().unwrap_or(I256::MIN + I256::ONE)
    }
}

fn ts_now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

#[async_trait::async_trait]
impl ExecutorBackend for LiveBackend {
    async fn preflight(&self, plan: &Plan) -> Result<I256, PreflightError> {
        preflight::check(
            self.provider_for_lane(&plan.submission_lane),
            plan,
            self.signer.address(),
        )
        .await
    }

    async fn sign_and_submit(&self, plan: &Plan) -> Result<B256, SubmitError> {
        let provider = self.provider_for_lane(&plan.submission_lane);
        let pre_submit_balance =
            read_profit_balance(provider, plan.profit_token, self.signer.address())
                .await
                .map_err(|e| SubmitError::Rpc(format!("pre-submit balance: {e}")))?;
        let nonce = self.next_nonce(provider).await?;
        let tx = tx_builder::build_tx_request(plan).with_nonce(nonce);

        let pending = match provider.send_transaction(tx).await {
            Ok(pending) => pending,
            Err(e) => {
                self.nonce.clear();
                return Err(SubmitError::Rpc(format!("send_transaction: {e}")));
            }
        };
        let tx_hash = *pending.tx_hash();
        self.submitted.insert(
            tx_hash,
            SubmittedTxContext {
                from: self.signer.address(),
                nonce,
                profit_token: plan.profit_token,
                lane: plan.submission_lane.clone(),
                pre_submit_balance,
            },
        );
        Ok(tx_hash)
    }

    async fn await_inclusion(
        &self,
        tx_hash: B256,
        deadline_ms: u64,
    ) -> Result<InclusionOutcome, InclusionError> {
        let context = self.submitted.get(&tx_hash).map(|entry| entry.clone());
        let provider = context
            .as_ref()
            .map(|ctx| self.provider_for_lane(&ctx.lane))
            .unwrap_or_else(|| self.provider_for_lane(&Lane::Default));

        let mut outcome = match context.as_ref() {
            Some(ctx) => {
                inclusion::watch_with_replacement(
                    provider,
                    tx_hash,
                    ctx.from,
                    ctx.nonce,
                    deadline_ms,
                )
                .await?
            }
            None => inclusion::watch(provider, tx_hash, deadline_ms).await?,
        };

        if let (Some(ctx), InclusionOutcome::Mined(receipt)) = (&context, &mut outcome) {
            let post_balance = read_profit_balance(provider, ctx.profit_token, ctx.from)
                .await
                .map_err(|e| InclusionError::Rpc(format!("post-inclusion balance: {e}")))?;
            receipt.realized_balance_delta =
                u256_diff_to_i256(post_balance, ctx.pre_submit_balance);
        }

        if matches!(
            outcome,
            InclusionOutcome::Mined(_) | InclusionOutcome::Replaced | InclusionOutcome::Dropped
        ) {
            self.submitted.remove(&tx_hash);
        }

        Ok(outcome)
    }
}

// Suppress unused warnings on imports referenced only by LiveBackend's
// Alloy provider construction (some are pulled in via the ProviderBuilder
// chain rather than directly).
#[allow(dead_code)]
fn _phantom_alloy_imports() {
    let _ = std::any::TypeId::of::<Ethereum>();
    let _: Option<Arc<()>> = None;
}

// ---------------------------------------------------------------------------
// Tests — the actor state machine
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{GasEnvelope, Lane, PlanKind};
    use alloy::primitives::{address, b256, bytes};

    fn future_deadline_ms() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_millis() as u64 + 10_000)
            .unwrap_or(u64::MAX)
    }

    fn sample_plan() -> Plan {
        Plan {
            trace_id: "01HZK0Z0Z0Z0Z0Z0Z0Z0Z0Z0Z0".to_string(),
            opportunity_id: "01HZK0Z0Z0Z0Z0Z0Z0Z0Z0Z0Z0".to_string(),
            admission_hash: Some(b256!(
                "ad00000000000000000000000000000000000000000000000000000000000001"
            )),
            kind: PlanKind::Liquidation,
            target: address!("794a61358D6845594F94dc1DB02A252b5b4814aD"),
            calldata: bytes!("a9059cbb"),
            value: U256::ZERO,
            gas_limit: 800_000,
            gas_envelope: GasEnvelope {
                max_fee_per_gas_wei: U256::from(2_000_000_000_u64),
                max_priority_fee_per_gas_wei: U256::from(100_000_000_u64),
            },
            deadline_ms: future_deadline_ms(),
            require_preflight: true,
            expected_balance_delta_floor: I256::try_from(10_000_000_000_000_000_i128).unwrap(),
            profit_token: address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
            submission_lane: Lane::Kairos,
            timeboost_bid_wei: None,
            dry_run: false,
            eip7702: None,
        }
    }

    /// Drain every Settlement currently buffered on the broadcast bus.
    async fn collect_settlements(rx: &mut broadcast::Receiver<Message>) -> Vec<Settlement> {
        let mut out = Vec::new();
        // Yield to let the actor task run.
        tokio::task::yield_now().await;
        while let Ok(msg) = rx.try_recv() {
            if let Message::Settlement(s) = msg {
                out.push(s);
            }
        }
        out
    }

    #[tokio::test]
    async fn happy_path_emits_submitted_then_included() {
        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(MockBackend::happy(), plan_rx, settlement_tx));

        plan_tx.send(sample_plan()).await.unwrap();
        // Give the actor a moment to drive both stages.
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 2, "expected Submitted + Included");
        assert_eq!(settlements[0].status, SettlementStatus::Submitted);
        assert_eq!(settlements[1].status, SettlementStatus::Included);
        assert!(settlements[0].tx_hash.is_some());
        assert_eq!(settlements[0].tx_hash, settlements[1].tx_hash);
        assert!(settlements[1].block_number.is_some());
        assert!(settlements[1].timestamps.included_ns.is_some());
    }

    #[tokio::test]
    async fn non_dry_run_without_admission_hash_is_dropped_before_preflight() {
        let backend = MockBackend {
            preflight_result: std::sync::Arc::new(|_| {
                panic!("missing admission hash must be rejected before preflight")
            }),
            ..MockBackend::happy()
        };
        let mut plan = sample_plan();
        plan.admission_hash = None;

        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1);
        assert_eq!(settlements[0].status, SettlementStatus::Dropped);
        assert!(settlements[0].tx_hash.is_none());
        assert!(settlements[0]
            .revert_reason
            .as_deref()
            .unwrap_or_default()
            .contains("admission_hash"));
    }

    #[tokio::test]
    async fn dry_run_without_admission_hash_still_runs_preflight() {
        let mut plan = sample_plan();
        plan.dry_run = true;
        plan.admission_hash = None;

        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(MockBackend::happy(), plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1);
        assert_eq!(settlements[0].status, SettlementStatus::PreflightPassed);
        assert!(settlements[0].dry_run);
    }

    #[tokio::test]
    async fn timeboost_lane_requires_positive_bid_before_preflight() {
        let backend = MockBackend {
            preflight_result: std::sync::Arc::new(|_| {
                panic!("timeboost bid validation must run before preflight")
            }),
            ..MockBackend::happy()
        };
        let mut plan = sample_plan();
        plan.submission_lane = Lane::Timeboost;
        plan.timeboost_bid_wei = None;

        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1);
        assert_eq!(settlements[0].status, SettlementStatus::Dropped);
        assert!(settlements[0]
            .revert_reason
            .as_deref()
            .unwrap_or_default()
            .contains("timeboost_bid_wei"));
    }

    #[tokio::test]
    async fn timeboost_bid_must_stay_below_profit_floor() {
        let backend = MockBackend {
            preflight_result: std::sync::Arc::new(|_| {
                panic!("timeboost bid validation must run before preflight")
            }),
            ..MockBackend::happy()
        };
        let mut plan = sample_plan();
        plan.submission_lane = Lane::Timeboost;
        plan.timeboost_bid_wei = Some(U256::from(10_000_000_000_000_000_u64));

        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1);
        assert_eq!(settlements[0].status, SettlementStatus::Dropped);
        assert!(settlements[0]
            .revert_reason
            .as_deref()
            .unwrap_or_default()
            .contains("profit floor"));
    }

    #[tokio::test]
    async fn non_timeboost_lane_rejects_nonzero_timeboost_bid() {
        let backend = MockBackend {
            preflight_result: std::sync::Arc::new(|_| {
                panic!("non-timeboost bid validation must run before preflight")
            }),
            ..MockBackend::happy()
        };
        let mut plan = sample_plan();
        plan.submission_lane = Lane::Kairos;
        plan.timeboost_bid_wei = Some(U256::ONE);

        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1);
        assert_eq!(settlements[0].status, SettlementStatus::Dropped);
        assert!(settlements[0]
            .revert_reason
            .as_deref()
            .unwrap_or_default()
            .contains("Timeboost lane"));
    }

    #[tokio::test]
    async fn message_bus_routes_plan_envelopes_to_executor_and_mirrors_settlements() {
        let (inbound_tx, inbound_rx) = broadcast::channel::<Message>(64);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve_message_bus(
            MockBackend::happy(),
            inbound_rx,
            settlement_tx,
            0,
        ));

        inbound_tx.send(Message::Heartbeat { ts_ms: 1 }).unwrap();
        inbound_tx.send(Message::Plan(sample_plan())).unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(30)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(inbound_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 2, "expected Submitted + Included");
        assert_eq!(settlements[0].status, SettlementStatus::Submitted);
        assert_eq!(settlements[1].status, SettlementStatus::Included);
    }

    #[tokio::test]
    async fn tx_rate_ceiling_blocks_the_second_broadcast() {
        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        // Ceiling of 1/min: the first plan broadcasts, the second is blocked.
        let actor = tokio::spawn(serve_with_rate_ceiling(
            MockBackend::happy(),
            plan_rx,
            settlement_tx,
            1,
        ));

        plan_tx.send(sample_plan()).await.unwrap();
        plan_tx.send(sample_plan()).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(40)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        let dropped: Vec<_> = settlements
            .iter()
            .filter(|s| s.status == SettlementStatus::Dropped)
            .collect();
        assert_eq!(dropped.len(), 1, "exactly one plan must be rate-limited");
        assert!(dropped[0]
            .revert_reason
            .as_deref()
            .unwrap_or_default()
            .contains("tx-rate ceiling"));
        // The first plan still reached inclusion.
        assert!(settlements
            .iter()
            .any(|s| s.status == SettlementStatus::Included));
    }

    #[tokio::test]
    async fn zero_ceiling_disables_the_rate_limit() {
        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve_with_rate_ceiling(
            MockBackend::happy(),
            plan_rx,
            settlement_tx,
            0,
        ));

        plan_tx.send(sample_plan()).await.unwrap();
        plan_tx.send(sample_plan()).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(40)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        // No plan is rate-limited; both reach inclusion.
        assert!(!settlements
            .iter()
            .any(|s| s.status == SettlementStatus::Dropped));
        assert_eq!(
            settlements
                .iter()
                .filter(|s| s.status == SettlementStatus::Included)
                .count(),
            2
        );
    }

    #[tokio::test]
    async fn preflight_failure_emits_only_preflightfailed() {
        let backend = MockBackend {
            preflight_result: std::sync::Arc::new(|p| {
                Err(PreflightError::DeltaBelowFloor {
                    actual: I256::ZERO,
                    floor: p.expected_balance_delta_floor,
                })
            }),
            ..MockBackend::happy()
        };
        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(sample_plan()).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1, "preflight reject is terminal");
        assert_eq!(settlements[0].status, SettlementStatus::PreflightFailed);
        assert!(settlements[0].tx_hash.is_none());
        assert!(settlements[0]
            .revert_reason
            .as_deref()
            .unwrap()
            .contains("below floor"));
        assert!(settlements[0].timestamps.preflight_ns.is_some());
        assert!(settlements[0].timestamps.broadcast_ns.is_none());
    }

    #[tokio::test]
    async fn below_floor_preflight_delta_is_rejected_by_actor() {
        let backend = MockBackend {
            preflight_result: std::sync::Arc::new(|p| {
                Ok(p.expected_balance_delta_floor - I256::ONE)
            }),
            ..MockBackend::happy()
        };
        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(sample_plan()).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1);
        assert_eq!(settlements[0].status, SettlementStatus::PreflightFailed);
        assert!(settlements[0]
            .revert_reason
            .as_deref()
            .unwrap_or_default()
            .contains("below floor"));
    }

    #[tokio::test]
    async fn deadline_expired_before_broadcast_emits_dropped() {
        let mut plan = sample_plan();
        plan.deadline_ms = 1; // Far in the past.

        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(MockBackend::happy(), plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1, "deadline-drop is terminal");
        assert_eq!(settlements[0].status, SettlementStatus::Dropped);
        assert!(settlements[0].tx_hash.is_none());
        assert!(settlements[0]
            .revert_reason
            .as_deref()
            .unwrap()
            .contains("deadline expired"));
    }

    #[tokio::test]
    async fn submit_failure_emits_broadcastfailed() {
        let backend = MockBackend {
            submit_result: std::sync::Arc::new(|_p| {
                Err(SubmitError::Rpc("connection refused".to_string()))
            }),
            ..MockBackend::happy()
        };
        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(sample_plan()).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1);
        assert_eq!(settlements[0].status, SettlementStatus::BroadcastFailed);
        assert!(settlements[0].tx_hash.is_none());
        assert!(settlements[0]
            .revert_reason
            .as_deref()
            .unwrap()
            .contains("connection refused"));
    }

    #[tokio::test]
    async fn replaced_inclusion_outcome_propagates() {
        let backend = MockBackend {
            inclusion_result: std::sync::Arc::new(|_h| Ok(InclusionOutcome::Replaced)),
            ..MockBackend::happy()
        };
        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(sample_plan()).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 2, "Submitted + Replaced");
        assert_eq!(settlements[0].status, SettlementStatus::Submitted);
        assert_eq!(settlements[1].status, SettlementStatus::Replaced);
    }

    #[tokio::test]
    async fn reverted_inclusion_propagates_revert_reason() {
        let backend = MockBackend {
            inclusion_result: std::sync::Arc::new(|_h| {
                Ok(InclusionOutcome::Mined(InclusionReceipt {
                    block_number: 100,
                    gas_used: 50_000,
                    effective_gas_price_wei: U256::from(1_500_000_000_u64),
                    realized_balance_delta: I256::ZERO,
                    status: false,
                    revert_reason: Some("Executor__InsufficientProfit".to_string()),
                }))
            }),
            ..MockBackend::happy()
        };
        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(sample_plan()).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 2);
        assert_eq!(settlements[1].status, SettlementStatus::Reverted);
        assert_eq!(
            settlements[1].revert_reason.as_deref(),
            Some("Executor__InsufficientProfit")
        );
    }

    // -- LiveBackend integration test against anvil ----------------------

    /// Anvil round-trip: spawn anvil, build LiveBackend with anvil's first
    /// pre-funded test account, send a self-pay Plan, verify Submitted +
    /// Included Settlements land on the broadcast bus. Marked `#[ignore]`
    /// because it requires the `anvil` binary on the test machine; run via
    /// `cargo test --package mev-engine -- --ignored anvil_round_trip`.
    #[tokio::test]
    #[ignore]
    async fn anvil_round_trip_emits_submitted_then_included() {
        use alloy::node_bindings::Anvil;
        use alloy::primitives::{address, Bytes};

        // Anvil default key #0 — well-known test wallet, pre-funded with
        // 10000 ETH on the spawned dev chain.
        const KEY: &str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";

        let anvil = Anvil::new().chain_id(31337_u64).spawn();
        let endpoint = anvil.endpoint();

        let lane_endpoints = lane::LaneEndpoints {
            default_http: endpoint,
            ..Default::default()
        };
        let signer = signer::ExecutorSigner::from_hex(KEY).expect("anvil key parses");
        let signer_addr = signer.address();

        let backend = LiveBackend::with_signer(signer, lane_endpoints)
            .await
            .expect("backend constructs");

        // Plan: self-pay 1 wei (no calldata, no revert, deterministic).
        let plan = Plan {
            trace_id: "anvil-rt-01".to_string(),
            opportunity_id: "anvil-rt-01".to_string(),
            admission_hash: Some(b256!(
                "ad00000000000000000000000000000000000000000000000000000000000002"
            )),
            kind: PlanKind::NativeArb,
            target: signer_addr,
            calldata: Bytes::new(),
            value: U256::from(1_u64),
            gas_limit: 100_000,
            gas_envelope: GasEnvelope {
                max_fee_per_gas_wei: U256::from(10_000_000_000_u64), // 10 gwei
                max_priority_fee_per_gas_wei: U256::from(1_000_000_000_u64), // 1 gwei
            },
            deadline_ms: future_deadline_ms(),
            require_preflight: true,
            expected_balance_delta_floor: I256::ZERO,
            profit_token: address!("0000000000000000000000000000000000000000"),
            submission_lane: Lane::Default,
            timeboost_bid_wei: None,
            dry_run: false,
            eip7702: None,
        };

        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();

        // Anvil mines instantly per tx; allow 2s for the receipt poll cycle.
        let mut got_submitted = false;
        let mut got_included = false;
        let timeout = tokio::time::Instant::now() + std::time::Duration::from_secs(5);

        while tokio::time::Instant::now() < timeout {
            tokio::time::sleep(std::time::Duration::from_millis(100)).await;
            while let Ok(Message::Settlement(s)) = settlement_rx.try_recv() {
                match s.status {
                    SettlementStatus::Submitted => {
                        got_submitted = true;
                        assert!(s.tx_hash.is_some());
                    }
                    SettlementStatus::Included => {
                        got_included = true;
                        assert!(s.block_number.is_some());
                        assert!(s.timestamps.included_ns.is_some());
                    }
                    ref other => panic!("unexpected status {other:?}: {:?}", s),
                }
            }
            if got_submitted && got_included {
                break;
            }
        }

        drop(plan_tx);
        actor.await.unwrap();

        assert!(got_submitted, "expected Submitted Settlement");
        assert!(got_included, "expected Included Settlement");

        // Anvil dropped at end of scope.
        drop(anvil);
    }

    #[tokio::test]
    async fn dry_run_pass_emits_only_preflightpassed() {
        let mut plan = sample_plan();
        plan.dry_run = true;

        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(MockBackend::happy(), plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(
            settlements.len(),
            1,
            "dry_run pass is terminal at PreflightPassed"
        );
        assert_eq!(settlements[0].status, SettlementStatus::PreflightPassed);
        assert!(settlements[0].dry_run);
        assert!(settlements[0].tx_hash.is_none());
        assert!(settlements[0].timestamps.preflight_ns.is_some());
        assert!(settlements[0].timestamps.broadcast_ns.is_none());
    }

    #[tokio::test]
    async fn dry_run_runs_preflight_even_when_require_preflight_is_false() {
        // dry_run=true MUST force preflight regardless of require_preflight,
        // since the whole point of dry-run is the preflight outcome.
        let mut plan = sample_plan();
        plan.dry_run = true;
        plan.require_preflight = false;

        let backend = MockBackend {
            preflight_result: std::sync::Arc::new(|_p| {
                Err(PreflightError::DeltaBelowFloor {
                    actual: I256::ZERO,
                    floor: I256::ONE,
                })
            }),
            ..MockBackend::happy()
        };
        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 1);
        assert_eq!(settlements[0].status, SettlementStatus::PreflightFailed);
        assert!(settlements[0].dry_run);
    }

    #[tokio::test]
    async fn require_preflight_false_skips_preflight_stage() {
        let backend = MockBackend {
            preflight_result: std::sync::Arc::new(|_| {
                panic!("preflight must NOT be called when require_preflight=false")
            }),
            ..MockBackend::happy()
        };
        let mut plan = sample_plan();
        plan.require_preflight = false;

        let (plan_tx, plan_rx) = mpsc::channel::<Plan>(8);
        let (settlement_tx, mut settlement_rx) = broadcast::channel::<Message>(64);
        let actor = tokio::spawn(serve(backend, plan_rx, settlement_tx));

        plan_tx.send(plan).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        let settlements = collect_settlements(&mut settlement_rx).await;

        drop(plan_tx);
        actor.await.unwrap();

        assert_eq!(settlements.len(), 2);
        assert_eq!(settlements[0].status, SettlementStatus::Submitted);
        assert!(settlements[0].timestamps.preflight_ns.is_none());
    }
}
