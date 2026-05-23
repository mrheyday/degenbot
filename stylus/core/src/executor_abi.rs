use alloc::vec::Vec;

use stylus_sdk::alloy_primitives::{Address, FixedBytes, U256};

use crate::interface_surfaces;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SwapStep {
    pub dex_kind: u8,
    pub router: Address,
    pub call_data: Vec<u8>,
    pub token_in: Address,
    pub token_out: Address,
    pub amount_in: U256,
    pub amount_out_min: U256,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NativeArbParams {
    pub flash_lender: Address,
    pub flash_protocol: u8,
    pub flash_token: Address,
    pub flash_amount: U256,
    pub swaps: Vec<SwapStep>,
    pub min_profit: U256,
    pub deadline: U256,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OwnedSwapsParams {
    pub swaps: Vec<SwapStep>,
    pub profit_token: Address,
    pub min_profit: U256,
    pub deadline: U256,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MatchParams {
    pub cow_settlement_calldata: Vec<u8>,
    pub uniswapx_batch_calldata: Vec<u8>,
    pub expected_token_inflows: Vec<Address>,
    pub expected_token_inflow_min: Vec<U256>,
    pub flash_lender: Address,
    pub flash_protocol: u8,
    pub flash_token: Address,
    pub flash_amount: U256,
    pub min_profit: U256,
    pub deadline: U256,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ComposeParams {
    pub across_fill_calldata: Vec<u8>,
    pub arb_swaps: Vec<SwapStep>,
    pub cow_fill_calldata: Vec<u8>,
    pub uniswapx_rebalance_calldata: Vec<u8>,
    pub flash_lender: Address,
    pub flash_protocol: u8,
    pub flash_token: Address,
    pub flash_amount: U256,
    pub min_profit: U256,
    pub deadline: U256,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CoWFlashLoanRouterStartParams {
    pub expected_root: FixedBytes<32>,
    pub total_rounds: U256,
    pub initial_loan_calldata: Vec<u8>,
    pub deadline: U256,
}

#[must_use]
pub fn encode_execute_native_arb_calldata(params: &NativeArbParams) -> Vec<u8> {
    encode_single_dynamic_tuple_call(
        interface_surfaces::EXECUTE_NATIVE_ARB,
        encode_native_arb_tuple(params),
    )
}

#[must_use]
pub fn encode_execute_owned_swaps_calldata(params: &OwnedSwapsParams) -> Vec<u8> {
    encode_single_dynamic_tuple_call(
        interface_surfaces::EXECUTE_OWNED_SWAPS,
        encode_owned_swaps_tuple(params),
    )
}

#[must_use]
pub fn encode_match_internal_calldata(params: &MatchParams) -> Vec<u8> {
    encode_single_dynamic_tuple_call(
        interface_surfaces::MATCH_INTERNAL,
        encode_match_tuple(params),
    )
}

#[must_use]
pub fn encode_compose_four_leg_calldata(params: &ComposeParams) -> Vec<u8> {
    encode_single_dynamic_tuple_call(
        interface_surfaces::COMPOSE_FOUR_LEG,
        encode_compose_tuple(params),
    )
}

#[must_use]
pub fn encode_execute_uniswapx_fill_calldata(
    reactor: Address,
    execute_calldata: &[u8],
    callback_data: &[u8],
) -> Vec<u8> {
    let execute_tail_len = encoded_bytes_len(execute_calldata.len());
    let execute_offset = 32 * 3;
    let callback_offset = execute_offset + execute_tail_len;

    let mut out = Vec::with_capacity(4 + callback_offset + encoded_bytes_len(callback_data.len()));
    out.extend_from_slice(&interface_surfaces::EXECUTE_UNISWAPX_FILL);
    push_address_word(&mut out, reactor);
    push_u256_word(&mut out, U256::from(execute_offset));
    push_u256_word(&mut out, U256::from(callback_offset));
    push_bytes_tail(&mut out, execute_calldata);
    push_bytes_tail(&mut out, callback_data);
    out
}

#[must_use]
pub fn encode_trigger_cow_flash_loan_router_calldata(
    params: &CoWFlashLoanRouterStartParams,
) -> Vec<u8> {
    encode_single_dynamic_tuple_call(
        interface_surfaces::TRIGGER_COW_FLASH_LOAN_ROUTER,
        encode_cow_flash_loan_router_start_tuple(params),
    )
}

#[must_use]
pub fn encode_uniswapx_callback_data(
    steps: &[SwapStep],
    callback_recipient: Address,
    callback_deadline: U256,
) -> Vec<u8> {
    let steps_tail = encode_swap_steps_array(steps);
    let steps_offset = 32 * 3;

    let mut out = Vec::with_capacity(steps_offset + steps_tail.len());
    push_u256_word(&mut out, U256::from(steps_offset));
    push_address_word(&mut out, callback_recipient);
    push_u256_word(&mut out, callback_deadline);
    out.extend_from_slice(&steps_tail);
    out
}

fn encode_single_dynamic_tuple_call(selector: [u8; 4], tuple_tail: Vec<u8>) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + 32 + tuple_tail.len());
    out.extend_from_slice(&selector);
    push_u256_word(&mut out, U256::from(32));
    out.extend_from_slice(&tuple_tail);
    out
}

fn encode_native_arb_tuple(params: &NativeArbParams) -> Vec<u8> {
    let swaps_tail = encode_swap_steps_array(&params.swaps);
    let swaps_offset = 32 * 7;

    let mut out = Vec::with_capacity(swaps_offset + swaps_tail.len());
    push_address_word(&mut out, params.flash_lender);
    push_u8_word(&mut out, params.flash_protocol);
    push_address_word(&mut out, params.flash_token);
    push_u256_word(&mut out, params.flash_amount);
    push_u256_word(&mut out, U256::from(swaps_offset));
    push_u256_word(&mut out, params.min_profit);
    push_u256_word(&mut out, params.deadline);
    out.extend_from_slice(&swaps_tail);
    out
}

fn encode_owned_swaps_tuple(params: &OwnedSwapsParams) -> Vec<u8> {
    let swaps_tail = encode_swap_steps_array(&params.swaps);
    let swaps_offset = 32 * 4;

    let mut out = Vec::with_capacity(swaps_offset + swaps_tail.len());
    push_u256_word(&mut out, U256::from(swaps_offset));
    push_address_word(&mut out, params.profit_token);
    push_u256_word(&mut out, params.min_profit);
    push_u256_word(&mut out, params.deadline);
    out.extend_from_slice(&swaps_tail);
    out
}

fn encode_match_tuple(params: &MatchParams) -> Vec<u8> {
    let cow_tail = encode_bytes_tail(&params.cow_settlement_calldata);
    let uniswapx_tail = encode_bytes_tail(&params.uniswapx_batch_calldata);
    let inflows_tail = encode_address_array(&params.expected_token_inflows);
    let inflow_min_tail = encode_u256_array(&params.expected_token_inflow_min);

    let cow_offset = 32 * 10;
    let uniswapx_offset = cow_offset + cow_tail.len();
    let inflows_offset = uniswapx_offset + uniswapx_tail.len();
    let inflow_min_offset = inflows_offset + inflows_tail.len();

    let mut out = Vec::with_capacity(inflow_min_offset + inflow_min_tail.len());
    push_u256_word(&mut out, U256::from(cow_offset));
    push_u256_word(&mut out, U256::from(uniswapx_offset));
    push_u256_word(&mut out, U256::from(inflows_offset));
    push_u256_word(&mut out, U256::from(inflow_min_offset));
    push_address_word(&mut out, params.flash_lender);
    push_u8_word(&mut out, params.flash_protocol);
    push_address_word(&mut out, params.flash_token);
    push_u256_word(&mut out, params.flash_amount);
    push_u256_word(&mut out, params.min_profit);
    push_u256_word(&mut out, params.deadline);
    out.extend_from_slice(&cow_tail);
    out.extend_from_slice(&uniswapx_tail);
    out.extend_from_slice(&inflows_tail);
    out.extend_from_slice(&inflow_min_tail);
    out
}

fn encode_compose_tuple(params: &ComposeParams) -> Vec<u8> {
    let across_tail = encode_bytes_tail(&params.across_fill_calldata);
    let swaps_tail = encode_swap_steps_array(&params.arb_swaps);
    let cow_tail = encode_bytes_tail(&params.cow_fill_calldata);
    let uniswapx_tail = encode_bytes_tail(&params.uniswapx_rebalance_calldata);

    let across_offset = 32 * 10;
    let swaps_offset = across_offset + across_tail.len();
    let cow_offset = swaps_offset + swaps_tail.len();
    let uniswapx_offset = cow_offset + cow_tail.len();

    let mut out = Vec::with_capacity(uniswapx_offset + uniswapx_tail.len());
    push_u256_word(&mut out, U256::from(across_offset));
    push_u256_word(&mut out, U256::from(swaps_offset));
    push_u256_word(&mut out, U256::from(cow_offset));
    push_u256_word(&mut out, U256::from(uniswapx_offset));
    push_address_word(&mut out, params.flash_lender);
    push_u8_word(&mut out, params.flash_protocol);
    push_address_word(&mut out, params.flash_token);
    push_u256_word(&mut out, params.flash_amount);
    push_u256_word(&mut out, params.min_profit);
    push_u256_word(&mut out, params.deadline);
    out.extend_from_slice(&across_tail);
    out.extend_from_slice(&swaps_tail);
    out.extend_from_slice(&cow_tail);
    out.extend_from_slice(&uniswapx_tail);
    out
}

fn encode_cow_flash_loan_router_start_tuple(params: &CoWFlashLoanRouterStartParams) -> Vec<u8> {
    let initial_loan_tail = encode_bytes_tail(&params.initial_loan_calldata);
    let initial_loan_offset = 32 * 4;

    let mut out = Vec::with_capacity(initial_loan_offset + initial_loan_tail.len());
    push_bytes32_word(&mut out, params.expected_root);
    push_u256_word(&mut out, params.total_rounds);
    push_u256_word(&mut out, U256::from(initial_loan_offset));
    push_u256_word(&mut out, params.deadline);
    out.extend_from_slice(&initial_loan_tail);
    out
}

fn encode_swap_steps_array(swaps: &[SwapStep]) -> Vec<u8> {
    let encoded_steps: Vec<Vec<u8>> = swaps.iter().map(encode_swap_step_tuple).collect();
    let offsets_len = swaps.len() * 32;
    let tails_len: usize = encoded_steps.iter().map(Vec::len).sum();

    let mut out = Vec::with_capacity(32 + offsets_len + tails_len);
    push_u256_word(&mut out, U256::from(swaps.len()));
    let mut relative_offset = offsets_len;
    for step in &encoded_steps {
        push_u256_word(&mut out, U256::from(relative_offset));
        relative_offset += step.len();
    }
    for step in encoded_steps {
        out.extend_from_slice(&step);
    }
    out
}

fn encode_swap_step_tuple(step: &SwapStep) -> Vec<u8> {
    let call_data_tail = encode_bytes_tail(&step.call_data);
    let call_data_offset = 32 * 7;

    let mut out = Vec::with_capacity(call_data_offset + call_data_tail.len());
    push_u8_word(&mut out, step.dex_kind);
    push_address_word(&mut out, step.router);
    push_u256_word(&mut out, U256::from(call_data_offset));
    push_address_word(&mut out, step.token_in);
    push_address_word(&mut out, step.token_out);
    push_u256_word(&mut out, step.amount_in);
    push_u256_word(&mut out, step.amount_out_min);
    out.extend_from_slice(&call_data_tail);
    out
}

fn encode_address_array(values: &[Address]) -> Vec<u8> {
    let mut out = Vec::with_capacity(32 + values.len() * 32);
    push_u256_word(&mut out, U256::from(values.len()));
    for value in values {
        push_address_word(&mut out, *value);
    }
    out
}

fn encode_u256_array(values: &[U256]) -> Vec<u8> {
    let mut out = Vec::with_capacity(32 + values.len() * 32);
    push_u256_word(&mut out, U256::from(values.len()));
    for value in values {
        push_u256_word(&mut out, *value);
    }
    out
}

fn encode_bytes_tail(bytes: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(encoded_bytes_len(bytes.len()));
    push_bytes_tail(&mut out, bytes);
    out
}

fn encoded_bytes_len(len: usize) -> usize {
    32 + padded_byte_len(len)
}

fn padded_byte_len(len: usize) -> usize {
    len + (32 - len % 32) % 32
}

fn push_bytes_tail(out: &mut Vec<u8>, bytes: &[u8]) {
    push_u256_word(out, U256::from(bytes.len()));
    out.extend_from_slice(bytes);
    out.resize(out.len() + (32 - bytes.len() % 32) % 32, 0);
}

fn push_address_word(out: &mut Vec<u8>, address: Address) {
    out.extend_from_slice(&[0u8; 12]);
    out.extend_from_slice(address.as_slice());
}

fn push_bytes32_word(out: &mut Vec<u8>, value: FixedBytes<32>) {
    out.extend_from_slice(value.as_slice());
}

fn push_u8_word(out: &mut Vec<u8>, value: u8) {
    out.extend_from_slice(&[0u8; 31]);
    out.push(value);
}

fn push_u256_word(out: &mut Vec<u8>, value: U256) {
    out.extend_from_slice(&value.to_be_bytes::<32>());
}
