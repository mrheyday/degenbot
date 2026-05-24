use alloc::vec::Vec;

use alloy_primitives::address;
use stylus_sdk::alloy_primitives::{Address, U256};

pub const MASK_OWNER_RENOUNCED: U256 = U256::from_limbs([1 << 0, 0, 0, 0]);
pub const MASK_MINT_DISABLED: U256 = U256::from_limbs([1 << 1, 0, 0, 0]);
pub const MASK_TRANSFER_TAX: U256 = U256::from_limbs([1 << 2, 0, 0, 0]);
pub const MASK_SELL_TAX_HIGHER: U256 = U256::from_limbs([1 << 3, 0, 0, 0]);
pub const MASK_CONCENTRATED_HOLDERS: U256 = U256::from_limbs([1 << 4, 0, 0, 0]);
pub const MASK_BLACKLIST_FUNC: U256 = U256::from_limbs([1 << 5, 0, 0, 0]);
pub const MASK_PAUSABLE_TRANSFERS: U256 = U256::from_limbs([1 << 6, 0, 0, 0]);
pub const MASK_PROXY_MINT: U256 = U256::from_limbs([1 << 7, 0, 0, 0]);
pub const MASK_NO_CODE: U256 = U256::from_limbs([1 << 8, 0, 0, 0]);

pub const CACHE_TTL_SECONDS: u64 = 300;
pub const RISK_STATICCALL_GAS: u64 = 30_000;

pub const ARBITRUM_USDC: Address = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");
pub const ARBITRUM_USDT: Address = address!("Fd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9");
pub const ARBITRUM_DAI: Address = address!("DA10009cBd5D07dd0CeCc66161FC93D7c9000da1");
pub const ARBITRUM_WETH: Address = address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1");
pub const ARBITRUM_WBTC: Address = address!("2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f");
pub const ARBITRUM_ARB: Address = address!("912CE59144191C1204E64559FE8253a0e49E6548");
pub const ARBITRUM_WSTETH: Address = address!("5979D7b546E38E414F7E9822514be443A4800529");
pub const ARBITRUM_CBETH: Address = address!("1DEBd73E752bEaF79865Fd6446b0c970EaE7732f");
pub const ARBITRUM_RETH: Address = address!("EC70Dcb4A1EFa46b8F2D97C310C9c4790ba5ffA8");

pub const ARBITRUM_MAJOR_TOKENS: [Address; 9] = [
    ARBITRUM_USDC,
    ARBITRUM_USDT,
    ARBITRUM_DAI,
    ARBITRUM_WETH,
    ARBITRUM_WBTC,
    ARBITRUM_ARB,
    ARBITRUM_WSTETH,
    ARBITRUM_CBETH,
    ARBITRUM_RETH,
];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RiskReason {
    TokenHasNoCode,
    TransferSimulationUnavailable,
    TransferFailedOrTax,
    TransferReturnMalformed,
    HasBlacklistFunction,
    TransfersArePaused,
}

#[must_use]
pub const fn reason_label(reason: RiskReason) -> &'static str {
    match reason {
        RiskReason::TokenHasNoCode => "token_has_no_code",
        RiskReason::TransferSimulationUnavailable => "transfer_simulation_unavailable",
        RiskReason::TransferFailedOrTax => "transfer_failed_or_tax",
        RiskReason::TransferReturnMalformed => "transfer_return_malformed",
        RiskReason::HasBlacklistFunction => "has_blacklist_function",
        RiskReason::TransfersArePaused => "transfers_are_paused",
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TransferProbe {
    Unavailable,
    ReturnedBool(bool),
    EmptyReturn,
    MalformedReturn,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ProbeVerdict {
    pub has_code: bool,
    pub owner_renounced: Option<bool>,
    pub transfer_result: TransferProbe,
    pub has_blacklist: bool,
    pub paused: Option<bool>,
}

impl ProbeVerdict {
    pub const fn no_code() -> Self {
        Self {
            has_code: false,
            owner_renounced: None,
            transfer_result: TransferProbe::Unavailable,
            has_blacklist: false,
            paused: None,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RiskVerdict {
    pub flags: U256,
    pub is_safe: bool,
    pub reasons: Vec<RiskReason>,
}

pub fn is_major(token: Address) -> bool {
    ARBITRUM_MAJOR_TOKENS.contains(&token)
}

pub fn known_risk_mask() -> U256 {
    MASK_OWNER_RENOUNCED
        | MASK_MINT_DISABLED
        | MASK_TRANSFER_TAX
        | MASK_SELL_TAX_HIGHER
        | MASK_CONCENTRATED_HOLDERS
        | MASK_BLACKLIST_FUNC
        | MASK_PAUSABLE_TRANSFERS
        | MASK_PROXY_MINT
        | MASK_NO_CODE
}

pub fn is_safe_flags(flags: U256) -> bool {
    (flags & (MASK_TRANSFER_TAX | MASK_BLACKLIST_FUNC | MASK_PROXY_MINT)) == U256::ZERO
}

pub fn assess_probe(token: Address, probe: ProbeVerdict) -> RiskVerdict {
    if is_major(token) {
        return RiskVerdict {
            flags: U256::ZERO,
            is_safe: true,
            reasons: Vec::new(),
        };
    }

    if !probe.has_code {
        return RiskVerdict {
            flags: MASK_NO_CODE,
            is_safe: false,
            reasons: alloc::vec![RiskReason::TokenHasNoCode],
        };
    }

    let mut flags = U256::ZERO;
    let mut reasons = Vec::new();

    if probe.owner_renounced == Some(true) {
        flags |= MASK_OWNER_RENOUNCED;
    }

    match probe.transfer_result {
        TransferProbe::Unavailable => {
            flags |= MASK_TRANSFER_TAX;
            reasons.push(RiskReason::TransferSimulationUnavailable);
        }
        TransferProbe::ReturnedBool(false) => {
            flags |= MASK_TRANSFER_TAX;
            reasons.push(RiskReason::TransferFailedOrTax);
        }
        TransferProbe::MalformedReturn => {
            flags |= MASK_TRANSFER_TAX;
            reasons.push(RiskReason::TransferReturnMalformed);
        }
        TransferProbe::ReturnedBool(true) | TransferProbe::EmptyReturn => {}
    }

    if probe.has_blacklist {
        flags |= MASK_BLACKLIST_FUNC;
        reasons.push(RiskReason::HasBlacklistFunction);
    }

    if probe.paused == Some(true) {
        flags |= MASK_PAUSABLE_TRANSFERS;
        reasons.push(RiskReason::TransfersArePaused);
    }

    RiskVerdict {
        flags,
        is_safe: is_safe_flags(flags),
        reasons,
    }
}
