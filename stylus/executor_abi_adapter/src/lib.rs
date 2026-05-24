#![cfg_attr(
    not(any(test, feature = "export-abi", feature = "native-test")),
    no_main
)]
#![cfg_attr(feature = "contract-client-gen", allow(unused_imports))]
#![cfg_attr(feature = "native-test", allow(dead_code))]

extern crate alloc;

use alloc::vec::Vec;

#[cfg(not(any(test, feature = "native-test")))]
use alloy_sol_types::sol;
#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::abi::Bytes;
#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::alloy_primitives::FixedBytes;
use stylus_sdk::alloy_primitives::{Address, U256};

#[path = "../../core/src/executor_abi.rs"]
pub mod executor_abi;
#[path = "../../core/src/interface_surfaces.rs"]
pub mod interface_surfaces;

#[cfg(all(not(any(test, feature = "native-test")), not(target_arch = "wasm32")))]
mod native_hostio_shims {
    include!("../../test_hostio_shims.rs");
}

#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::prelude::*;

#[cfg(not(any(test, feature = "native-test")))]
sol! {
    error SwapArrayLengthMismatch();
    error TokenInflowArrayLengthMismatch();
}

#[cfg(not(any(test, feature = "native-test")))]
#[derive(SolidityError)]
pub enum ExecutorAbiAdapterError {
    SwapArrayLengthMismatch(SwapArrayLengthMismatch),
    TokenInflowArrayLengthMismatch(TokenInflowArrayLengthMismatch),
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct SwapArrays {
    dex_kinds: Vec<u8>,
    routers: Vec<Address>,
    call_datas: Vec<Vec<u8>>,
    token_ins: Vec<Address>,
    token_outs: Vec<Address>,
    amounts_in: Vec<U256>,
    amount_out_mins: Vec<U256>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum AdapterBuildError {
    SwapArrayLengthMismatch,
    TokenInflowArrayLengthMismatch,
}

#[cfg(not(any(test, feature = "native-test")))]
sol_storage! {
    #[entrypoint]
    pub struct ExecutorAbiAdapter {}
}

#[cfg(not(any(test, feature = "native-test")))]
#[public]
impl ExecutorAbiAdapter {
    pub fn encode_execute_native_arb(
        &self,
        flash_lender: Address,
        flash_protocol: u8,
        flash_token: Address,
        flash_amount: U256,
        dex_kinds: Vec<u8>,
        routers: Vec<Address>,
        call_datas: Vec<Bytes>,
        token_ins: Vec<Address>,
        token_outs: Vec<Address>,
        amounts_in: Vec<U256>,
        amount_out_mins: Vec<U256>,
        min_profit: U256,
        deadline: U256,
    ) -> Result<Bytes, ExecutorAbiAdapterError> {
        let swaps = collect_swap_steps(SwapArrays {
            dex_kinds,
            routers,
            call_datas: bytes_vecs_to_raw(call_datas),
            token_ins,
            token_outs,
            amounts_in,
            amount_out_mins,
        })
        .map_err(to_abi_error)?;
        Ok(executor_abi::encode_execute_native_arb_calldata(
            &executor_abi::NativeArbParams {
                flash_lender,
                flash_protocol,
                flash_token,
                flash_amount,
                swaps,
                min_profit,
                deadline,
            },
        ))
        .map(Into::into)
    }

    pub fn encode_execute_owned_swaps(
        &self,
        dex_kinds: Vec<u8>,
        routers: Vec<Address>,
        call_datas: Vec<Bytes>,
        token_ins: Vec<Address>,
        token_outs: Vec<Address>,
        amounts_in: Vec<U256>,
        amount_out_mins: Vec<U256>,
        profit_token: Address,
        min_profit: U256,
        deadline: U256,
    ) -> Result<Bytes, ExecutorAbiAdapterError> {
        let swaps = collect_swap_steps(SwapArrays {
            dex_kinds,
            routers,
            call_datas: bytes_vecs_to_raw(call_datas),
            token_ins,
            token_outs,
            amounts_in,
            amount_out_mins,
        })
        .map_err(to_abi_error)?;
        Ok(executor_abi::encode_execute_owned_swaps_calldata(
            &executor_abi::OwnedSwapsParams {
                swaps,
                profit_token,
                min_profit,
                deadline,
            },
        ))
        .map(Into::into)
    }

    pub fn encode_match_internal(
        &self,
        cow_settlement_calldata: Bytes,
        uniswapx_batch_calldata: Bytes,
        expected_token_inflows: Vec<Address>,
        expected_token_inflow_min: Vec<U256>,
        flash_lender: Address,
        flash_protocol: u8,
        flash_token: Address,
        flash_amount: U256,
        min_profit: U256,
        deadline: U256,
    ) -> Result<Bytes, ExecutorAbiAdapterError> {
        if expected_token_inflows.len() != expected_token_inflow_min.len() {
            return Err(to_abi_error(
                AdapterBuildError::TokenInflowArrayLengthMismatch,
            ));
        }
        Ok(executor_abi::encode_match_internal_calldata(
            &executor_abi::MatchParams {
                cow_settlement_calldata: cow_settlement_calldata.to_vec(),
                uniswapx_batch_calldata: uniswapx_batch_calldata.to_vec(),
                expected_token_inflows,
                expected_token_inflow_min,
                flash_lender,
                flash_protocol,
                flash_token,
                flash_amount,
                min_profit,
                deadline,
            },
        ))
        .map(Into::into)
    }

    pub fn encode_compose_four_leg(
        &self,
        across_fill_calldata: Bytes,
        dex_kinds: Vec<u8>,
        routers: Vec<Address>,
        call_datas: Vec<Bytes>,
        token_ins: Vec<Address>,
        token_outs: Vec<Address>,
        amounts_in: Vec<U256>,
        amount_out_mins: Vec<U256>,
        cow_fill_calldata: Bytes,
        uniswapx_rebalance_calldata: Bytes,
        flash_lender: Address,
        flash_protocol: u8,
        flash_token: Address,
        flash_amount: U256,
        min_profit: U256,
        deadline: U256,
    ) -> Result<Bytes, ExecutorAbiAdapterError> {
        let arb_swaps = collect_swap_steps(SwapArrays {
            dex_kinds,
            routers,
            call_datas: bytes_vecs_to_raw(call_datas),
            token_ins,
            token_outs,
            amounts_in,
            amount_out_mins,
        })
        .map_err(to_abi_error)?;
        Ok(executor_abi::encode_compose_four_leg_calldata(
            &executor_abi::ComposeParams {
                across_fill_calldata: across_fill_calldata.to_vec(),
                arb_swaps,
                cow_fill_calldata: cow_fill_calldata.to_vec(),
                uniswapx_rebalance_calldata: uniswapx_rebalance_calldata.to_vec(),
                flash_lender,
                flash_protocol,
                flash_token,
                flash_amount,
                min_profit,
                deadline,
            },
        ))
        .map(Into::into)
    }

    pub fn encode_execute_uniswapx_fill(
        &self,
        reactor: Address,
        execute_calldata: Bytes,
        callback_data: Bytes,
    ) -> Bytes {
        executor_abi::encode_execute_uniswapx_fill_calldata(
            reactor,
            execute_calldata.as_ref(),
            callback_data.as_ref(),
        )
        .into()
    }

    pub fn encode_trigger_cow_flash_loan_router(
        &self,
        expected_root: FixedBytes<32>,
        total_rounds: U256,
        initial_loan_calldata: Bytes,
        deadline: U256,
    ) -> Bytes {
        executor_abi::encode_trigger_cow_flash_loan_router_calldata(
            &executor_abi::CoWFlashLoanRouterStartParams {
                expected_root,
                total_rounds,
                initial_loan_calldata: initial_loan_calldata.to_vec(),
                deadline,
            },
        )
        .into()
    }

    pub fn encode_uniswapx_callback_data(
        &self,
        dex_kinds: Vec<u8>,
        routers: Vec<Address>,
        call_datas: Vec<Bytes>,
        token_ins: Vec<Address>,
        token_outs: Vec<Address>,
        amounts_in: Vec<U256>,
        amount_out_mins: Vec<U256>,
        callback_recipient: Address,
        callback_deadline: U256,
    ) -> Result<Bytes, ExecutorAbiAdapterError> {
        let swaps = collect_swap_steps(SwapArrays {
            dex_kinds,
            routers,
            call_datas: bytes_vecs_to_raw(call_datas),
            token_ins,
            token_outs,
            amounts_in,
            amount_out_mins,
        })
        .map_err(to_abi_error)?;
        Ok(executor_abi::encode_uniswapx_callback_data(
            &swaps,
            callback_recipient,
            callback_deadline,
        ))
        .map(Into::into)
    }
}

fn collect_swap_steps(input: SwapArrays) -> Result<Vec<executor_abi::SwapStep>, AdapterBuildError> {
    let len = input.dex_kinds.len();
    if input.routers.len() != len
        || input.call_datas.len() != len
        || input.token_ins.len() != len
        || input.token_outs.len() != len
        || input.amounts_in.len() != len
        || input.amount_out_mins.len() != len
    {
        return Err(AdapterBuildError::SwapArrayLengthMismatch);
    }

    let mut swaps = Vec::with_capacity(len);
    for index in 0..len {
        swaps.push(executor_abi::SwapStep {
            dex_kind: input.dex_kinds[index],
            router: input.routers[index],
            call_data: input.call_datas[index].clone(),
            token_in: input.token_ins[index],
            token_out: input.token_outs[index],
            amount_in: input.amounts_in[index],
            amount_out_min: input.amount_out_mins[index],
        });
    }
    Ok(swaps)
}

#[cfg(not(any(test, feature = "native-test")))]
fn bytes_vecs_to_raw(input: Vec<Bytes>) -> Vec<Vec<u8>> {
    input.into_iter().map(|bytes| bytes.to_vec()).collect()
}

#[cfg(not(any(test, feature = "native-test")))]
fn to_abi_error(error: AdapterBuildError) -> ExecutorAbiAdapterError {
    match error {
        AdapterBuildError::SwapArrayLengthMismatch => {
            ExecutorAbiAdapterError::SwapArrayLengthMismatch(SwapArrayLengthMismatch {})
        }
        AdapterBuildError::TokenInflowArrayLengthMismatch => {
            ExecutorAbiAdapterError::TokenInflowArrayLengthMismatch(
                TokenInflowArrayLengthMismatch {},
            )
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use alloy_primitives::{address, hex};

    fn swap_arrays() -> SwapArrays {
        SwapArrays {
            dex_kinds: vec![1],
            routers: vec![address!("111111125421cA6dc452d289314280a0f8842A65")],
            call_datas: vec![hex!("deadbeef").to_vec()],
            token_ins: vec![address!("af88d065e77c8cC2239327C5EDb3A432268e5831")],
            token_outs: vec![address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1")],
            amounts_in: vec![U256::from(1_000_000_000_u64)],
            amount_out_mins: vec![U256::from(250_000_000_000_000_000_u64)],
        }
    }

    #[test]
    fn flat_swap_arrays_collect_to_core_shape() {
        let swaps = collect_swap_steps(swap_arrays()).expect("valid fixture");

        assert_eq!(1, swaps.len());
        assert_eq!(1, swaps[0].dex_kind);
        assert_eq!(hex!("deadbeef").to_vec(), swaps[0].call_data);
    }

    #[test]
    fn flat_swap_arrays_reject_length_mismatch() {
        let mut input = swap_arrays();
        input.amount_out_mins.push(U256::from(1));

        assert_eq!(
            Err(AdapterBuildError::SwapArrayLengthMismatch),
            collect_swap_steps(input)
        );
    }

    #[test]
    fn adapter_shape_keeps_core_native_arb_selector() {
        let swaps = collect_swap_steps(swap_arrays()).expect("valid fixture");
        let calldata =
            executor_abi::encode_execute_native_arb_calldata(&executor_abi::NativeArbParams {
                flash_lender: address!("BA12222222228d8Ba445958a75a0704d566BF2C8"),
                flash_protocol: 1,
                flash_token: address!("af88d065e77c8cC2239327C5EDb3A432268e5831"),
                flash_amount: U256::from(1_000_000_000_u64),
                swaps,
                min_profit: U256::from(1),
                deadline: U256::from(1_900_000_000_u64),
            });

        assert_eq!(
            &interface_surfaces::EXECUTE_NATIVE_ARB,
            calldata.get(..4).expect("selector")
        );
    }
}
