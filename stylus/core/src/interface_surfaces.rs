use alloc::vec::Vec;

use alloy_primitives::address;
use stylus_sdk::alloy_primitives::{Address, U256};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum FlashProtocol {
    AaveV3 = 0,
    MorphoBlue = 1,
    Erc3156 = 2,
    UniswapV3 = 3,
    UniswapV2 = 4,
    UniswapV4 = 5,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum DexKind {
    UniswapV2 = 0,
    UniswapV3 = 1,
    UniswapV4 = 2,
    Curve = 3,
    ReservedAerodrome = 4,
    Aggregator = 5,
    MorphoBlue = 6,
    Algebra = 7,
    Solidly = 8,
    CurveNg = 9,
    BalancerV2 = 10,
    MaverickV2 = 11,
    DodoPmm = 12,
    FluidDex = 13,
    BalancerV3 = 14,
    KyberElastic = 15,
    LfjLiquidityBook = 16,
    GmxV2 = 17,
    Wombat = 18,
    Bebop = 19,
    Hashflow = 20,
    WooFi = 21,
    OkxDex = 22,
    Enso = 23,
    Squid = 24,
    LiFi = 25,
    Rango = 26,
    Rubic = 27,
    Native = 28,
}

impl DexKind {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::UniswapV2),
            1 => Some(Self::UniswapV3),
            2 => Some(Self::UniswapV4),
            3 => Some(Self::Curve),
            4 => Some(Self::ReservedAerodrome),
            5 => Some(Self::Aggregator),
            6 => Some(Self::MorphoBlue),
            7 => Some(Self::Algebra),
            8 => Some(Self::Solidly),
            9 => Some(Self::CurveNg),
            10 => Some(Self::BalancerV2),
            11 => Some(Self::MaverickV2),
            12 => Some(Self::DodoPmm),
            13 => Some(Self::FluidDex),
            14 => Some(Self::BalancerV3),
            15 => Some(Self::KyberElastic),
            16 => Some(Self::LfjLiquidityBook),
            17 => Some(Self::GmxV2),
            18 => Some(Self::Wombat),
            19 => Some(Self::Bebop),
            20 => Some(Self::Hashflow),
            21 => Some(Self::WooFi),
            22 => Some(Self::OkxDex),
            23 => Some(Self::Enso),
            24 => Some(Self::Squid),
            25 => Some(Self::LiFi),
            26 => Some(Self::Rango),
            27 => Some(Self::Rubic),
            28 => Some(Self::Native),
            _ => None,
        }
    }
}

pub fn dex_kind_for(kind: u8) -> u8 {
    DexKind::from_u8(kind)
        .map(|dex_kind| dex_kind as u8)
        .unwrap_or(u8::MAX)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum PathFinderVenue {
    V2 = 0,
    V3 = 1,
    V4 = 2,
    Curve = 3,
    Aggregator = 5,
    Morpho = 6,
    Solidly = 8,
    Balancer = 9,
}

impl PathFinderVenue {
    pub fn executor_dex_kind(self) -> Option<DexKind> {
        match self {
            Self::V2 => Some(DexKind::UniswapV2),
            Self::V3 => Some(DexKind::UniswapV3),
            Self::V4 => Some(DexKind::UniswapV4),
            Self::Curve => Some(DexKind::Curve),
            Self::Aggregator => Some(DexKind::Aggregator),
            Self::Morpho => Some(DexKind::MorphoBlue),
            Self::Solidly => Some(DexKind::UniswapV2),
            Self::Balancer => Some(DexKind::Aggregator),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Route {
    pub path: Vec<Address>,
    pub venues: Vec<u8>,
    pub fees: Vec<u32>,
    pub amount_out: U256,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RouteAbiError {
    PathTooShort,
    VenueLengthMismatch,
    FeeLengthMismatch,
    FeeTooLarge,
}

pub fn encode_route_return(route: &Route) -> Result<Vec<u8>, RouteAbiError> {
    let hop_count = route
        .path
        .len()
        .checked_sub(1)
        .ok_or(RouteAbiError::PathTooShort)?;
    if hop_count == 0 {
        return Err(RouteAbiError::PathTooShort);
    }
    if route.venues.len() != hop_count {
        return Err(RouteAbiError::VenueLengthMismatch);
    }
    if route.fees.len() != hop_count {
        return Err(RouteAbiError::FeeLengthMismatch);
    }
    if route.fees.iter().any(|fee| *fee > 0x00ff_ffff) {
        return Err(RouteAbiError::FeeTooLarge);
    }

    let path_tail_len = 32 * (1 + route.path.len());
    let venues_tail_len = 32 * (1 + route.venues.len());
    let fees_tail_len = 32 * (1 + route.fees.len());
    let path_offset = 32 * 4;
    let venues_offset = path_offset + path_tail_len;
    let fees_offset = venues_offset + venues_tail_len;

    let mut out = Vec::with_capacity(32 + 32 * 4 + path_tail_len + venues_tail_len + fees_tail_len);
    push_u256_word(&mut out, U256::from(32));
    push_u256_word(&mut out, U256::from(path_offset));
    push_u256_word(&mut out, U256::from(venues_offset));
    push_u256_word(&mut out, U256::from(fees_offset));
    push_u256_word(&mut out, route.amount_out);

    push_u256_word(&mut out, U256::from(route.path.len()));
    for token in &route.path {
        push_address_word(&mut out, *token);
    }

    push_u256_word(&mut out, U256::from(route.venues.len()));
    for venue in &route.venues {
        push_u8_word(&mut out, *venue);
    }

    push_u256_word(&mut out, U256::from(route.fees.len()));
    for fee in &route.fees {
        push_u24_word(&mut out, *fee);
    }

    Ok(out)
}

pub const IDENTITY_REGISTRY: Address = address!("8004A169FB4a3325136EB29fA0ceB6D2e539a432");
pub const REPUTATION_REGISTRY: Address = address!("8004BAa17C55a88189AE136b182e5fdA19dE9b63");

pub const ON_MORPHO_FLASH_LOAN: [u8; 4] = [0x31, 0xf5, 0x70, 0x72];
pub const ON_MORPHO_LIQUIDATE: [u8; 4] = [0x79, 0x87, 0x70, 0x91];
pub const AAVE_EXECUTE_OPERATION: [u8; 4] = [0x92, 0x0f, 0x5c, 0x84];
pub const AAVE_SIMPLE_EXECUTE_OPERATION: [u8; 4] = [0x1b, 0x11, 0xd0, 0xff];
pub const V4_UNLOCK_CALLBACK: [u8; 4] = [0x91, 0xdd, 0x73, 0x46];
pub const V3_FLASH_CALLBACK: [u8; 4] = [0xe9, 0xcb, 0xaf, 0xb0];
pub const V3_SWAP_CALLBACK: [u8; 4] = [0xfa, 0x46, 0x1e, 0x33];
pub const V2_FLASH_CALLBACK: [u8; 4] = [0x10, 0xd1, 0xe8, 0x5c];
pub const ERC3156_ON_FLASH_LOAN: [u8; 4] = [0x23, 0xe3, 0x0c, 0x8b];
pub const COW_BORROWER_CALLBACK: [u8; 4] = [0x0d, 0xae, 0x46, 0x86];
pub const UNISWAPX_REACTOR_CALLBACK: [u8; 4] = [0x58, 0x5d, 0xa6, 0x28];
pub const ROUTE_FLASH_LOAN: [u8; 4] = [0x0d, 0x81, 0x8d, 0x48];
pub const ROUTE_INTENT_FLASH_LOAN: [u8; 4] = [0x79, 0x9d, 0x1e, 0x57];
pub const MORPHO_FLASH_LOAN: [u8; 4] = [0xe0, 0x23, 0x2b, 0x42];
pub const AAVE_FLASH_LOAN: [u8; 4] = [0xab, 0x9c, 0x4b, 0x5d];
pub const AAVE_FLASH_LOAN_SIMPLE: [u8; 4] = [0x42, 0xb0, 0xb7, 0x7c];
pub const V3_POOL_FLASH: [u8; 4] = [0x49, 0x0e, 0x6c, 0xbc];
pub const V2_PAIR_SWAP: [u8; 4] = [0x02, 0x2c, 0x0d, 0x9f];
pub const V4_POOL_MANAGER_UNLOCK: [u8; 4] = [0x48, 0xc8, 0x94, 0x91];
pub const PERMIT2_APPROVE: [u8; 4] = [0x87, 0x51, 0x7c, 0x45];
pub const PERMIT2_TRANSFER_FROM: [u8; 4] = [0x36, 0xc7, 0x85, 0x16];

pub const EXECUTE_NATIVE_ARB: [u8; 4] = [0xf6, 0xf6, 0xad, 0xd1];
pub const EXECUTE_OWNED_SWAPS: [u8; 4] = [0xba, 0x44, 0x42, 0x0d];
pub const MATCH_INTERNAL: [u8; 4] = [0x5f, 0x18, 0x86, 0x78];
pub const COMPOSE_FOUR_LEG: [u8; 4] = [0x72, 0xc0, 0x46, 0x9b];
pub const EXECUTE_UNISWAPX_FILL: [u8; 4] = [0x2e, 0x13, 0x86, 0xcc];
pub const TRIGGER_COW_FLASH_LOAN_ROUTER: [u8; 4] = [0x90, 0x08, 0x66, 0xce];
pub const TRANSFER_TO_SETTLEMENT: [u8; 4] = [0x45, 0x15, 0xdd, 0x0f];
pub const SET_UNIVERSAL_ROUTER_PERMIT2_APPROVAL: [u8; 4] = [0x1a, 0x42, 0x8b, 0x49];
pub const FIND_ROUTE: [u8; 4] = [0x21, 0xbf, 0x9f, 0x26];
pub const FIND_ROUTE_WITH_HINTS: [u8; 4] = [0xc0, 0x36, 0xc8, 0xea];

pub const IDENTITY_REGISTER: [u8; 4] = [0x1a, 0xa3, 0xa0, 0x08];
pub const IDENTITY_REGISTER_WITH_URI: [u8; 4] = [0xf2, 0xc2, 0x98, 0xbe];
pub const IDENTITY_REGISTER_WITH_METADATA: [u8; 4] = [0x8e, 0xa4, 0x22, 0x86];
pub const IDENTITY_SET_AGENT_URI: [u8; 4] = [0x0a, 0xf2, 0x8b, 0xd3];
pub const IDENTITY_SET_METADATA: [u8; 4] = [0x46, 0x66, 0x48, 0xda];
pub const IDENTITY_SET_AGENT_WALLET: [u8; 4] = [0x2d, 0x1e, 0xf5, 0xae];
pub const IDENTITY_UNSET_AGENT_WALLET: [u8; 4] = [0x3f, 0xdd, 0xcf, 0x19];
pub const IDENTITY_GET_METADATA: [u8; 4] = [0xcb, 0x47, 0x99, 0xf2];
pub const IDENTITY_GET_AGENT_WALLET: [u8; 4] = [0x00, 0x33, 0x95, 0x09];
pub const IDENTITY_IS_AUTHORIZED_OR_OWNER: [u8; 4] = [0xd9, 0x5e, 0x72, 0xbe];

pub const REPUTATION_GIVE_FEEDBACK: [u8; 4] = [0x3c, 0x03, 0x6a, 0x7e];
pub const REPUTATION_REVOKE_FEEDBACK: [u8; 4] = [0x4a, 0xb3, 0xca, 0x99];
pub const REPUTATION_APPEND_RESPONSE: [u8; 4] = [0xc2, 0x34, 0x9a, 0xb2];
pub const REPUTATION_GET_SUMMARY: [u8; 4] = [0x81, 0xbb, 0xba, 0x58];
pub const REPUTATION_READ_FEEDBACK: [u8; 4] = [0x23, 0x2b, 0x08, 0x10];
pub const REPUTATION_GET_RESPONSE_COUNT: [u8; 4] = [0x6e, 0x04, 0xca, 0xcd];
pub const REPUTATION_GET_CLIENTS: [u8; 4] = [0x42, 0xdd, 0x51, 0x9c];

pub const ALL_HOOK_MASK: u16 = (1 << 14) - 1;
pub const BEFORE_INITIALIZE_FLAG: u16 = 1 << 13;
pub const AFTER_INITIALIZE_FLAG: u16 = 1 << 12;
pub const BEFORE_ADD_LIQUIDITY_FLAG: u16 = 1 << 11;
pub const AFTER_ADD_LIQUIDITY_FLAG: u16 = 1 << 10;
pub const BEFORE_REMOVE_LIQUIDITY_FLAG: u16 = 1 << 9;
pub const AFTER_REMOVE_LIQUIDITY_FLAG: u16 = 1 << 8;
pub const BEFORE_SWAP_FLAG: u16 = 1 << 7;
pub const AFTER_SWAP_FLAG: u16 = 1 << 6;
pub const BEFORE_DONATE_FLAG: u16 = 1 << 5;
pub const AFTER_DONATE_FLAG: u16 = 1 << 4;
pub const BEFORE_SWAP_RETURNS_DELTA_FLAG: u16 = 1 << 3;
pub const AFTER_SWAP_RETURNS_DELTA_FLAG: u16 = 1 << 2;
pub const AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG: u16 = 1 << 1;
pub const AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG: u16 = 1;

pub const BEFORE_SWAP_RETURN_DELTA_FLAG: u16 = BEFORE_SWAP_RETURNS_DELTA_FLAG;
pub const AFTER_SWAP_RETURN_DELTA_FLAG: u16 = AFTER_SWAP_RETURNS_DELTA_FLAG;
pub const AFTER_ADD_LIQUIDITY_RETURN_DELTA_FLAG: u16 = AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG;
pub const AFTER_REMOVE_LIQUIDITY_RETURN_DELTA_FLAG: u16 = AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG;

pub fn v4_hook_flags(hook: Address) -> u16 {
    let bytes = hook.as_slice();
    u16::from_be_bytes([bytes[18], bytes[19]]) & ALL_HOOK_MASK
}

pub fn has_v4_hook_flag(hook: Address, flag: u16) -> bool {
    (v4_hook_flags(hook) & flag) != 0
}

fn push_address_word(out: &mut Vec<u8>, address: Address) {
    out.extend_from_slice(&[0u8; 12]);
    out.extend_from_slice(address.as_slice());
}

fn push_u8_word(out: &mut Vec<u8>, value: u8) {
    out.extend_from_slice(&[0u8; 31]);
    out.push(value);
}

fn push_u24_word(out: &mut Vec<u8>, value: u32) {
    push_u256_word(out, U256::from(value));
}

fn push_u256_word(out: &mut Vec<u8>, value: U256) {
    out.extend_from_slice(&value.to_be_bytes::<32>());
}
