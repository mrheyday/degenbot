use alloy::primitives::{Address, Bytes, B256, I256, U256};
use serde::{Deserialize, Serialize};
use std::fmt;

use crate::monitor::sequencer_feed::FrontrunCandidate;

// ---------------------------------------------------------------------------
// Wire-shape helpers
// ---------------------------------------------------------------------------

fn deserialize_string_or_u64<'de, D>(deserializer: D) -> Result<u64, D::Error>
where
    D: serde::Deserializer<'de>,
{
    use serde::de::{self, Visitor};
    struct Helper;
    impl<'de> Visitor<'de> for Helper {
        type Value = u64;
        fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
            f.write_str("u64 or numeric string")
        }
        fn visit_u64<E: de::Error>(self, v: u64) -> Result<u64, E> {
            Ok(v)
        }
        fn visit_i64<E: de::Error>(self, v: i64) -> Result<u64, E> {
            u64::try_from(v).map_err(|_| de::Error::custom("negative"))
        }
        fn visit_str<E: de::Error>(self, v: &str) -> Result<u64, E> {
            v.parse::<u64>()
                .map_err(|e| de::Error::custom(format!("parse {e}")))
        }
    }
    deserializer.deserialize_any(Helper)
}

#[allow(clippy::large_enum_variant)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Message {
    Opportunity(Opportunity),
    PoolUpdate(PoolState),
    Heartbeat {
        ts_ms: u64,
    },
    Error(ErrorInfo),
    Plan(Plan),
    Settlement(Settlement),
    FrontrunCandidate(FrontrunCandidate),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Opportunity {
    pub id: String,
    #[serde(deserialize_with = "deserialize_string_or_u64")]
    pub detected_at_ns: u64,
    pub kind: OpportunityKind,
    pub token_in: Address,
    pub token_out: Address,
    pub amount_in: U256,
    pub expected_amount_out: U256,
    pub estimated_profit_wei: U256,
    pub flash_token: Address,
    pub flash_amount: U256,
    pub path: Vec<SwapStep>,
    pub pool_addresses: Vec<Address>,
}

#[allow(clippy::large_enum_variant)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OpportunityKind {
    NativeArb,
    CoWIntentFillable { order_uid: B256 },
    UniswapXFillable { order_hash: B256 },
    AcrossFillable { order_id: B256 },
    MorphoLiquidation(MorphoLiquidationOpportunityPayload),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MorphoLiquidationOpportunityPayload {
    pub market_id: B256,
    pub market_params: MorphoMarketParams,
    pub borrower: Address,
    pub repaid_shares: U256,
    pub expected_seized_assets: U256,
    pub ranking_score_bps: U256,
    pub risk_cost_wei: U256,
    pub bad_debt_mode: MorphoBadDebtMode,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MorphoMarketParams {
    pub loan_token: Address,
    pub collateral_token: Address,
    pub oracle: Address,
    pub irm: Address,
    pub lltv: U256,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum MorphoBadDebtMode {
    None,
    AllowProfitable,
    RealizeAnyway,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct V4PoolKey {
    pub currency0: Address,
    pub currency1: Address,
    pub fee: u32,
    pub tick_spacing: i32,
    pub hooks: Address,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SwapStep {
    pub pool: Address,
    pub token_in: Address,
    pub token_out: Address,
    pub amount_in: U256,
    pub amount_out_min: U256,
    pub zero_for_one: bool,
    pub dex: DexKind,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub fee: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub pool_key: Option<V4PoolKey>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub hook_data: Option<Bytes>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub deadline: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub token_in_idx: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub token_out_idx: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub is_legacy: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DexKind {
    UniswapV2,
    UniswapV3,
    UniswapV4,
    UniswapUniversalRouter,
    PancakeSwapV2,
    PancakeSwapV3,
    SushiSwapV2,
    SushiSwapV3,
    CamelotV2,
    CamelotV3,
    CamelotAlgebraV4,
    FraxSwap,
    BalancerV2,
    BalancerV3,
    Curve,
    CurveNG,
    Aerodrome,
    Solidly,
    RamsesV2,
    Algebra,
    KyberElastic,
    MaverickV2,
    DodoPmm,
    FluidDex,
    LFJLiquidityBook,
    GMXV2,
    Wombat,
    Bebop,
    Hashflow,
    WooFi,
    OKXDex,
    Enso,
    Squid,
    LiFi,
    Rango,
    Rubic,
    Native,
    OneInchV6,
    ZeroX,
    ParaSwap,
    Odos,
    KyberSwap,
    OpenOcean,
    AggregatorV6,
    MorphoBlue,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PoolState {
    pub address: Address,
    pub block_number: u64,
    pub reserves: Reserves,
}

#[allow(non_snake_case)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Reserves {
    V2 {
        reserve0: U256,
        reserve1: U256,
    },
    V3 {
        sqrt_price_x96: U256,
        liquidity: u128,
        tick: i32,
    },
    V4 {
        key: B256,
        sqrt_price_x96: U256,
        liquidity: u128,
        tick: i32,
    },
    Curve {
        balances: Vec<U256>,
        A: U256,
        fee: u32,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorInfo {
    pub code: String,
    pub message: String,
    pub context: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum PlanKind {
    NativeArb,
    InternalMatch,
    FourLeg,
    Liquidation,
    CowSolverBid,
    UniswapXFill,
    UniswapXFlashFill,
    AcrossFill,
    AcrossIntentFill,
    MorphoLiquidation,
    OneInchFusionGap,
    OracleSandwich,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GasEnvelope {
    pub max_fee_per_gas_wei: U256,
    pub max_priority_fee_per_gas_wei: U256,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Eip7702Delegation {
    pub authority: Address,
    pub delegate_address: Address,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum Lane {
    Default,
    PrivateRelay,
    Kairos,
    Timeboost,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Plan {
    pub trace_id: String,
    pub opportunity_id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub admission_hash: Option<B256>,
    pub kind: PlanKind,
    pub target: Address,
    pub calldata: Bytes,
    pub value: U256,
    pub gas_limit: u64,
    pub gas_envelope: GasEnvelope,
    pub deadline_ms: u64,
    pub require_preflight: bool,
    pub expected_balance_delta_floor: I256,
    pub profit_token: Address,
    pub submission_lane: Lane,
    pub timeboost_bid_wei: Option<U256>,
    #[serde(default)]
    pub dry_run: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub eip7702: Option<Eip7702Delegation>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum SettlementStatus {
    PreflightFailed,
    PreflightPassed,
    BroadcastFailed,
    Submitted,
    Included,
    Reverted,
    Replaced,
    Dropped,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct Timestamps {
    pub received_ns: u64,
    pub preflight_ns: Option<u64>,
    pub broadcast_ns: Option<u64>,
    pub included_ns: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Settlement {
    pub trace_id: String,
    pub status: SettlementStatus,
    pub tx_hash: Option<B256>,
    pub block_number: Option<u64>,
    pub effective_gas_price_wei: Option<U256>,
    pub gas_used: Option<u64>,
    pub realized_balance_delta: Option<I256>,
    pub revert_reason: Option<String>,
    pub timestamps: Timestamps,
    #[serde(default)]
    pub dry_run: bool,
}
