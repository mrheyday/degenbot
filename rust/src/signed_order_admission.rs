//! Deterministic signed-order admission helpers.
//!
//! This module captures the useful production pattern from
//! `bleu/prediction-fx-markets`: EIP-712 order hashing, cumulative fill
//! capacity, proportional minimum-output checks, and fee-split accounting.
//! It does not import that hackathon contract design or its owner-managed
//! oracle. Callers supply live-sourced state and use the returned admission
//! hash as the immutable artifact bound to downstream execution.

use alloy::primitives::{keccak256, Address, B256, U256};
use alloy::sol_types::SolValue;
use serde::Serialize;
use serde_json::Value;
use thiserror::Error;

const BPS_DENOMINATOR: u16 = 10_000;
const MAX_SOURCE_FEE_BPS: u16 = 1_000;

/// Result alias for signed-order admission.
pub type SignedOrderAdmissionResult<T> = Result<T, SignedOrderAdmissionError>;

/// Arithmetic and parsing failures that must fail closed.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum SignedOrderAdmissionError {
    /// A checked arithmetic operation overflowed.
    #[error("arithmetic overflow in {context}")]
    ArithmeticOverflow {
        /// Operation context.
        context: &'static str,
    },
    /// A checked subtraction underflowed.
    #[error("arithmetic underflow in {context}")]
    ArithmeticUnderflow {
        /// Operation context.
        context: &'static str,
    },
    /// JSON input could not be parsed or report output could not serialize.
    #[error("invalid json: {message}")]
    InvalidJson {
        /// Parser or serializer error.
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
}

/// Prediction-FX style signed order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PredictionFxOrder {
    /// Order maker.
    pub maker: Address,
    /// YES side if true, NO side if false.
    pub is_yes: bool,
    /// Total maker deposit capacity.
    pub deposit_amount: U256,
    /// Minimum shares for a full fill. Partial fills scale this value.
    pub min_shares: U256,
    /// Maker nonce.
    pub nonce: U256,
    /// Signature deadline.
    pub deadline: U256,
}

/// EIP-712 domain for the `BinaryOption` reference contract.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PredictionFxDomain {
    /// Chain id.
    pub chain_id: U256,
    /// Verifying contract.
    pub verifying_contract: Address,
}

/// Live-sourced match input.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PredictionFxMatchInput {
    /// YES-side order.
    pub yes_order: PredictionFxOrder,
    /// NO-side order.
    pub no_order: PredictionFxOrder,
    /// Fill amount against YES order.
    pub yes_fill_amount: U256,
    /// Fill amount against NO order.
    pub no_fill_amount: U256,
    /// Cumulative YES amount already filled from live state.
    pub yes_already_filled: U256,
    /// Cumulative NO amount already filled from live state.
    pub no_already_filled: U256,
    /// Current live timestamp used for admission.
    pub now: U256,
    /// Market expiry timestamp from live contract/source state.
    pub market_expiry: U256,
    /// Whether live state says the market is already resolved.
    pub market_resolved: bool,
    /// Source fee in basis points.
    pub fee_bps: u16,
    /// Creator share of the source fee in basis points.
    pub creator_fee_bps: u16,
}

/// Deterministic policy violation code.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PredictionFxViolationCode {
    /// Market already resolved.
    MarketResolved,
    /// Matching window expired.
    MarketExpired,
    /// First order is not YES-side.
    YesOrderWrongSide,
    /// Second order is not NO-side.
    NoOrderWrongSide,
    /// YES order deadline elapsed.
    YesOrderExpired,
    /// NO order deadline elapsed.
    NoOrderExpired,
    /// One or both fill amounts are zero.
    ZeroFill,
    /// One or both order deposit amounts are zero.
    ZeroOrderDeposit,
    /// YES fill exceeds remaining capacity.
    YesOverfill,
    /// NO fill exceeds remaining capacity.
    NoOverfill,
    /// Source fee exceeds policy range.
    FeeBpsOutOfRange,
    /// Creator fee exceeds policy range.
    CreatorFeeBpsOutOfRange,
    /// YES order proportional minimum shares not met.
    YesMinSharesNotMet,
    /// NO order proportional minimum shares not met.
    NoMinSharesNotMet,
}

impl PredictionFxViolationCode {
    /// Stable wire code.
    #[must_use]
    pub const fn as_wire(self) -> &'static str {
        match self {
            Self::MarketResolved => "market_resolved",
            Self::MarketExpired => "market_expired",
            Self::YesOrderWrongSide => "yes_order_wrong_side",
            Self::NoOrderWrongSide => "no_order_wrong_side",
            Self::YesOrderExpired => "yes_order_expired",
            Self::NoOrderExpired => "no_order_expired",
            Self::ZeroFill => "zero_fill",
            Self::ZeroOrderDeposit => "zero_order_deposit",
            Self::YesOverfill => "yes_overfill",
            Self::NoOverfill => "no_overfill",
            Self::FeeBpsOutOfRange => "fee_bps_out_of_range",
            Self::CreatorFeeBpsOutOfRange => "creator_fee_bps_out_of_range",
            Self::YesMinSharesNotMet => "yes_min_shares_not_met",
            Self::NoMinSharesNotMet => "no_min_shares_not_met",
        }
    }
}

/// Deterministic policy violation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PredictionFxViolation {
    /// Machine-readable code.
    pub code: PredictionFxViolationCode,
    /// Human-readable reason.
    pub message: String,
}

/// Fee split for one side of a match.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct PredictionFxFeeSplit {
    /// Gross fill amount.
    pub gross: U256,
    /// Total fee.
    pub fee: U256,
    /// Creator fee.
    pub creator_fee: U256,
    /// Resolver fee.
    pub resolver_fee: U256,
    /// Net amount after fee.
    pub net: U256,
}

/// Deterministic preview and admission artifact.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PredictionFxMatchPreview {
    /// YES order EIP-712 struct hash.
    pub yes_order_hash: B256,
    /// NO order EIP-712 struct hash.
    pub no_order_hash: B256,
    /// Fill amount against YES order.
    pub yes_fill_amount: U256,
    /// Fill amount against NO order.
    pub no_fill_amount: U256,
    /// YES remaining capacity before this fill.
    pub yes_remaining_before: U256,
    /// NO remaining capacity before this fill.
    pub no_remaining_before: U256,
    /// YES-side fee split.
    pub yes_side: PredictionFxFeeSplit,
    /// NO-side fee split.
    pub no_side: PredictionFxFeeSplit,
    /// Shares minted to YES maker.
    pub yes_shares_minted: U256,
    /// Shares minted to NO maker.
    pub no_shares_minted: U256,
    /// True when no violations were found.
    pub executable: bool,
    /// All deterministic violations, without short-circuiting.
    pub violations: Vec<PredictionFxViolation>,
    /// Stable degenbot admission artifact hash.
    pub admission_hash: B256,
}

/// JSON-safe report for Python/control-plane callers.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PredictionFxMatchReport {
    /// YES order EIP-712 struct hash.
    pub yes_order_hash: String,
    /// NO order EIP-712 struct hash.
    pub no_order_hash: String,
    /// YES fill amount.
    pub yes_fill_amount: String,
    /// NO fill amount.
    pub no_fill_amount: String,
    /// YES remaining before fill.
    pub yes_remaining_before: String,
    /// NO remaining before fill.
    pub no_remaining_before: String,
    /// YES-side fee split.
    pub yes_side: PredictionFxFeeSplitReport,
    /// NO-side fee split.
    pub no_side: PredictionFxFeeSplitReport,
    /// Shares minted to YES maker.
    pub yes_shares_minted: String,
    /// Shares minted to NO maker.
    pub no_shares_minted: String,
    /// True when no violations were found.
    pub executable: bool,
    /// All deterministic violations.
    pub violations: Vec<PredictionFxViolationReport>,
    /// Stable degenbot admission artifact hash.
    pub admission_hash: String,
}

/// JSON-safe fee split.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PredictionFxFeeSplitReport {
    /// Gross fill amount.
    pub gross: String,
    /// Total fee.
    pub fee: String,
    /// Creator fee.
    pub creator_fee: String,
    /// Resolver fee.
    pub resolver_fee: String,
    /// Net amount.
    pub net: String,
}

/// JSON-safe violation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PredictionFxViolationReport {
    /// Stable violation code.
    pub code: String,
    /// Human-readable reason.
    pub message: String,
}

/// EIP-712 type hash for the reference order.
#[must_use]
pub fn prediction_fx_order_type_hash() -> B256 {
    keccak256(
        b"Order(address maker,bool isYes,uint256 depositAmount,uint256 minShares,uint256 nonce,uint256 deadline)",
    )
}

/// EIP-712 domain type hash.
#[must_use]
pub fn prediction_fx_domain_type_hash() -> B256 {
    keccak256(b"EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")
}

/// EIP-712 domain name hash.
#[must_use]
pub fn prediction_fx_domain_name_hash() -> B256 {
    keccak256(b"BinaryOption")
}

/// EIP-712 domain version hash.
#[must_use]
pub fn prediction_fx_domain_version_hash() -> B256 {
    keccak256(b"1")
}

/// Hash a Prediction-FX order using the reference EIP-712 struct layout.
#[must_use]
pub fn hash_prediction_fx_order(order: &PredictionFxOrder) -> B256 {
    let encoded = (
        prediction_fx_order_type_hash(),
        order.maker,
        order.is_yes,
        order.deposit_amount,
        order.min_shares,
        order.nonce,
        order.deadline,
    )
        .abi_encode();
    keccak256(encoded)
}

/// Hash the EIP-712 domain separator.
#[must_use]
pub fn hash_prediction_fx_domain_separator(domain: PredictionFxDomain) -> B256 {
    let encoded = (
        prediction_fx_domain_type_hash(),
        prediction_fx_domain_name_hash(),
        prediction_fx_domain_version_hash(),
        domain.chain_id,
        domain.verifying_contract,
    )
        .abi_encode();
    keccak256(encoded)
}

/// Hash the EIP-712 digest a maker signs.
#[must_use]
pub fn hash_prediction_fx_eip712_digest(
    domain: PredictionFxDomain,
    order: &PredictionFxOrder,
) -> B256 {
    let mut encoded = Vec::with_capacity(66);
    encoded.extend_from_slice(&[0x19, 0x01]);
    encoded.extend_from_slice(hash_prediction_fx_domain_separator(domain).as_slice());
    encoded.extend_from_slice(hash_prediction_fx_order(order).as_slice());
    keccak256(encoded)
}

/// Evaluate a match and return a deterministic admission preview.
pub fn evaluate_prediction_fx_match(
    input: &PredictionFxMatchInput,
) -> SignedOrderAdmissionResult<PredictionFxMatchPreview> {
    let mut violations = Vec::new();
    let yes_order_hash = hash_prediction_fx_order(&input.yes_order);
    let no_order_hash = hash_prediction_fx_order(&input.no_order);
    let yes_remaining_before =
        remaining_capacity(input.yes_order.deposit_amount, input.yes_already_filled);
    let no_remaining_before =
        remaining_capacity(input.no_order.deposit_amount, input.no_already_filled);

    collect_basic_match_violations(
        input,
        yes_remaining_before,
        no_remaining_before,
        &mut violations,
    );

    let fee_bps = if input.fee_bps <= MAX_SOURCE_FEE_BPS {
        input.fee_bps
    } else {
        0
    };
    let creator_fee_bps = if input.creator_fee_bps <= BPS_DENOMINATOR {
        input.creator_fee_bps
    } else {
        0
    };
    let yes_side = split_prediction_fx_fees(input.yes_fill_amount, fee_bps, creator_fee_bps)?;
    let no_side = split_prediction_fx_fees(input.no_fill_amount, fee_bps, creator_fee_bps)?;
    let yes_shares_minted = no_side.net;
    let no_shares_minted = yes_side.net;

    collect_min_share_violations(input, yes_shares_minted, no_shares_minted, &mut violations)?;

    let executable = violations.is_empty();
    let admission_hash = hash_prediction_fx_admission(input, executable, &violations);
    Ok(PredictionFxMatchPreview {
        yes_order_hash,
        no_order_hash,
        yes_fill_amount: input.yes_fill_amount,
        no_fill_amount: input.no_fill_amount,
        yes_remaining_before,
        no_remaining_before,
        yes_side,
        no_side,
        yes_shares_minted,
        no_shares_minted,
        executable,
        violations,
        admission_hash,
    })
}

/// Evaluate a match from JSON and return a JSON-safe report.
///
/// Numeric fields may be decimal strings, hex strings, or JSON u64 numbers.
/// Decimal strings are preferred for JavaScript/Python callers so values never
/// lose precision before Rust parses them.
pub fn evaluate_prediction_fx_match_json(input_json: &str) -> SignedOrderAdmissionResult<String> {
    let value: Value =
        serde_json::from_str(input_json).map_err(|err| SignedOrderAdmissionError::InvalidJson {
            message: err.to_string(),
        })?;
    let input = parse_prediction_fx_match_input(&value)?;
    let preview = evaluate_prediction_fx_match(&input)?;
    serde_json::to_string(&PredictionFxMatchReport::from_preview(&preview)).map_err(|err| {
        SignedOrderAdmissionError::InvalidJson {
            message: err.to_string(),
        }
    })
}

/// Split fees using integer-only floor division.
pub fn split_prediction_fx_fees(
    gross: U256,
    fee_bps: u16,
    creator_fee_bps: u16,
) -> SignedOrderAdmissionResult<PredictionFxFeeSplit> {
    let fee = mul_div_floor(
        gross,
        U256::from(fee_bps),
        U256::from(BPS_DENOMINATOR),
        "fee",
    )?;
    let creator_fee = mul_div_floor(
        fee,
        U256::from(creator_fee_bps),
        U256::from(BPS_DENOMINATOR),
        "creator_fee",
    )?;
    let resolver_fee = checked_sub(
        fee,
        creator_fee,
        "resolver_fee must not underflow creator_fee",
    )?;
    let net = checked_sub(gross, fee, "net amount must not underflow fee")?;
    Ok(PredictionFxFeeSplit {
        gross,
        fee,
        creator_fee,
        resolver_fee,
        net,
    })
}

fn collect_basic_match_violations(
    input: &PredictionFxMatchInput,
    yes_remaining_before: U256,
    no_remaining_before: U256,
    violations: &mut Vec<PredictionFxViolation>,
) {
    if input.market_resolved {
        push_violation(
            violations,
            PredictionFxViolationCode::MarketResolved,
            "market is already resolved",
        );
    }
    if input.now >= input.market_expiry {
        push_violation(
            violations,
            PredictionFxViolationCode::MarketExpired,
            "market matching window has expired",
        );
    }
    if !input.yes_order.is_yes {
        push_violation(
            violations,
            PredictionFxViolationCode::YesOrderWrongSide,
            "expected first order to be YES-side",
        );
    }
    if input.no_order.is_yes {
        push_violation(
            violations,
            PredictionFxViolationCode::NoOrderWrongSide,
            "expected second order to be NO-side",
        );
    }
    if input.now > input.yes_order.deadline {
        push_violation(
            violations,
            PredictionFxViolationCode::YesOrderExpired,
            "YES order signature deadline has elapsed",
        );
    }
    if input.now > input.no_order.deadline {
        push_violation(
            violations,
            PredictionFxViolationCode::NoOrderExpired,
            "NO order signature deadline has elapsed",
        );
    }
    if input.yes_fill_amount.is_zero() || input.no_fill_amount.is_zero() {
        push_violation(
            violations,
            PredictionFxViolationCode::ZeroFill,
            "both fill amounts must be positive",
        );
    }
    if input.yes_order.deposit_amount.is_zero() || input.no_order.deposit_amount.is_zero() {
        push_violation(
            violations,
            PredictionFxViolationCode::ZeroOrderDeposit,
            "both orders must have positive deposit amounts",
        );
    }
    if input.yes_fill_amount > yes_remaining_before {
        push_violation(
            violations,
            PredictionFxViolationCode::YesOverfill,
            "YES fill exceeds remaining order capacity",
        );
    }
    if input.no_fill_amount > no_remaining_before {
        push_violation(
            violations,
            PredictionFxViolationCode::NoOverfill,
            "NO fill exceeds remaining order capacity",
        );
    }
    if input.fee_bps > MAX_SOURCE_FEE_BPS {
        push_violation(
            violations,
            PredictionFxViolationCode::FeeBpsOutOfRange,
            "fee_bps exceeds policy maximum",
        );
    }
    if input.creator_fee_bps > BPS_DENOMINATOR {
        push_violation(
            violations,
            PredictionFxViolationCode::CreatorFeeBpsOutOfRange,
            "creator_fee_bps exceeds 100%",
        );
    }
}

fn collect_min_share_violations(
    input: &PredictionFxMatchInput,
    yes_shares_minted: U256,
    no_shares_minted: U256,
    violations: &mut Vec<PredictionFxViolation>,
) -> SignedOrderAdmissionResult<()> {
    if proportional_min_shares_not_met(
        yes_shares_minted,
        input.yes_order.deposit_amount,
        input.yes_order.min_shares,
        input.yes_fill_amount,
        "yes_min_shares",
    )? {
        push_violation(
            violations,
            PredictionFxViolationCode::YesMinSharesNotMet,
            "YES order proportional min_shares is not met",
        );
    }
    if proportional_min_shares_not_met(
        no_shares_minted,
        input.no_order.deposit_amount,
        input.no_order.min_shares,
        input.no_fill_amount,
        "no_min_shares",
    )? {
        push_violation(
            violations,
            PredictionFxViolationCode::NoMinSharesNotMet,
            "NO order proportional min_shares is not met",
        );
    }
    Ok(())
}

fn remaining_capacity(deposit_amount: U256, already_filled: U256) -> U256 {
    if already_filled >= deposit_amount {
        U256::ZERO
    } else {
        deposit_amount - already_filled
    }
}

fn proportional_min_shares_not_met(
    shares_minted: U256,
    deposit_amount: U256,
    min_shares: U256,
    fill_amount: U256,
    context: &'static str,
) -> SignedOrderAdmissionResult<bool> {
    let lhs = checked_mul(shares_minted, deposit_amount, context)?;
    let rhs = checked_mul(min_shares, fill_amount, context)?;
    Ok(lhs < rhs)
}

fn push_violation(
    violations: &mut Vec<PredictionFxViolation>,
    code: PredictionFxViolationCode,
    message: &str,
) {
    violations.push(PredictionFxViolation {
        code,
        message: message.to_string(),
    });
}

fn mul_div_floor(
    value: U256,
    numerator: U256,
    denominator: U256,
    context: &'static str,
) -> SignedOrderAdmissionResult<U256> {
    let product = checked_mul(value, numerator, context)?;
    Ok(product / denominator)
}

fn checked_mul(left: U256, right: U256, context: &'static str) -> SignedOrderAdmissionResult<U256> {
    left.checked_mul(right)
        .ok_or(SignedOrderAdmissionError::ArithmeticOverflow { context })
}

fn checked_sub(left: U256, right: U256, context: &'static str) -> SignedOrderAdmissionResult<U256> {
    left.checked_sub(right)
        .ok_or(SignedOrderAdmissionError::ArithmeticUnderflow { context })
}

impl PredictionFxMatchReport {
    fn from_preview(preview: &PredictionFxMatchPreview) -> Self {
        Self {
            yes_order_hash: format!("{:#x}", preview.yes_order_hash),
            no_order_hash: format!("{:#x}", preview.no_order_hash),
            yes_fill_amount: preview.yes_fill_amount.to_string(),
            no_fill_amount: preview.no_fill_amount.to_string(),
            yes_remaining_before: preview.yes_remaining_before.to_string(),
            no_remaining_before: preview.no_remaining_before.to_string(),
            yes_side: PredictionFxFeeSplitReport::from_split(preview.yes_side),
            no_side: PredictionFxFeeSplitReport::from_split(preview.no_side),
            yes_shares_minted: preview.yes_shares_minted.to_string(),
            no_shares_minted: preview.no_shares_minted.to_string(),
            executable: preview.executable,
            violations: preview
                .violations
                .iter()
                .map(PredictionFxViolationReport::from_violation)
                .collect(),
            admission_hash: format!("{:#x}", preview.admission_hash),
        }
    }
}

impl PredictionFxFeeSplitReport {
    fn from_split(split: PredictionFxFeeSplit) -> Self {
        Self {
            gross: split.gross.to_string(),
            fee: split.fee.to_string(),
            creator_fee: split.creator_fee.to_string(),
            resolver_fee: split.resolver_fee.to_string(),
            net: split.net.to_string(),
        }
    }
}

impl PredictionFxViolationReport {
    fn from_violation(violation: &PredictionFxViolation) -> Self {
        Self {
            code: violation.code.as_wire().to_string(),
            message: violation.message.clone(),
        }
    }
}

fn parse_prediction_fx_match_input(
    value: &Value,
) -> SignedOrderAdmissionResult<PredictionFxMatchInput> {
    Ok(PredictionFxMatchInput {
        yes_order: parse_order(field(value, "input", "yes_order")?, "yes_order")?,
        no_order: parse_order(field(value, "input", "no_order")?, "no_order")?,
        yes_fill_amount: required_u256(value, "input", "yes_fill_amount")?,
        no_fill_amount: required_u256(value, "input", "no_fill_amount")?,
        yes_already_filled: optional_u256(value, "input", "yes_already_filled")?
            .unwrap_or(U256::ZERO),
        no_already_filled: optional_u256(value, "input", "no_already_filled")?
            .unwrap_or(U256::ZERO),
        now: required_u256(value, "input", "now")?,
        market_expiry: required_u256(value, "input", "market_expiry")?,
        market_resolved: optional_bool(value, "market_resolved").unwrap_or(false),
        fee_bps: required_u16(value, "input", "fee_bps")?,
        creator_fee_bps: required_u16(value, "input", "creator_fee_bps")?,
    })
}

fn parse_order(
    value: &Value,
    object: &'static str,
) -> SignedOrderAdmissionResult<PredictionFxOrder> {
    Ok(PredictionFxOrder {
        maker: required_address(value, object, "maker")?,
        is_yes: required_bool(value, object, "is_yes")?,
        deposit_amount: required_u256(value, object, "deposit_amount")?,
        min_shares: required_u256(value, object, "min_shares")?,
        nonce: required_u256(value, object, "nonce")?,
        deadline: required_u256(value, object, "deadline")?,
    })
}

fn field<'a>(
    value: &'a Value,
    object: &'static str,
    key: &'static str,
) -> SignedOrderAdmissionResult<&'a Value> {
    value
        .get(key)
        .ok_or(SignedOrderAdmissionError::MissingField { object, field: key })
}

fn required_address(
    value: &Value,
    object: &'static str,
    key: &'static str,
) -> SignedOrderAdmissionResult<Address> {
    required_str(value, object, key)?
        .parse::<Address>()
        .map_err(|err| SignedOrderAdmissionError::InvalidField {
            object,
            field: key,
            message: err.to_string(),
        })
}

fn required_str<'a>(
    value: &'a Value,
    object: &'static str,
    key: &'static str,
) -> SignedOrderAdmissionResult<&'a str> {
    field(value, object, key)?
        .as_str()
        .ok_or_else(|| SignedOrderAdmissionError::InvalidField {
            object,
            field: key,
            message: "expected string".to_string(),
        })
}

fn required_bool(
    value: &Value,
    object: &'static str,
    key: &'static str,
) -> SignedOrderAdmissionResult<bool> {
    field(value, object, key)?
        .as_bool()
        .ok_or_else(|| SignedOrderAdmissionError::InvalidField {
            object,
            field: key,
            message: "expected bool".to_string(),
        })
}

fn optional_bool(value: &Value, key: &'static str) -> Option<bool> {
    value.get(key).and_then(Value::as_bool)
}

fn required_u16(
    value: &Value,
    object: &'static str,
    key: &'static str,
) -> SignedOrderAdmissionResult<u16> {
    let raw = field(value, object, key)?;
    if let Some(n) = raw.as_u64() {
        return u16::try_from(n).map_err(|err| SignedOrderAdmissionError::InvalidField {
            object,
            field: key,
            message: err.to_string(),
        });
    }
    let text = raw
        .as_str()
        .ok_or_else(|| SignedOrderAdmissionError::InvalidField {
            object,
            field: key,
            message: "expected u16 or decimal string".to_string(),
        })?;
    text.parse::<u16>()
        .map_err(|err| SignedOrderAdmissionError::InvalidField {
            object,
            field: key,
            message: err.to_string(),
        })
}

fn required_u256(
    value: &Value,
    object: &'static str,
    key: &'static str,
) -> SignedOrderAdmissionResult<U256> {
    optional_u256(value, object, key)?
        .ok_or(SignedOrderAdmissionError::MissingField { object, field: key })
}

fn optional_u256(
    value: &Value,
    object: &'static str,
    key: &'static str,
) -> SignedOrderAdmissionResult<Option<U256>> {
    let Some(raw) = value.get(key) else {
        return Ok(None);
    };
    if let Some(n) = raw.as_u64() {
        return Ok(Some(U256::from(n)));
    }
    let text = raw
        .as_str()
        .ok_or_else(|| SignedOrderAdmissionError::InvalidField {
            object,
            field: key,
            message: "expected decimal string, hex string, or u64".to_string(),
        })?;
    let parsed = text
        .strip_prefix("0x")
        .map_or_else(
            || U256::from_str_radix(text, 10),
            |hex| U256::from_str_radix(hex, 16),
        )
        .map_err(|err| SignedOrderAdmissionError::InvalidField {
            object,
            field: key,
            message: err.to_string(),
        })?;
    Ok(Some(parsed))
}

fn hash_prediction_fx_admission(
    input: &PredictionFxMatchInput,
    executable: bool,
    violations: &[PredictionFxViolation],
) -> B256 {
    let mut bytes = Vec::new();
    push_str(&mut bytes, "degenbot-signed-order-admission-v1");
    push_str(&mut bytes, "prediction_fx");
    push_order(&mut bytes, &input.yes_order);
    push_order(&mut bytes, &input.no_order);
    push_u256(&mut bytes, input.yes_fill_amount);
    push_u256(&mut bytes, input.no_fill_amount);
    push_u256(&mut bytes, input.yes_already_filled);
    push_u256(&mut bytes, input.no_already_filled);
    push_u256(&mut bytes, input.now);
    push_u256(&mut bytes, input.market_expiry);
    bytes.push(u8::from(input.market_resolved));
    bytes.extend_from_slice(&input.fee_bps.to_be_bytes());
    bytes.extend_from_slice(&input.creator_fee_bps.to_be_bytes());
    bytes.push(u8::from(executable));
    bytes.extend_from_slice(&(violations.len() as u64).to_be_bytes());
    for violation in violations {
        push_str(&mut bytes, violation.code.as_wire());
    }
    keccak256(bytes)
}

fn push_order(out: &mut Vec<u8>, order: &PredictionFxOrder) {
    out.extend_from_slice(order.maker.as_slice());
    out.push(u8::from(order.is_yes));
    push_u256(out, order.deposit_amount);
    push_u256(out, order.min_shares);
    push_u256(out, order.nonce);
    push_u256(out, order.deadline);
    out.extend_from_slice(hash_prediction_fx_order(order).as_slice());
}

fn push_u256(out: &mut Vec<u8>, value: U256) {
    push_str(out, &value.to_string());
}

fn push_str(out: &mut Vec<u8>, value: &str) {
    out.extend_from_slice(&(value.len() as u64).to_be_bytes());
    out.extend_from_slice(value.as_bytes());
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;
    use alloy::primitives::{address, b256};

    fn yes_order() -> PredictionFxOrder {
        PredictionFxOrder {
            maker: address!("1111111111111111111111111111111111111111"),
            is_yes: true,
            deposit_amount: U256::from(100_000_000u64),
            min_shares: U256::from(110_000_000u64),
            nonce: U256::from(7u64),
            deadline: U256::from(1_800_000_000u64),
        }
    }

    fn no_order() -> PredictionFxOrder {
        PredictionFxOrder {
            maker: address!("2222222222222222222222222222222222222222"),
            is_yes: false,
            deposit_amount: U256::from(120_000_000u64),
            min_shares: U256::from(90_000_000u64),
            nonce: U256::from(8u64),
            deadline: U256::from(1_800_000_000u64),
        }
    }

    fn executable_input() -> PredictionFxMatchInput {
        PredictionFxMatchInput {
            yes_order: yes_order(),
            no_order: no_order(),
            yes_fill_amount: U256::from(100_000_000u64),
            no_fill_amount: U256::from(120_000_000u64),
            yes_already_filled: U256::ZERO,
            no_already_filled: U256::ZERO,
            now: U256::from(1_700_000_000u64),
            market_expiry: U256::from(1_900_000_000u64),
            market_resolved: false,
            fee_bps: 100,
            creator_fee_bps: 5_000,
        }
    }

    #[test]
    fn pins_prediction_fx_eip712_hashes() {
        assert_eq!(
            prediction_fx_order_type_hash(),
            b256!("38ae19288860b4b479ee33301d04ce032f4e992ac5c9562bd37f8c7133712b70")
        );
        assert_eq!(
            prediction_fx_domain_type_hash(),
            b256!("8b73c3c69bb8fe3d512ecc4cf759cc79239f7b179b0ffacaa9a75d522b39400f")
        );
        let domain = PredictionFxDomain {
            chain_id: U256::from(42_161u64),
            verifying_contract: address!("3333333333333333333333333333333333333333"),
        };
        assert_eq!(
            hash_prediction_fx_order(&yes_order()),
            b256!("e02e95e1be4945d958b70e89a137a5098c9986d6cda543cb537725de0da9692d")
        );
        assert_eq!(
            hash_prediction_fx_domain_separator(domain),
            b256!("73fb01273d5e1f9fc444abc178d21e8923d40a9939b917dffdcdc839d7cf1957")
        );
        assert_eq!(
            hash_prediction_fx_eip712_digest(domain, &yes_order()),
            b256!("45d0cd09f23848ea7d7c29c320769809520aba3983fdbb0329dec99a4c5eeceb")
        );
    }

    #[test]
    fn evaluates_full_fill_economics_exactly() {
        let preview = evaluate_prediction_fx_match(&executable_input()).unwrap();
        assert!(preview.executable);
        assert!(preview.violations.is_empty());
        assert_eq!(preview.yes_side.gross, U256::from(100_000_000u64));
        assert_eq!(preview.yes_side.fee, U256::from(1_000_000u64));
        assert_eq!(preview.yes_side.creator_fee, U256::from(500_000u64));
        assert_eq!(preview.yes_side.resolver_fee, U256::from(500_000u64));
        assert_eq!(preview.yes_side.net, U256::from(99_000_000u64));
        assert_eq!(preview.no_side.gross, U256::from(120_000_000u64));
        assert_eq!(preview.no_side.fee, U256::from(1_200_000u64));
        assert_eq!(preview.no_side.creator_fee, U256::from(600_000u64));
        assert_eq!(preview.no_side.resolver_fee, U256::from(600_000u64));
        assert_eq!(preview.no_side.net, U256::from(118_800_000u64));
        assert_eq!(preview.yes_shares_minted, U256::from(118_800_000u64));
        assert_eq!(preview.no_shares_minted, U256::from(99_000_000u64));
        assert_ne!(preview.admission_hash, B256::ZERO);
    }

    #[test]
    fn enforces_partial_fill_min_shares_and_capacity() {
        let mut input = executable_input();
        input.yes_order.deposit_amount = U256::from(1_000_000_000u64);
        input.yes_order.min_shares = U256::from(1_100_000_000u64);
        input.no_order.deposit_amount = U256::from(500_000_000u64);
        input.no_order.min_shares = U256::from(300_000_000u64);
        input.yes_fill_amount = U256::from(400_000_000u64);
        input.no_fill_amount = U256::from(500_000_000u64);
        let preview = evaluate_prediction_fx_match(&input).unwrap();
        assert!(preview.executable);
        assert_eq!(preview.yes_shares_minted, U256::from(495_000_000u64));
        assert_eq!(preview.no_shares_minted, U256::from(396_000_000u64));

        let mut overfill = executable_input();
        overfill.yes_fill_amount = U256::from(1u64);
        overfill.no_fill_amount = U256::from(1u64);
        overfill.yes_already_filled = U256::from(100_000_000u64);
        overfill.no_already_filled = U256::from(119_999_999u64);
        let rejected = evaluate_prediction_fx_match(&overfill).unwrap();
        assert!(!rejected.executable);
        assert!(rejected
            .violations
            .iter()
            .any(|violation| violation.code == PredictionFxViolationCode::YesOverfill));
    }

    #[test]
    fn reports_all_gate_violations_without_short_circuiting() {
        let mut input = executable_input();
        input.yes_order.is_yes = false;
        input.yes_order.deadline = U256::from(1_600_000_000u64);
        input.no_order.is_yes = true;
        input.no_order.min_shares = U256::from(999_000_000u64);
        input.yes_fill_amount = U256::ZERO;
        input.no_fill_amount = U256::from(121_000_000u64);
        input.now = U256::from(1_900_000_000u64);
        input.market_expiry = U256::from(1_800_000_000u64);
        input.market_resolved = true;
        input.fee_bps = 1_001;
        input.creator_fee_bps = 10_001;
        let preview = evaluate_prediction_fx_match(&input).unwrap();
        let codes = preview
            .violations
            .iter()
            .map(|violation| violation.code)
            .collect::<Vec<_>>();
        assert_eq!(
            codes,
            vec![
                PredictionFxViolationCode::MarketResolved,
                PredictionFxViolationCode::MarketExpired,
                PredictionFxViolationCode::YesOrderWrongSide,
                PredictionFxViolationCode::NoOrderWrongSide,
                PredictionFxViolationCode::YesOrderExpired,
                PredictionFxViolationCode::NoOrderExpired,
                PredictionFxViolationCode::ZeroFill,
                PredictionFxViolationCode::NoOverfill,
                PredictionFxViolationCode::FeeBpsOutOfRange,
                PredictionFxViolationCode::CreatorFeeBpsOutOfRange,
                PredictionFxViolationCode::NoMinSharesNotMet,
            ]
        );
    }

    #[test]
    fn json_api_returns_decimal_strings_and_admission_hash() {
        let input_json = r#"{
            "yes_order":{
                "maker":"0x1111111111111111111111111111111111111111",
                "is_yes":true,
                "deposit_amount":"100000000",
                "min_shares":"110000000",
                "nonce":"7",
                "deadline":"1800000000"
            },
            "no_order":{
                "maker":"0x2222222222222222222222222222222222222222",
                "is_yes":false,
                "deposit_amount":"120000000",
                "min_shares":"90000000",
                "nonce":"8",
                "deadline":"1800000000"
            },
            "yes_fill_amount":"100000000",
            "no_fill_amount":"120000000",
            "now":"1700000000",
            "market_expiry":"1900000000",
            "fee_bps":100,
            "creator_fee_bps":5000
        }"#;
        let report_json = evaluate_prediction_fx_match_json(input_json).unwrap();
        let report: Value = serde_json::from_str(&report_json).unwrap();
        assert_eq!(report["executable"], true);
        assert_eq!(report["yes_side"]["fee"], "1000000");
        assert_eq!(report["no_side"]["net"], "118800000");
        assert_eq!(report["violations"].as_array().unwrap().len(), 0);
        assert!(report["admission_hash"].as_str().unwrap().starts_with("0x"));
    }
}
