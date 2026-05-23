use alloc::vec::Vec;

use stylus_sdk::alloy_primitives::{Address, U256};

use crate::mega_mev_optimization;

pub const V2_SWAP_EXACT_TOKENS_FOR_TOKENS: [u8; 4] = [0x38, 0xed, 0x17, 0x39];
pub const V3_EXACT_INPUT_SINGLE: [u8; 4] = [0x41, 0x4b, 0xf3, 0x89];
pub const V3_EXACT_INPUT_SINGLE_02: [u8; 4] = [0x04, 0xe4, 0x5a, 0xaf];
pub const V3_EXACT_INPUT: [u8; 4] = [0xc0, 0x4b, 0x8d, 0x59];
pub const V3_EXACT_INPUT_02: [u8; 4] = [0xb8, 0x58, 0x18, 0x3f];
pub const UR_EXECUTE: [u8; 4] = [0x35, 0x93, 0x56, 0x4c];
pub const UR_EXECUTE_NO_DEADLINE: [u8; 4] = [0x24, 0x85, 0x6b, 0xc3];
pub const AAVE_V3_LIQUIDATION_CALL: [u8; 4] = [0x00, 0xa7, 0x18, 0xa9];
pub const ERC20_TRANSFER: [u8; 4] = [0xa9, 0x05, 0x9c, 0xbb];

pub const FLAG_ALLOW_REVERT: u8 = 0x80;
pub const COMMAND_TYPE_MASK: u8 = 0x3f;
pub const CMD_V3_SWAP_EXACT_IN: u8 = 0x00;
pub const CMD_V3_SWAP_EXACT_OUT: u8 = 0x01;
pub const CMD_PERMIT2_TRANSFER_FROM: u8 = 0x02;
pub const CMD_V2_SWAP_EXACT_IN: u8 = 0x08;
pub const CMD_V2_SWAP_EXACT_OUT: u8 = 0x09;
pub const CMD_WRAP_ETH: u8 = 0x0b;
pub const CMD_UNWRAP_WETH: u8 = 0x0c;
pub const CMD_V4_SWAP: u8 = 0x10;
pub const CMD_EXECUTE_SUB_PLAN: u8 = 0x21;

const V3_TOKEN_BYTES: usize = 20;
const V3_FEE_BYTES: usize = 3;
const V3_HOP_BYTES: usize = V3_TOKEN_BYTES + V3_FEE_BYTES;
const BPS_DENOMINATOR: U256 = U256::from_limbs([10_000, 0, 0, 0]);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CalldataError {
    CalldataTooShort,
    UnknownSelector([u8; 4]),
    InvalidAbi,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PathError {
    EmptyPath,
    InvalidV3PathLength(usize),
    InvalidV3Fee(u32),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FrontrunMathError {
    InvalidReserves,
    InvalidFeeBps(U256),
    InvalidMarginBps(U256),
    Overflow,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum URCommand {
    V3SwapExactIn = 0,
    V3SwapExactOut = 1,
    Permit2TransferFrom = 2,
    V2SwapExactIn = 3,
    V2SwapExactOut = 4,
    WrapEth = 5,
    UnwrapWeth = 6,
    V4Swap = 7,
    ExecuteSubPlan = 8,
    Unknown = 9,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct URCommandClass {
    pub kind: URCommand,
    pub allow_revert: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct V3ExactInputSingleParams {
    pub token_in: Address,
    pub token_out: Address,
    pub fee: u32,
    pub recipient: Address,
    pub deadline: U256,
    pub amount_in: U256,
    pub amount_out_minimum: U256,
    pub sqrt_price_limit_x96: U256,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct V2SwapExactInParams {
    pub amount_in: U256,
    pub amount_out_min: U256,
    pub path: Vec<Address>,
    pub to: Address,
    pub deadline: U256,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct V3ExactInputParams {
    pub path: Vec<u8>,
    pub recipient: Address,
    pub deadline: U256,
    pub amount_in: U256,
    pub amount_out_minimum: U256,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AaveLiquidationCallParams {
    pub collateral_asset: Address,
    pub debt_asset: Address,
    pub user: Address,
    pub debt_to_cover: U256,
    pub receive_a_token: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct URCommandStep {
    pub kind: URCommand,
    pub allow_revert: bool,
    pub raw_input: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct URV2SwapExactInInput {
    pub recipient: Address,
    pub amount_in: U256,
    pub amount_out_min: U256,
    pub path: Vec<Address>,
    pub payer_is_user: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct URV3SwapExactInInput {
    pub recipient: Address,
    pub amount_in: U256,
    pub amount_out_min: U256,
    pub path: Vec<u8>,
    pub payer_is_user: bool,
}

pub fn selector_of(data: &[u8]) -> Result<[u8; 4], CalldataError> {
    if data.len() < 4 {
        return Err(CalldataError::CalldataTooShort);
    }
    Ok([data[0], data[1], data[2], data[3]])
}

pub fn is_frontrun_selector(selector: [u8; 4]) -> bool {
    matches!(
        selector,
        V2_SWAP_EXACT_TOKENS_FOR_TOKENS
            | V3_EXACT_INPUT_SINGLE
            | V3_EXACT_INPUT_SINGLE_02
            | V3_EXACT_INPUT
            | V3_EXACT_INPUT_02
            | UR_EXECUTE
            | UR_EXECUTE_NO_DEADLINE
            | AAVE_V3_LIQUIDATION_CALL
            | ERC20_TRANSFER
    )
}

pub fn is_frontrun_target(data: &[u8]) -> bool {
    selector_of(data).map(is_frontrun_selector).unwrap_or(false)
}

pub fn classify_ur_command(raw: u8) -> URCommandClass {
    let kind = match raw & COMMAND_TYPE_MASK {
        CMD_V3_SWAP_EXACT_IN => URCommand::V3SwapExactIn,
        CMD_V3_SWAP_EXACT_OUT => URCommand::V3SwapExactOut,
        CMD_PERMIT2_TRANSFER_FROM => URCommand::Permit2TransferFrom,
        CMD_V2_SWAP_EXACT_IN => URCommand::V2SwapExactIn,
        CMD_V2_SWAP_EXACT_OUT => URCommand::V2SwapExactOut,
        CMD_WRAP_ETH => URCommand::WrapEth,
        CMD_UNWRAP_WETH => URCommand::UnwrapWeth,
        CMD_V4_SWAP => URCommand::V4Swap,
        CMD_EXECUTE_SUB_PLAN => URCommand::ExecuteSubPlan,
        _ => URCommand::Unknown,
    };
    URCommandClass {
        kind,
        allow_revert: (raw & FLAG_ALLOW_REVERT) != 0,
    }
}

pub fn encode_v3_path(tokens: &[Address], fees: &[u32]) -> Result<Vec<u8>, PathError> {
    let hop_count = fees.len();
    if hop_count == 0 {
        return Err(PathError::EmptyPath);
    }
    if tokens.len() != hop_count + 1 {
        return Err(PathError::InvalidV3PathLength(tokens.len()));
    }

    let mut path = Vec::with_capacity(V3_TOKEN_BYTES + V3_HOP_BYTES * hop_count);
    path.extend_from_slice(tokens[0].as_slice());
    for (index, fee) in fees.iter().enumerate() {
        if *fee > 0x00ff_ffff {
            return Err(PathError::InvalidV3Fee(*fee));
        }
        let fee_bytes = fee.to_be_bytes();
        path.extend_from_slice(&fee_bytes[1..4]);
        path.extend_from_slice(tokens[index + 1].as_slice());
    }
    Ok(path)
}

pub fn encode_v2_swap_exact_tokens_for_tokens(
    amount_in: U256,
    amount_out_min: U256,
    path: &[Address],
    to: Address,
    deadline: U256,
) -> Result<Vec<u8>, PathError> {
    if path.len() < 2 {
        return Err(PathError::EmptyPath);
    }

    let mut out = Vec::with_capacity(4 + 32 * (6 + path.len()));
    out.extend_from_slice(&V2_SWAP_EXACT_TOKENS_FOR_TOKENS);
    push_u256_word(&mut out, amount_in);
    push_u256_word(&mut out, amount_out_min);
    push_u256_word(&mut out, U256::from(0xa0));
    push_address_word(&mut out, to);
    push_u256_word(&mut out, deadline);
    push_u256_word(&mut out, U256::from(path.len()));
    for token in path {
        push_address_word(&mut out, *token);
    }
    Ok(out)
}

pub fn encode_v3_exact_input_single(params: V3ExactInputSingleParams) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + 32 * 8);
    out.extend_from_slice(&V3_EXACT_INPUT_SINGLE);
    push_address_word(&mut out, params.token_in);
    push_address_word(&mut out, params.token_out);
    push_u256_word(&mut out, U256::from(params.fee));
    push_address_word(&mut out, params.recipient);
    push_u256_word(&mut out, params.deadline);
    push_u256_word(&mut out, params.amount_in);
    push_u256_word(&mut out, params.amount_out_minimum);
    push_u256_word(&mut out, params.sqrt_price_limit_x96);
    out
}

pub fn decode_v2_swap_exact_tokens_for_tokens(
    data: &[u8],
) -> Result<V2SwapExactInParams, CalldataError> {
    let selector = selector_of(data)?;
    if selector != V2_SWAP_EXACT_TOKENS_FOR_TOKENS {
        return Err(CalldataError::UnknownSelector(selector));
    }
    let body = function_body(data)?;
    Ok(V2SwapExactInParams {
        amount_in: read_u256(body, 0)?,
        amount_out_min: read_u256(body, 32)?,
        path: read_address_array(body, read_u256_usize(body, 64)?)?,
        to: read_address(body, 96)?,
        deadline: read_u256(body, 128)?,
    })
}

pub fn decode_v3_exact_input_single(
    data: &[u8],
) -> Result<V3ExactInputSingleParams, CalldataError> {
    let selector = selector_of(data)?;
    let body = function_body(data)?;
    match selector {
        V3_EXACT_INPUT_SINGLE => Ok(V3ExactInputSingleParams {
            token_in: read_address(body, 0)?,
            token_out: read_address(body, 32)?,
            fee: read_u24(body, 64)?,
            recipient: read_address(body, 96)?,
            deadline: read_u256(body, 128)?,
            amount_in: read_u256(body, 160)?,
            amount_out_minimum: read_u256(body, 192)?,
            sqrt_price_limit_x96: read_u160_as_u256(body, 224)?,
        }),
        V3_EXACT_INPUT_SINGLE_02 => Ok(V3ExactInputSingleParams {
            token_in: read_address(body, 0)?,
            token_out: read_address(body, 32)?,
            fee: read_u24(body, 64)?,
            recipient: read_address(body, 96)?,
            deadline: U256::ZERO,
            amount_in: read_u256(body, 128)?,
            amount_out_minimum: read_u256(body, 160)?,
            sqrt_price_limit_x96: read_u160_as_u256(body, 192)?,
        }),
        _ => Err(CalldataError::UnknownSelector(selector)),
    }
}

pub fn encode_v3_exact_input(params: V3ExactInputParams) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + 32 * 7 + padded_byte_len(params.path.len()));
    out.extend_from_slice(&V3_EXACT_INPUT);
    push_u256_word(&mut out, U256::from(0x20));
    push_u256_word(&mut out, U256::from(0xa0));
    push_address_word(&mut out, params.recipient);
    push_u256_word(&mut out, params.deadline);
    push_u256_word(&mut out, params.amount_in);
    push_u256_word(&mut out, params.amount_out_minimum);
    push_bytes_tail(&mut out, &params.path);
    out
}

pub fn encode_v3_exact_input_02(
    path: Vec<u8>,
    recipient: Address,
    amount_in: U256,
    amount_out_minimum: U256,
) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + 32 * 6 + padded_byte_len(path.len()));
    out.extend_from_slice(&V3_EXACT_INPUT_02);
    push_u256_word(&mut out, U256::from(0x20));
    push_u256_word(&mut out, U256::from(0x80));
    push_address_word(&mut out, recipient);
    push_u256_word(&mut out, amount_in);
    push_u256_word(&mut out, amount_out_minimum);
    push_bytes_tail(&mut out, &path);
    out
}

pub fn decode_v3_exact_input(data: &[u8]) -> Result<V3ExactInputParams, CalldataError> {
    let selector = selector_of(data)?;
    match selector {
        V3_EXACT_INPUT => {
            let body = data.get(36..).ok_or(CalldataError::CalldataTooShort)?;
            Ok(V3ExactInputParams {
                path: read_bytes(body, read_u256_usize(body, 0)?)?,
                recipient: read_address(body, 32)?,
                deadline: read_u256(body, 64)?,
                amount_in: read_u256(body, 96)?,
                amount_out_minimum: read_u256(body, 128)?,
            })
        }
        V3_EXACT_INPUT_02 => {
            let body = data.get(36..).ok_or(CalldataError::CalldataTooShort)?;
            Ok(V3ExactInputParams {
                path: read_bytes(body, read_u256_usize(body, 0)?)?,
                recipient: read_address(body, 32)?,
                deadline: U256::ZERO,
                amount_in: read_u256(body, 64)?,
                amount_out_minimum: read_u256(body, 96)?,
            })
        }
        _ => Err(CalldataError::UnknownSelector(selector)),
    }
}

pub fn encode_aave_v3_liquidation_call(
    collateral_asset: Address,
    debt_asset: Address,
    user: Address,
    debt_to_cover: U256,
    receive_a_token: bool,
) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + 32 * 5);
    out.extend_from_slice(&AAVE_V3_LIQUIDATION_CALL);
    push_address_word(&mut out, collateral_asset);
    push_address_word(&mut out, debt_asset);
    push_address_word(&mut out, user);
    push_u256_word(&mut out, debt_to_cover);
    push_bool_word(&mut out, receive_a_token);
    out
}

pub fn decode_aave_v3_liquidation_call(
    data: &[u8],
) -> Result<AaveLiquidationCallParams, CalldataError> {
    let selector = selector_of(data)?;
    if selector != AAVE_V3_LIQUIDATION_CALL {
        return Err(CalldataError::UnknownSelector(selector));
    }
    let body = function_body(data)?;
    Ok(AaveLiquidationCallParams {
        collateral_asset: read_address(body, 0)?,
        debt_asset: read_address(body, 32)?,
        user: read_address(body, 64)?,
        debt_to_cover: read_u256(body, 96)?,
        receive_a_token: read_bool(body, 128)?,
    })
}

pub fn encode_ur_execute(commands: &[u8], inputs: &[Vec<u8>], deadline: U256) -> Vec<u8> {
    let encoded_commands_len = encoded_bytes_len(commands.len());
    let mut out =
        Vec::with_capacity(4 + 32 * 3 + encoded_commands_len + encoded_bytes_array_len(inputs));
    out.extend_from_slice(&UR_EXECUTE);
    push_u256_word(&mut out, U256::from(0x60));
    push_u256_word(&mut out, U256::from(0x60 + encoded_commands_len));
    push_u256_word(&mut out, deadline);
    push_bytes_tail(&mut out, commands);
    push_bytes_array_tail(&mut out, inputs);
    out
}

pub fn encode_ur_execute_no_deadline(commands: &[u8], inputs: &[Vec<u8>]) -> Vec<u8> {
    let encoded_commands_len = encoded_bytes_len(commands.len());
    let mut out =
        Vec::with_capacity(4 + 32 * 2 + encoded_commands_len + encoded_bytes_array_len(inputs));
    out.extend_from_slice(&UR_EXECUTE_NO_DEADLINE);
    push_u256_word(&mut out, U256::from(0x40));
    push_u256_word(&mut out, U256::from(0x40 + encoded_commands_len));
    push_bytes_tail(&mut out, commands);
    push_bytes_array_tail(&mut out, inputs);
    out
}

pub fn decode_ur_execute(data: &[u8]) -> Result<(Vec<URCommandStep>, U256), CalldataError> {
    let selector = selector_of(data)?;
    let body = function_body(data)?;
    let (commands, inputs, deadline) = match selector {
        UR_EXECUTE => (
            read_bytes(body, read_u256_usize(body, 0)?)?,
            read_bytes_array(body, read_u256_usize(body, 32)?)?,
            read_u256(body, 64)?,
        ),
        UR_EXECUTE_NO_DEADLINE => (
            read_bytes(body, read_u256_usize(body, 0)?)?,
            read_bytes_array(body, read_u256_usize(body, 32)?)?,
            U256::ZERO,
        ),
        _ => return Err(CalldataError::UnknownSelector(selector)),
    };

    let out_len = core::cmp::min(commands.len(), inputs.len());
    let mut steps = Vec::with_capacity(out_len);
    for index in 0..out_len {
        let classified = classify_ur_command(commands[index]);
        steps.push(URCommandStep {
            kind: classified.kind,
            allow_revert: classified.allow_revert,
            raw_input: inputs[index].clone(),
        });
    }
    Ok((steps, deadline))
}

pub fn decode_ur_v2_swap_exact_in(input: &[u8]) -> Result<URV2SwapExactInInput, CalldataError> {
    Ok(URV2SwapExactInInput {
        recipient: read_address(input, 0)?,
        amount_in: read_u256(input, 32)?,
        amount_out_min: read_u256(input, 64)?,
        path: read_address_array(input, read_u256_usize(input, 96)?)?,
        payer_is_user: read_bool(input, 128)?,
    })
}

pub fn decode_ur_v3_swap_exact_in(input: &[u8]) -> Result<URV3SwapExactInInput, CalldataError> {
    Ok(URV3SwapExactInInput {
        recipient: read_address(input, 0)?,
        amount_in: read_u256(input, 32)?,
        amount_out_min: read_u256(input, 64)?,
        path: read_bytes(input, read_u256_usize(input, 96)?)?,
        payer_is_user: read_bool(input, 128)?,
    })
}

pub fn parse_v3_path(path: &[u8]) -> Result<(Vec<Address>, Vec<u32>), PathError> {
    let path_len = path.len();
    if path_len < V3_HOP_BYTES + V3_TOKEN_BYTES {
        return Err(PathError::InvalidV3PathLength(path_len));
    }
    if !(path_len - V3_TOKEN_BYTES).is_multiple_of(V3_HOP_BYTES) {
        return Err(PathError::InvalidV3PathLength(path_len));
    }

    let hop_count = (path_len - V3_TOKEN_BYTES) / V3_HOP_BYTES;
    let mut tokens = Vec::with_capacity(hop_count + 1);
    let mut fees = Vec::with_capacity(hop_count);

    tokens.push(Address::from_slice(&path[..V3_TOKEN_BYTES]));
    for index in 0..hop_count {
        let fee_offset = V3_TOKEN_BYTES + index * V3_HOP_BYTES;
        let fee = u32::from_be_bytes([
            0,
            path[fee_offset],
            path[fee_offset + 1],
            path[fee_offset + 2],
        ]);
        let token_offset = fee_offset + V3_FEE_BYTES;
        fees.push(fee);
        tokens.push(Address::from_slice(
            &path[token_offset..token_offset + V3_TOKEN_BYTES],
        ));
    }

    Ok((tokens, fees))
}

pub fn get_amount_out(
    amount_in: U256,
    reserve_in: U256,
    reserve_out: U256,
    fee_bps: U256,
) -> Result<U256, FrontrunMathError> {
    if amount_in == U256::ZERO {
        return Ok(U256::ZERO);
    }
    if reserve_in == U256::ZERO || reserve_out == U256::ZERO {
        return Err(FrontrunMathError::InvalidReserves);
    }
    if fee_bps >= BPS_DENOMINATOR {
        return Err(FrontrunMathError::InvalidFeeBps(fee_bps));
    }

    let amount_in_with_fee = amount_in
        .checked_mul(BPS_DENOMINATOR - fee_bps)
        .ok_or(FrontrunMathError::Overflow)?;
    let numerator = amount_in_with_fee
        .checked_mul(reserve_out)
        .ok_or(FrontrunMathError::Overflow)?;
    let denominator = reserve_in
        .checked_mul(BPS_DENOMINATOR)
        .and_then(|base| base.checked_add(amount_in_with_fee))
        .ok_or(FrontrunMathError::Overflow)?;

    Ok(numerator / denominator)
}

pub fn optimal_v2_frontrun_amount(
    victim_amount_in: U256,
    victim_min_out: U256,
    reserve_in: U256,
    reserve_out: U256,
    fee_bps: U256,
    margin_bps: U256,
) -> Result<U256, FrontrunMathError> {
    if fee_bps >= BPS_DENOMINATOR {
        return Err(FrontrunMathError::InvalidFeeBps(fee_bps));
    }
    if margin_bps >= BPS_DENOMINATOR {
        return Err(FrontrunMathError::InvalidMarginBps(margin_bps));
    }
    if reserve_in == U256::ZERO || reserve_out == U256::ZERO {
        return Err(FrontrunMathError::InvalidReserves);
    }
    if victim_amount_in == U256::ZERO || victim_min_out == U256::ZERO {
        return Ok(U256::ZERO);
    }

    let baseline_out = get_amount_out(victim_amount_in, reserve_in, reserve_out, fee_bps)?;
    if baseline_out <= victim_min_out {
        return Ok(U256::ZERO);
    }

    let g_bps = BPS_DENOMINATOR - fee_bps;
    let g_bps_av = checked_mul(g_bps, victim_amount_in)?;

    let c1_pos = {
        let inner_first = checked_add(checked_mul(reserve_in, BPS_DENOMINATOR)?, g_bps_av)?;
        checked_mul_div(reserve_in, inner_first, g_bps)?
    };
    let c1_neg = checked_mul_div3(victim_amount_in, reserve_in, reserve_out, victim_min_out)?;
    if c1_neg <= c1_pos {
        return Ok(U256::ZERO);
    }

    let b1_over_a1 = {
        let lhs = checked_mul_div(reserve_in, BPS_DENOMINATOR + g_bps, g_bps)?;
        let rhs = checked_mul(g_bps, victim_amount_in)? / BPS_DENOMINATOR;
        checked_add(lhs, rhs)?
    };

    let abs_c1_over_a1 = c1_neg - c1_pos;
    let half_b = b1_over_a1 / U256::from(2);
    let half_b_sq = checked_mul(half_b, half_b)?;
    let disc = checked_add(half_b_sq, abs_c1_over_a1)?;
    let sqrt_disc = mega_mev_optimization::sqrt(disc);

    if sqrt_disc <= half_b {
        return Ok(U256::ZERO);
    }

    let mut frontrun_amount = sqrt_disc - half_b;
    if margin_bps != U256::ZERO {
        frontrun_amount =
            checked_mul(frontrun_amount, BPS_DENOMINATOR - margin_bps)? / BPS_DENOMINATOR;
    }
    Ok(frontrun_amount)
}

fn checked_add(a: U256, b: U256) -> Result<U256, FrontrunMathError> {
    a.checked_add(b).ok_or(FrontrunMathError::Overflow)
}

fn checked_mul(a: U256, b: U256) -> Result<U256, FrontrunMathError> {
    a.checked_mul(b).ok_or(FrontrunMathError::Overflow)
}

fn checked_mul_div(a: U256, b: U256, denominator: U256) -> Result<U256, FrontrunMathError> {
    if denominator == U256::ZERO {
        return Err(FrontrunMathError::Overflow);
    }
    Ok(checked_mul(a, b)? / denominator)
}

fn checked_mul_div3(
    a: U256,
    b: U256,
    c: U256,
    denominator: U256,
) -> Result<U256, FrontrunMathError> {
    if denominator == U256::ZERO {
        return Err(FrontrunMathError::Overflow);
    }
    Ok(checked_mul(checked_mul(a, b)?, c)? / denominator)
}

fn push_address_word(out: &mut Vec<u8>, address: Address) {
    out.extend_from_slice(&[0u8; 12]);
    out.extend_from_slice(address.as_slice());
}

fn push_u256_word(out: &mut Vec<u8>, value: U256) {
    out.extend_from_slice(&value.to_be_bytes::<32>());
}

fn push_bool_word(out: &mut Vec<u8>, value: bool) {
    out.extend_from_slice(&[0u8; 31]);
    out.push(u8::from(value));
}

fn function_body(data: &[u8]) -> Result<&[u8], CalldataError> {
    data.get(4..).ok_or(CalldataError::CalldataTooShort)
}

fn read_word(data: &[u8], offset: usize) -> Result<&[u8], CalldataError> {
    checked_end(offset, 32)
        .and_then(|end| data.get(offset..end))
        .ok_or(CalldataError::CalldataTooShort)
}

fn read_u256(data: &[u8], offset: usize) -> Result<U256, CalldataError> {
    Ok(U256::from_be_slice(read_word(data, offset)?))
}

fn read_u256_usize(data: &[u8], offset: usize) -> Result<usize, CalldataError> {
    u256_to_usize(read_u256(data, offset)?)
}

fn read_address(data: &[u8], offset: usize) -> Result<Address, CalldataError> {
    let word = read_word(data, offset)?;
    if word[..12].iter().any(|byte| *byte != 0) {
        return Err(CalldataError::InvalidAbi);
    }
    Ok(Address::from_slice(&word[12..]))
}

fn read_u24(data: &[u8], offset: usize) -> Result<u32, CalldataError> {
    let value = read_u256(data, offset)?;
    if value > U256::from(0x00ff_ffff) {
        return Err(CalldataError::InvalidAbi);
    }
    Ok(value.to::<u32>())
}

fn read_u160_as_u256(data: &[u8], offset: usize) -> Result<U256, CalldataError> {
    let word = read_word(data, offset)?;
    if word[..12].iter().any(|byte| *byte != 0) {
        return Err(CalldataError::InvalidAbi);
    }
    Ok(U256::from_be_slice(word))
}

fn read_bool(data: &[u8], offset: usize) -> Result<bool, CalldataError> {
    match read_u256(data, offset)? {
        value if value == U256::ZERO => Ok(false),
        value if value == U256::from(1) => Ok(true),
        _ => Err(CalldataError::InvalidAbi),
    }
}

fn read_bytes(data: &[u8], offset: usize) -> Result<Vec<u8>, CalldataError> {
    let len_offset = offset;
    let len = read_u256_usize(data, len_offset)?;
    let bytes_start = checked_end(len_offset, 32).ok_or(CalldataError::CalldataTooShort)?;
    let bytes_end = checked_end(bytes_start, len).ok_or(CalldataError::CalldataTooShort)?;
    let padded_len = padded_byte_len_checked(len).ok_or(CalldataError::InvalidAbi)?;
    let padded_end = checked_end(bytes_start, padded_len).ok_or(CalldataError::CalldataTooShort)?;
    if padded_end > data.len() {
        return Err(CalldataError::CalldataTooShort);
    }
    Ok(data[bytes_start..bytes_end].to_vec())
}

fn read_address_array(data: &[u8], offset: usize) -> Result<Vec<Address>, CalldataError> {
    let len = read_u256_usize(data, offset)?;
    let elements_start = checked_end(offset, 32).ok_or(CalldataError::CalldataTooShort)?;
    let bytes_len = len.checked_mul(32).ok_or(CalldataError::InvalidAbi)?;
    let elements_end =
        checked_end(elements_start, bytes_len).ok_or(CalldataError::CalldataTooShort)?;
    if elements_end > data.len() {
        return Err(CalldataError::CalldataTooShort);
    }

    let mut out = Vec::with_capacity(len);
    for index in 0..len {
        out.push(read_address(data, elements_start + index * 32)?);
    }
    Ok(out)
}

fn read_bytes_array(data: &[u8], offset: usize) -> Result<Vec<Vec<u8>>, CalldataError> {
    let len = read_u256_usize(data, offset)?;
    let offsets_start = checked_end(offset, 32).ok_or(CalldataError::CalldataTooShort)?;
    let offsets_len = len.checked_mul(32).ok_or(CalldataError::InvalidAbi)?;
    let offsets_end =
        checked_end(offsets_start, offsets_len).ok_or(CalldataError::CalldataTooShort)?;
    if offsets_end > data.len() {
        return Err(CalldataError::CalldataTooShort);
    }

    let mut out = Vec::with_capacity(len);
    for index in 0..len {
        let relative_offset = read_u256_usize(data, offsets_start + index * 32)?;
        let element_offset = offset
            .checked_add(relative_offset)
            .ok_or(CalldataError::InvalidAbi)?;
        out.push(read_bytes(data, element_offset)?);
    }
    Ok(out)
}

fn u256_to_usize(value: U256) -> Result<usize, CalldataError> {
    let limbs = value.as_limbs();
    if limbs[1] != 0 || limbs[2] != 0 || limbs[3] != 0 || limbs[0] > usize::MAX as u64 {
        return Err(CalldataError::InvalidAbi);
    }
    Ok(limbs[0] as usize)
}

fn checked_end(offset: usize, len: usize) -> Option<usize> {
    offset.checked_add(len)
}

fn padded_byte_len(len: usize) -> usize {
    len.checked_add((32 - len % 32) % 32)
        .expect("ABI byte padding length overflow")
}

fn padded_byte_len_checked(len: usize) -> Option<usize> {
    len.checked_add((32 - len % 32) % 32)
}

fn encoded_bytes_len(len: usize) -> usize {
    32usize
        .checked_add(padded_byte_len(len))
        .expect("ABI bytes length overflow")
}

fn encoded_bytes_array_len(inputs: &[Vec<u8>]) -> usize {
    let head_len = 32usize
        .checked_add(
            inputs
                .len()
                .checked_mul(32)
                .expect("ABI bytes[] head length overflow"),
        )
        .expect("ABI bytes[] head length overflow");
    inputs.iter().fold(head_len, |acc, input| {
        acc.checked_add(encoded_bytes_len(input.len()))
            .expect("ABI bytes[] tail length overflow")
    })
}

fn push_bytes_tail(out: &mut Vec<u8>, bytes: &[u8]) {
    push_u256_word(out, U256::from(bytes.len()));
    out.extend_from_slice(bytes);
    let padding = (32 - bytes.len() % 32) % 32;
    let new_len = out.len() + padding;
    out.resize(new_len, 0);
}

fn push_bytes_array_tail(out: &mut Vec<u8>, inputs: &[Vec<u8>]) {
    push_u256_word(out, U256::from(inputs.len()));
    let mut relative_offset = 32 + inputs.len() * 32;
    for input in inputs {
        push_u256_word(out, U256::from(relative_offset));
        relative_offset += encoded_bytes_len(input.len());
    }
    for input in inputs {
        push_bytes_tail(out, input);
    }
}
