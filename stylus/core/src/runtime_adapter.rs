//! Deterministic runtime-adapter proof surface for the Stylus migration.
//!
//! This module ports the live execution invariants that were not covered by
//! the static executor fragments: callback authentication, flash-token
//! settlement math, typed approvals, generic-call allowlist checks, and a
//! receipt digest that binds the accepted off-chain execution adapter payload.
//! It does not issue host calls; it gives the Stylus replacement and the
//! off-chain signer/broadcast adapter one byte-stable proof language for the
//! capital-moving path.

extern crate alloc;

use alloc::vec::Vec;

use stylus_sdk::alloy_primitives::{Address, FixedBytes, U256, keccak256};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum RuntimeAdapterError {
    UnknownLane = 1,
    NoActiveFlow = 2,
    UnexpectedLender = 3,
    UnexpectedReactor = 4,
    UnexpectedInitiator = 5,
    WrongFlashAsset = 6,
    BalanceUnderBorrow = 7,
    IdleBalanceNotZero = 8,
    RepaymentOverflow = 9,
    RepaymentShortfall = 10,
    InsufficientProfit = 11,
    PlanHashMismatch = 12,
    ZeroAddress = 13,
    CallTargetNotAllowed = 14,
    CallSelectorNotAllowed = 15,
    NativeValueNotAllowed = 16,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum RuntimeLane {
    ExecutorAaveV3 = 0,
    ExecutorMorphoBlue = 1,
    ExecutorErc3156 = 2,
    ExecutorUniswapV3 = 3,
    AtomicBalancerV3 = 4,
    AtomicBalancerV2 = 5,
    AtomicAaveV3Simple = 6,
    UniswapXReactor = 7,
    CowFlashLoanRouter = 8,
}

impl RuntimeLane {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::ExecutorAaveV3),
            1 => Some(Self::ExecutorMorphoBlue),
            2 => Some(Self::ExecutorErc3156),
            3 => Some(Self::ExecutorUniswapV3),
            4 => Some(Self::AtomicBalancerV3),
            5 => Some(Self::AtomicBalancerV2),
            6 => Some(Self::AtomicAaveV3Simple),
            7 => Some(Self::UniswapXReactor),
            8 => Some(Self::CowFlashLoanRouter),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CallbackAuthProof {
    pub lane: u8,
    pub msg_sender: Address,
    pub expected_lender: Address,
    pub expected_v3_pool: Address,
    pub expected_reactor: Address,
    pub initiator: Address,
    pub executor: Address,
    pub canonical_sender: Address,
    pub active_plan_hash: FixedBytes<32>,
    pub expected_plan_hash: FixedBytes<32>,
    pub require_plan_hash: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FlashSettlementProof {
    pub flash_token: Address,
    pub callback_token: Address,
    pub flash_amount: U256,
    pub callback_amount: U256,
    pub premium: U256,
    pub balance_on_callback: U256,
    pub balance_before_repay: U256,
    pub min_profit: U256,
    pub reject_idle_balance: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RuntimeApprovalProof {
    pub token: Address,
    pub spender: Address,
    pub spender_allowed: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RuntimeCallProof {
    pub target: Address,
    pub selector: [u8; 4],
    pub target_allowed: bool,
    pub selector_allowed: bool,
    pub value: U256,
    pub native_value_limit: U256,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ExecutionReceiptProof {
    pub lane: u8,
    pub flow_id: FixedBytes<32>,
    pub plan_hash: FixedBytes<32>,
    pub flash_token: Address,
    pub flash_amount: U256,
    pub premium: U256,
    pub min_profit: U256,
    pub profit: U256,
}

#[must_use]
pub fn error_code(result: Result<(), RuntimeAdapterError>) -> u8 {
    match result {
        Ok(()) => 0,
        Err(error) => error as u8,
    }
}

pub fn validate_callback_auth(input: CallbackAuthProof) -> Result<(), RuntimeAdapterError> {
    let lane = RuntimeLane::from_u8(input.lane).ok_or(RuntimeAdapterError::UnknownLane)?;
    match lane {
        RuntimeLane::ExecutorAaveV3 | RuntimeLane::ExecutorErc3156 => {
            validate_active_lender(input.msg_sender, input.expected_lender)?;
            validate_initiator(input.initiator, input.executor)
        }
        RuntimeLane::ExecutorMorphoBlue => {
            validate_canonical_sender(input.msg_sender, input.canonical_sender)?;
            validate_active_lender(input.msg_sender, input.expected_lender)
        }
        RuntimeLane::ExecutorUniswapV3 => {
            validate_active_lender(input.msg_sender, input.expected_lender)?;
            if input.expected_v3_pool == Address::ZERO {
                return Err(RuntimeAdapterError::NoActiveFlow);
            }
            if input.msg_sender != input.expected_v3_pool {
                return Err(RuntimeAdapterError::UnexpectedLender);
            }
            Ok(())
        }
        RuntimeLane::AtomicBalancerV3
        | RuntimeLane::AtomicBalancerV2
        | RuntimeLane::AtomicAaveV3Simple => {
            validate_canonical_sender(input.msg_sender, input.canonical_sender)?;
            validate_active_lender(input.msg_sender, input.expected_lender)?;
            if matches!(lane, RuntimeLane::AtomicAaveV3Simple) {
                validate_initiator(input.initiator, input.executor)?;
            }
            validate_plan_hash(input)
        }
        RuntimeLane::UniswapXReactor => {
            validate_canonical_sender(input.msg_sender, input.canonical_sender)?;
            if input.expected_reactor == Address::ZERO {
                return Err(RuntimeAdapterError::NoActiveFlow);
            }
            if input.msg_sender != input.expected_reactor {
                return Err(RuntimeAdapterError::UnexpectedReactor);
            }
            Ok(())
        }
        RuntimeLane::CowFlashLoanRouter => {
            validate_canonical_sender(input.msg_sender, input.canonical_sender)
        }
    }
}

pub fn validate_flash_settlement(input: FlashSettlementProof) -> Result<U256, RuntimeAdapterError> {
    if input.flash_token == Address::ZERO {
        return Err(RuntimeAdapterError::ZeroAddress);
    }
    if input.callback_token != Address::ZERO && input.callback_token != input.flash_token {
        return Err(RuntimeAdapterError::WrongFlashAsset);
    }
    if input.callback_amount != input.flash_amount {
        return Err(RuntimeAdapterError::WrongFlashAsset);
    }
    if input.balance_on_callback < input.flash_amount {
        return Err(RuntimeAdapterError::BalanceUnderBorrow);
    }

    let idle_before = input.balance_on_callback - input.flash_amount;
    if input.reject_idle_balance && idle_before != U256::ZERO {
        return Err(RuntimeAdapterError::IdleBalanceNotZero);
    }

    let owed = input
        .flash_amount
        .checked_add(input.premium)
        .ok_or(RuntimeAdapterError::RepaymentOverflow)?;
    if input.balance_before_repay < owed {
        return Err(RuntimeAdapterError::RepaymentShortfall);
    }

    let profit = input.balance_before_repay - owed;
    if profit < input.min_profit {
        return Err(RuntimeAdapterError::InsufficientProfit);
    }
    Ok(profit)
}

pub fn validate_runtime_approval(input: RuntimeApprovalProof) -> Result<(), RuntimeAdapterError> {
    if input.token == Address::ZERO || input.spender == Address::ZERO {
        return Err(RuntimeAdapterError::ZeroAddress);
    }
    if !input.spender_allowed {
        return Err(RuntimeAdapterError::CallTargetNotAllowed);
    }
    Ok(())
}

pub fn validate_runtime_call(input: RuntimeCallProof) -> Result<(), RuntimeAdapterError> {
    if input.target == Address::ZERO || input.selector == [0; 4] {
        return Err(RuntimeAdapterError::ZeroAddress);
    }
    if !input.target_allowed {
        return Err(RuntimeAdapterError::CallTargetNotAllowed);
    }
    if !input.selector_allowed {
        return Err(RuntimeAdapterError::CallSelectorNotAllowed);
    }
    if input.value > input.native_value_limit {
        return Err(RuntimeAdapterError::NativeValueNotAllowed);
    }
    Ok(())
}

#[must_use]
pub fn domain_separator() -> FixedBytes<32> {
    keccak256(b"degenbot.stylus.runtime-adapter-proof.v1")
}

#[must_use]
pub fn settlement_profit_or_zero(input: FlashSettlementProof) -> U256 {
    validate_flash_settlement(input).unwrap_or(U256::ZERO)
}

#[must_use]
pub fn execution_receipt_digest(input: ExecutionReceiptProof) -> FixedBytes<32> {
    let mut out = Vec::with_capacity(32 * 8);
    out.extend_from_slice(domain_separator().as_slice());
    push_u8_word(&mut out, input.lane);
    out.extend_from_slice(input.flow_id.as_slice());
    out.extend_from_slice(input.plan_hash.as_slice());
    push_address_word(&mut out, input.flash_token);
    push_u256_word(&mut out, input.flash_amount);
    push_u256_word(&mut out, input.premium);
    push_u256_word(&mut out, input.min_profit);
    push_u256_word(&mut out, input.profit);
    keccak256(out)
}

fn validate_active_lender(
    msg_sender: Address,
    expected_lender: Address,
) -> Result<(), RuntimeAdapterError> {
    if expected_lender == Address::ZERO {
        return Err(RuntimeAdapterError::NoActiveFlow);
    }
    if msg_sender != expected_lender {
        return Err(RuntimeAdapterError::UnexpectedLender);
    }
    Ok(())
}

fn validate_canonical_sender(
    msg_sender: Address,
    canonical_sender: Address,
) -> Result<(), RuntimeAdapterError> {
    if canonical_sender == Address::ZERO {
        return Err(RuntimeAdapterError::ZeroAddress);
    }
    if msg_sender != canonical_sender {
        return Err(RuntimeAdapterError::UnexpectedLender);
    }
    Ok(())
}

fn validate_initiator(initiator: Address, executor: Address) -> Result<(), RuntimeAdapterError> {
    if executor == Address::ZERO {
        return Err(RuntimeAdapterError::ZeroAddress);
    }
    if initiator != executor {
        return Err(RuntimeAdapterError::UnexpectedInitiator);
    }
    Ok(())
}

fn validate_plan_hash(input: CallbackAuthProof) -> Result<(), RuntimeAdapterError> {
    if !input.require_plan_hash {
        return Ok(());
    }
    if input.active_plan_hash == FixedBytes::<32>::ZERO {
        return Err(RuntimeAdapterError::NoActiveFlow);
    }
    if input.active_plan_hash != input.expected_plan_hash {
        return Err(RuntimeAdapterError::PlanHashMismatch);
    }
    Ok(())
}

fn push_u8_word(out: &mut Vec<u8>, value: u8) {
    let mut word = [0_u8; 32];
    word[31] = value;
    out.extend_from_slice(&word);
}

fn push_address_word(out: &mut Vec<u8>, value: Address) {
    let mut word = [0_u8; 32];
    word[12..].copy_from_slice(value.as_slice());
    out.extend_from_slice(&word);
}

fn push_u256_word(out: &mut Vec<u8>, value: U256) {
    out.extend_from_slice(&value.to_be_bytes::<32>());
}

#[cfg(test)]
mod tests {
    use super::*;

    fn addr(byte: u8) -> Address {
        Address::repeat_byte(byte)
    }

    fn hash(byte: u8) -> FixedBytes<32> {
        FixedBytes::repeat_byte(byte)
    }

    fn auth(lane: RuntimeLane) -> CallbackAuthProof {
        CallbackAuthProof {
            lane: lane as u8,
            msg_sender: addr(0xaa),
            expected_lender: addr(0xaa),
            expected_v3_pool: addr(0xbb),
            expected_reactor: addr(0xcc),
            initiator: addr(0xee),
            executor: addr(0xee),
            canonical_sender: addr(0xaa),
            active_plan_hash: hash(0x11),
            expected_plan_hash: hash(0x11),
            require_plan_hash: false,
        }
    }

    fn settlement() -> FlashSettlementProof {
        FlashSettlementProof {
            flash_token: addr(0x01),
            callback_token: addr(0x01),
            flash_amount: U256::from(100),
            callback_amount: U256::from(100),
            premium: U256::from(2),
            balance_on_callback: U256::from(100),
            balance_before_repay: U256::from(111),
            min_profit: U256::from(9),
            reject_idle_balance: false,
        }
    }

    #[test]
    fn callback_auth_proves_executor_and_atomic_gates() {
        assert_eq!(
            Ok(()),
            validate_callback_auth(auth(RuntimeLane::ExecutorAaveV3))
        );
        assert_eq!(
            Err(RuntimeAdapterError::UnexpectedInitiator),
            validate_callback_auth(CallbackAuthProof {
                initiator: addr(0x01),
                ..auth(RuntimeLane::ExecutorAaveV3)
            })
        );

        assert_eq!(
            Ok(()),
            validate_callback_auth(CallbackAuthProof {
                require_plan_hash: true,
                ..auth(RuntimeLane::AtomicBalancerV2)
            })
        );
        assert_eq!(
            Err(RuntimeAdapterError::PlanHashMismatch),
            validate_callback_auth(CallbackAuthProof {
                require_plan_hash: true,
                expected_plan_hash: hash(0x22),
                ..auth(RuntimeLane::AtomicBalancerV2)
            })
        );
    }

    #[test]
    fn callback_auth_proves_v3_reactor_and_cow_senders() {
        assert_eq!(
            Ok(()),
            validate_callback_auth(CallbackAuthProof {
                msg_sender: addr(0xbb),
                expected_lender: addr(0xbb),
                ..auth(RuntimeLane::ExecutorUniswapV3)
            })
        );
        assert_eq!(
            Err(RuntimeAdapterError::UnexpectedLender),
            validate_callback_auth(auth(RuntimeLane::ExecutorUniswapV3))
        );

        assert_eq!(
            Ok(()),
            validate_callback_auth(CallbackAuthProof {
                msg_sender: addr(0xcc),
                canonical_sender: addr(0xcc),
                ..auth(RuntimeLane::UniswapXReactor)
            })
        );
        assert_eq!(
            Ok(()),
            validate_callback_auth(auth(RuntimeLane::CowFlashLoanRouter))
        );
    }

    #[test]
    fn settlement_math_matches_live_repayment_guards() {
        assert_eq!(Ok(U256::from(9)), validate_flash_settlement(settlement()));
        assert_eq!(
            Err(RuntimeAdapterError::InsufficientProfit),
            validate_flash_settlement(FlashSettlementProof {
                min_profit: U256::from(10),
                ..settlement()
            })
        );
        assert_eq!(
            Err(RuntimeAdapterError::RepaymentShortfall),
            validate_flash_settlement(FlashSettlementProof {
                balance_before_repay: U256::from(101),
                ..settlement()
            })
        );
        assert_eq!(
            Err(RuntimeAdapterError::IdleBalanceNotZero),
            validate_flash_settlement(FlashSettlementProof {
                balance_on_callback: U256::from(101),
                reject_idle_balance: true,
                ..settlement()
            })
        );
    }

    #[test]
    fn runtime_call_and_approval_proofs_match_allowlist_rules() {
        assert_eq!(
            Ok(()),
            validate_runtime_approval(RuntimeApprovalProof {
                token: addr(0x01),
                spender: addr(0x02),
                spender_allowed: true,
            })
        );
        assert_eq!(
            Err(RuntimeAdapterError::CallTargetNotAllowed),
            validate_runtime_approval(RuntimeApprovalProof {
                spender_allowed: false,
                ..RuntimeApprovalProof {
                    token: addr(0x01),
                    spender: addr(0x02),
                    spender_allowed: true,
                }
            })
        );

        let call = RuntimeCallProof {
            target: addr(0x03),
            selector: [0xde, 0xad, 0xbe, 0xef],
            target_allowed: true,
            selector_allowed: true,
            value: U256::from(1),
            native_value_limit: U256::from(1),
        };
        assert_eq!(Ok(()), validate_runtime_call(call));
        assert_eq!(
            Err(RuntimeAdapterError::CallSelectorNotAllowed),
            validate_runtime_call(RuntimeCallProof {
                selector_allowed: false,
                ..call
            })
        );
        assert_eq!(
            Err(RuntimeAdapterError::NativeValueNotAllowed),
            validate_runtime_call(RuntimeCallProof {
                value: U256::from(2),
                ..call
            })
        );
    }

    #[test]
    fn receipt_digest_binds_adapter_execution_fields() {
        let input = ExecutionReceiptProof {
            lane: RuntimeLane::AtomicBalancerV2 as u8,
            flow_id: hash(0x01),
            plan_hash: hash(0x02),
            flash_token: addr(0x03),
            flash_amount: U256::from(100),
            premium: U256::from(2),
            min_profit: U256::from(9),
            profit: U256::from(9),
        };
        let digest = execution_receipt_digest(input);
        assert_ne!(FixedBytes::<32>::ZERO, digest);
        assert_ne!(
            digest,
            execution_receipt_digest(ExecutionReceiptProof {
                plan_hash: hash(0x04),
                ..input
            })
        );
    }
}
