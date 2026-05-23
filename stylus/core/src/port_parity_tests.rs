use alloc::vec;
use alloy_primitives::{address, hex};
use stylus_sdk::alloy_primitives::{FixedBytes, U256, keccak256};

use crate::{
    executor_abi, frontrun_calldata, interface_surfaces, lib_uniswap, lp_transfer_lib,
    mega_mev_optimization, router_registry, singleton_arrays, step_merging, token_risk_filter,
    transient_slots,
};

const SCALE: u128 = 1_000_000_000_000_000_000;

fn m(value: u64) -> U256 {
    U256::from(value) * U256::from(SCALE)
}

fn id(label: &str) -> FixedBytes<32> {
    keccak256(label.as_bytes())
}

fn fixture_swap_step() -> executor_abi::SwapStep {
    executor_abi::SwapStep {
        dex_kind: 1,
        router: address!("111111125421cA6dc452d289314280a0f8842A65"),
        call_data: hex!("deadbeef").to_vec(),
        token_in: address!("af88d065e77c8cC2239327C5EDb3A432268e5831"),
        token_out: address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
        amount_in: U256::from(1_000_000_000u64),
        amount_out_min: U256::from(250_000_000_000_000_000u64),
    }
}

#[test]
fn router_registry_matches_solidity_constants() {
    assert_eq!(
        router_registry::router_for(router_registry::RouterKind::UniversalRouterV20),
        router_registry::UNIVERSAL_ROUTER_V20
    );
    assert_eq!(
        router_registry::UNIVERSAL_ROUTER_LATEST,
        router_registry::UNIVERSAL_ROUTER_V211
    );
    assert!(router_registry::is_known(router_registry::PERMIT2));
    assert!(router_registry::is_known(router_registry::UNIV4_STATE_VIEW));
    assert!(!router_registry::is_known(address!(
        "1111111111111111111111111111111111111111"
    )));
}

#[test]
fn universal_router_command_bytes_are_pinned() {
    assert_eq!(0x00, router_registry::commands::V3_SWAP_EXACT_IN);
    assert_eq!(0x01, router_registry::commands::V3_SWAP_EXACT_OUT);
    assert_eq!(0x08, router_registry::commands::V2_SWAP_EXACT_IN);
    assert_eq!(0x09, router_registry::commands::V2_SWAP_EXACT_OUT);
    assert_eq!(0x0b, router_registry::commands::WRAP_ETH);
    assert_eq!(0x0c, router_registry::commands::UNWRAP_WETH);
    assert_eq!(0x10, router_registry::commands::V4_SWAP);
    assert_eq!(0x21, router_registry::commands::EXECUTE_SUB_PLAN);
}

#[test]
fn transient_storage_slots_match_solidity_literals() {
    assert_eq!(
        FixedBytes::<32>::from_slice(&hex!(
            "2a51345724187232c4a2728b319ec298553f3eb52eb998941ca7a0ec47b3f640"
        )),
        transient_slots::EXPECTED_LENDER_SLOT
    );
    assert_eq!(
        FixedBytes::<32>::from_slice(&hex!(
            "a3fe3d870bd7283af33a8ef894ee9932b4710ce472ac6e764a3f66aaeb33fcf4"
        )),
        transient_slots::FLOW_ID_SLOT
    );
    assert_eq!(
        FixedBytes::<32>::from_slice(&hex!(
            "a297b7842bb27d1df6b58814cd9c628fad9558edf61186370124926f9ce1df5a"
        )),
        transient_slots::EXPECTED_V3_POOL_SLOT
    );
}

#[test]
fn transient_reentrancy_slots_are_label_hashes_and_do_not_collide() {
    let flash = keccak256(b"mev-arbitrum.TransientReentrancy.v1.flash");
    let settlement = keccak256(b"mev-arbitrum.TransientReentrancy.v1.settlement");
    let unlock = keccak256(b"mev-arbitrum.TransientReentrancy.v1.unlock");
    let composition = keccak256(b"mev-arbitrum.TransientReentrancy.v1.composition");

    assert_eq!(
        flash,
        transient_slots::reentrancy_slot(transient_slots::FlowKind::Flash)
    );
    assert_eq!(
        settlement,
        transient_slots::reentrancy_slot(transient_slots::FlowKind::Settlement)
    );
    assert_eq!(
        unlock,
        transient_slots::reentrancy_slot(transient_slots::FlowKind::Unlock)
    );
    assert_eq!(
        composition,
        transient_slots::reentrancy_slot(transient_slots::FlowKind::Composition)
    );

    let identity_slots = [
        transient_slots::EXPECTED_LENDER_SLOT,
        transient_slots::FLOW_ID_SLOT,
        transient_slots::CUMULATIVE_HASH_SLOT,
        transient_slots::EXECUTING_SLOT,
        transient_slots::EXPECTED_REACTOR_SLOT,
        transient_slots::EXPECTED_V3_POOL_SLOT,
    ];
    for ours in [flash, settlement, unlock, composition] {
        assert!(!identity_slots.contains(&ours));
    }
}

#[test]
fn lib_uniswap_address_derivation_is_order_invariant() {
    let factory = router_registry::UNIV3_FACTORY;
    let weth = address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1");
    let usdc = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");

    assert_eq!(
        lib_uniswap::compute_v3_address(factory, weth, usdc, 500),
        lib_uniswap::compute_v3_address(factory, usdc, weth, 500)
    );
    assert_ne!(
        lib_uniswap::compute_v3_address(factory, weth, usdc, 500),
        lib_uniswap::compute_v3_address(factory, weth, usdc, 3000)
    );
}

#[test]
fn singleton_arrays_wrap_one_value_without_reordering() {
    let owner = address!("2222222222222222222222222222222222222222");
    assert_eq!(vec![owner], singleton_arrays::address(owner));
    assert_eq!(vec![U256::from(42)], singleton_arrays::u256(U256::from(42)));
    assert_eq!(
        vec![vec![0xde, 0xad, 0xbe, 0xef]],
        singleton_arrays::bytes(vec![0xde, 0xad, 0xbe, 0xef])
    );
}

#[test]
fn step_merging_simulate_price_impact_matches_solidity_boundaries() {
    assert_eq!(
        U256::ZERO,
        step_merging::simulate_price_impact_u256(m(1), U256::ZERO)
    );

    let rate = step_merging::simulate_price_impact_u256(m(1), m(1_000_000_000));
    let fee_part = (U256::from(step_merging::FEE_BPS) * step_merging::SCALE) / U256::from(10_000);
    let no_impact_ceiling = step_merging::SCALE - fee_part;
    assert!(rate <= no_impact_ceiling);
    assert!(rate > no_impact_ceiling - step_merging::SCALE / U256::from(1_000_000));

    let small = step_merging::simulate_price_impact_u256(m(1_000), m(1_000_000));
    let big = step_merging::simulate_price_impact_u256(m(500_000), m(1_000_000));
    assert!(big < small);

    assert!(
        step_merging::simulate_price_impact_u256(m(10_000_000), U256::from(1))
            >= step_merging::SCALE / U256::from(10)
    );
}

#[test]
fn step_merging_consolidates_shared_intermediate_routes() {
    let eth = id("ETH");
    let weth = id("WETH");
    let usdc = id("USDC");
    let uni_v3 = id("UniV3");
    let curve = id("Curve");

    let route_a = step_merging::make_route(vec![
        step_merging::Hop {
            dex: uni_v3,
            from_token: eth,
            to_token: weth,
            amount_in: m(100),
            amount_out: m(99),
            gas: U256::from(35),
            pool_liquidity: m(85_000_000),
        },
        step_merging::Hop {
            dex: curve,
            from_token: weth,
            to_token: usdc,
            amount_in: m(99),
            amount_out: m(245_000),
            gas: U256::from(95),
            pool_liquidity: m(420_000_000),
        },
    ]);
    let route_b = step_merging::make_route(vec![
        step_merging::Hop {
            dex: uni_v3,
            from_token: eth,
            to_token: weth,
            amount_in: m(80),
            amount_out: m(79),
            gas: U256::from(30),
            pool_liquidity: m(85_000_000),
        },
        step_merging::Hop {
            dex: uni_v3,
            from_token: weth,
            to_token: usdc,
            amount_in: m(79),
            amount_out: m(197_000),
            gas: U256::from(75),
            pool_liquidity: m(180_000_000),
        },
    ]);

    let (optimised, groups) = step_merging::merge_steps_by_intermediate(&[route_a, route_b], usdc);

    assert_eq!(1, optimised.len());
    assert_eq!(1, groups.len());
    assert_eq!(m(99) + m(79), optimised[0].hops[1].amount_in);
    assert_eq!(U256::from(2), groups[0].merged_count);
    assert!(groups[0].merged_gas < groups[0].original_total_gas);
}

#[test]
fn mega_mev_bit_math_matches_solidity_harness_constants() {
    assert_eq!(U256::from(256), mega_mev_optimization::clz256(U256::ZERO));
    assert_eq!(
        U256::from(255),
        mega_mev_optimization::clz256(U256::from(1))
    );
    assert_eq!(U256::from(0), mega_mev_optimization::clz256(U256::MAX));
    assert_eq!(U256::from(256), mega_mev_optimization::ctz256(U256::ZERO));
    assert_eq!(U256::from(3), mega_mev_optimization::ctz256(U256::from(8)));
    assert_eq!(U256::from(0), mega_mev_optimization::bit_length(U256::ZERO));
    assert_eq!(
        U256::from(256),
        mega_mev_optimization::bit_length(U256::MAX)
    );
}

#[test]
fn mega_mev_power_sqrt_and_fixed_point_helpers_match_solidity() {
    assert_eq!(
        U256::ZERO,
        mega_mev_optimization::floor_power_of_two(U256::ZERO)
    );
    assert_eq!(
        U256::from(128),
        mega_mev_optimization::floor_power_of_two(U256::from(255))
    );
    assert_eq!(
        U256::from(4),
        mega_mev_optimization::lowest_bit(U256::from(12))
    );
    assert_eq!(
        Ok(U256::from(1)),
        mega_mev_optimization::next_power_of_two(U256::ZERO)
    );
    assert_eq!(
        Ok(U256::from(4)),
        mega_mev_optimization::next_power_of_two(U256::from(3))
    );
    assert_eq!(U256::from(3), mega_mev_optimization::sqrt(U256::from(15)));
    assert_eq!(
        U256::from(4),
        mega_mev_optimization::sqrt_up(U256::from(15))
    );
    assert_eq!(
        Ok(U256::from(21)),
        mega_mev_optimization::mul_div(U256::from(6), U256::from(7), U256::from(2))
    );
    assert_eq!(
        Ok(U256::from(34)),
        mega_mev_optimization::mul_div_up(U256::from(10), U256::from(10), U256::from(3))
    );
    assert_eq!(Ok(m(2)), mega_mev_optimization::mul_wad_down(m(1), m(2)));
}

#[test]
fn mega_mev_mul_div_uses_full_precision_intermediate_product() {
    assert_eq!(
        Ok(U256::MAX),
        mega_mev_optimization::mul_div(U256::MAX, U256::from(2), U256::from(2))
    );
    assert_eq!(
        Ok(U256::MAX),
        mega_mev_optimization::mul_div(U256::MAX, U256::MAX, U256::MAX)
    );
    assert_eq!(
        Err(mega_mev_optimization::MathError::Overflow),
        mega_mev_optimization::mul_div(U256::MAX, U256::MAX, U256::from(1))
    );

    let floor = mega_mev_optimization::mul_div(U256::MAX, U256::from(2), U256::from(7)).unwrap();
    assert_eq!(
        Ok(floor + U256::from(1)),
        mega_mev_optimization::mul_div_up(U256::MAX, U256::from(2), U256::from(7))
    );
    assert_eq!(
        Err(mega_mev_optimization::MathError::Overflow),
        mega_mev_optimization::mul_div_up(U256::MAX, U256::MAX, U256::from(1))
    );
}

#[test]
fn mega_mev_reserve_shape_heuristic_matches_solidity() {
    assert!(!mega_mev_optimization::reject_by_reserve_shape(
        m(1_000_000),
        m(500_000),
        U256::from(32),
        U256::from(2)
    ));
    assert!(mega_mev_optimization::reject_by_reserve_shape(
        U256::from(1),
        m(1_000_000),
        U256::from(32),
        U256::from(2)
    ));
    assert!(mega_mev_optimization::reject_by_reserve_shape(
        m(1_000_000),
        m(1),
        U256::from(32),
        U256::from(2)
    ));
}

#[test]
fn token_risk_filter_flags_and_arbitrum_major_whitelist_match_solidity() {
    assert_eq!(U256::from(1), token_risk_filter::MASK_OWNER_RENOUNCED);
    assert_eq!(U256::from(2), token_risk_filter::MASK_MINT_DISABLED);
    assert_eq!(U256::from(4), token_risk_filter::MASK_TRANSFER_TAX);
    assert_eq!(U256::from(8), token_risk_filter::MASK_SELL_TAX_HIGHER);
    assert_eq!(U256::from(16), token_risk_filter::MASK_CONCENTRATED_HOLDERS);
    assert_eq!(U256::from(32), token_risk_filter::MASK_BLACKLIST_FUNC);
    assert_eq!(U256::from(64), token_risk_filter::MASK_PAUSABLE_TRANSFERS);
    assert_eq!(U256::from(128), token_risk_filter::MASK_PROXY_MINT);
    assert_eq!(U256::from(256), token_risk_filter::MASK_NO_CODE);
    assert_eq!(U256::from(511), token_risk_filter::known_risk_mask());
    assert_eq!(300, token_risk_filter::CACHE_TTL_SECONDS);
    assert_eq!(30_000, token_risk_filter::RISK_STATICCALL_GAS);

    for major in [
        address!("af88d065e77c8cC2239327C5EDb3A432268e5831"),
        address!("Fd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"),
        address!("DA10009cBd5D07dd0CeCc66161FC93D7c9000da1"),
        address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
        address!("2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f"),
        address!("912CE59144191C1204E64559FE8253a0e49E6548"),
        address!("5979D7b546E38E414F7E9822514be443A4800529"),
        address!("1DEBd73E752bEaF79865Fd6446b0c970EaE7732f"),
        address!("EC70Dcb4A1EFa46b8F2D97C310C9c4790ba5ffA8"),
    ] {
        assert!(token_risk_filter::is_major(major));
    }

    assert!(!token_risk_filter::is_major(address!(
        "1111111111111111111111111111111111111111"
    )));
}

#[test]
fn token_risk_filter_verdict_reducer_matches_solidity_boundaries() {
    let major = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");
    let non_major = address!("1111111111111111111111111111111111111111");

    let major_verdict = token_risk_filter::assess_probe(
        major,
        token_risk_filter::ProbeVerdict {
            has_code: false,
            owner_renounced: None,
            transfer_result: token_risk_filter::TransferProbe::Unavailable,
            has_blacklist: true,
            paused: Some(true),
        },
    );
    assert_eq!(U256::ZERO, major_verdict.flags);
    assert!(major_verdict.is_safe);
    assert!(major_verdict.reasons.is_empty());

    let no_code =
        token_risk_filter::assess_probe(non_major, token_risk_filter::ProbeVerdict::no_code());
    assert_eq!(token_risk_filter::MASK_NO_CODE, no_code.flags);
    assert!(!no_code.is_safe);
    assert_eq!(
        vec![token_risk_filter::RiskReason::TokenHasNoCode],
        no_code.reasons
    );

    let paused_and_renounced = token_risk_filter::assess_probe(
        non_major,
        token_risk_filter::ProbeVerdict {
            has_code: true,
            owner_renounced: Some(true),
            transfer_result: token_risk_filter::TransferProbe::EmptyReturn,
            has_blacklist: false,
            paused: Some(true),
        },
    );
    assert_eq!(
        token_risk_filter::MASK_OWNER_RENOUNCED | token_risk_filter::MASK_PAUSABLE_TRANSFERS,
        paused_and_renounced.flags
    );
    assert!(paused_and_renounced.is_safe);
    assert_eq!(
        vec![token_risk_filter::RiskReason::TransfersArePaused],
        paused_and_renounced.reasons
    );

    let malformed_transfer = token_risk_filter::assess_probe(
        non_major,
        token_risk_filter::ProbeVerdict {
            has_code: true,
            owner_renounced: Some(false),
            transfer_result: token_risk_filter::TransferProbe::MalformedReturn,
            has_blacklist: true,
            paused: Some(false),
        },
    );
    assert_eq!(
        token_risk_filter::MASK_TRANSFER_TAX | token_risk_filter::MASK_BLACKLIST_FUNC,
        malformed_transfer.flags
    );
    assert!(!malformed_transfer.is_safe);
    assert_eq!(
        vec![
            token_risk_filter::RiskReason::TransferReturnMalformed,
            token_risk_filter::RiskReason::HasBlacklistFunction,
        ],
        malformed_transfer.reasons
    );
}

#[test]
fn frontrun_calldata_selectors_and_ur_command_classification_match_solidity() {
    assert_eq!(
        [0x38, 0xed, 0x17, 0x39],
        frontrun_calldata::V2_SWAP_EXACT_TOKENS_FOR_TOKENS
    );
    assert_eq!(
        [0x41, 0x4b, 0xf3, 0x89],
        frontrun_calldata::V3_EXACT_INPUT_SINGLE
    );
    assert_eq!(
        [0x04, 0xe4, 0x5a, 0xaf],
        frontrun_calldata::V3_EXACT_INPUT_SINGLE_02
    );
    assert_eq!([0xc0, 0x4b, 0x8d, 0x59], frontrun_calldata::V3_EXACT_INPUT);
    assert_eq!(
        [0xb8, 0x58, 0x18, 0x3f],
        frontrun_calldata::V3_EXACT_INPUT_02
    );
    assert_eq!([0x35, 0x93, 0x56, 0x4c], frontrun_calldata::UR_EXECUTE);
    assert_eq!(
        [0x24, 0x85, 0x6b, 0xc3],
        frontrun_calldata::UR_EXECUTE_NO_DEADLINE
    );
    assert_eq!(
        [0x00, 0xa7, 0x18, 0xa9],
        frontrun_calldata::AAVE_V3_LIQUIDATION_CALL
    );
    assert_eq!([0xa9, 0x05, 0x9c, 0xbb], frontrun_calldata::ERC20_TRANSFER);

    assert_eq!(
        Ok(frontrun_calldata::V2_SWAP_EXACT_TOKENS_FOR_TOKENS),
        frontrun_calldata::selector_of(&[0x38, 0xed, 0x17, 0x39, 0x00])
    );
    assert_eq!(
        Err(frontrun_calldata::CalldataError::CalldataTooShort),
        frontrun_calldata::selector_of(&[0x38, 0xed, 0x17])
    );

    for selector in [
        frontrun_calldata::V2_SWAP_EXACT_TOKENS_FOR_TOKENS,
        frontrun_calldata::V3_EXACT_INPUT_SINGLE,
        frontrun_calldata::V3_EXACT_INPUT_SINGLE_02,
        frontrun_calldata::V3_EXACT_INPUT,
        frontrun_calldata::V3_EXACT_INPUT_02,
        frontrun_calldata::UR_EXECUTE,
        frontrun_calldata::UR_EXECUTE_NO_DEADLINE,
        frontrun_calldata::AAVE_V3_LIQUIDATION_CALL,
        frontrun_calldata::ERC20_TRANSFER,
    ] {
        assert!(frontrun_calldata::is_frontrun_selector(selector));
    }
    assert!(!frontrun_calldata::is_frontrun_target(&[]));
    assert!(!frontrun_calldata::is_frontrun_selector([
        0xde, 0xad, 0xbe, 0xef
    ]));

    let v2_allow_revert = frontrun_calldata::classify_ur_command(0x88);
    assert_eq!(
        frontrun_calldata::URCommand::V2SwapExactIn,
        v2_allow_revert.kind
    );
    assert!(v2_allow_revert.allow_revert);
    assert_eq!(
        frontrun_calldata::URCommand::Unknown,
        frontrun_calldata::classify_ur_command(0x06).kind
    );
}

#[test]
fn frontrun_calldata_v3_path_encoding_roundtrips_like_solidity() {
    let weth = address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1");
    let usdc = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");
    let arb = address!("912CE59144191C1204E64559FE8253a0e49E6548");

    let path = frontrun_calldata::encode_v3_path(&[weth, usdc, arb], &[500, 3000]).unwrap();
    assert_eq!(66, path.len());
    assert_eq!(
        hex!(
            "82af49447d8a07e3bd95bd0d56f35241523fbab10001f4af88d065e77c8cc2239327c5edb3a432268e5831000bb8912ce59144191c1204e64559fe8253a0e49e6548"
        )
        .to_vec(),
        path
    );

    let (tokens, fees) = frontrun_calldata::parse_v3_path(&path).unwrap();
    assert_eq!(vec![weth, usdc, arb], tokens);
    assert_eq!(vec![500, 3000], fees);

    assert_eq!(
        Err(frontrun_calldata::PathError::InvalidV3PathLength(21)),
        frontrun_calldata::parse_v3_path(&[0u8; 21])
    );
    assert_eq!(
        Err(frontrun_calldata::PathError::EmptyPath),
        frontrun_calldata::encode_v3_path(&[weth], &[])
    );
}

#[test]
fn frontrun_calldata_common_encoders_match_cast_fixtures() {
    let weth = address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1");
    let usdc = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");
    let alice = address!("000000000000000000000000000000000000a11c");

    assert_eq!(
        hex!(
            "38ed17390000000000000000000000000000000000000000000000000de0b6b3a764000000000000000000000000000000000000000000000000000000000000b2d05e0000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000a11c0000000000000000000000000000000000000000000000000000000000003039000000000000000000000000000000000000000000000000000000000000000200000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831"
        )
        .to_vec(),
        frontrun_calldata::encode_v2_swap_exact_tokens_for_tokens(
            U256::from(SCALE),
            U256::from(3_000_000_000u64),
            &[weth, usdc],
            alice,
            U256::from(12_345)
        )
        .unwrap()
    );

    assert_eq!(
        hex!(
            "414bf38900000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e58310000000000000000000000000000000000000000000000000000000000000bb8000000000000000000000000000000000000000000000000000000000000a11c00000000000000000000000000000000000000000000000000000000000030390000000000000000000000000000000000000000000000000de0b6b3a764000000000000000000000000000000000000000000000000000000000000b2d05e000000000000000000000000000000000000000000000000000000000000000000"
        )
        .to_vec(),
        frontrun_calldata::encode_v3_exact_input_single(
            frontrun_calldata::V3ExactInputSingleParams {
                token_in: weth,
                token_out: usdc,
                fee: 3000,
                recipient: alice,
                deadline: U256::from(12_345),
                amount_in: U256::from(SCALE),
                amount_out_minimum: U256::from(3_000_000_000u64),
                sqrt_price_limit_x96: U256::ZERO,
            }
        )
    );

    assert_eq!(
        hex!(
            "00a718a900000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000000000000000000000000000000000000000a11c0000000000000000000000000000000000000000000000000000000059682f000000000000000000000000000000000000000000000000000000000000000000"
        )
        .to_vec(),
        frontrun_calldata::encode_aave_v3_liquidation_call(
            weth,
            usdc,
            alice,
            U256::from(1_500_000_000u64),
            false
        )
    );
}

#[test]
fn frontrun_calldata_decoders_match_solidity_roundtrips() {
    let weth = address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1");
    let usdc = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");
    let arb = address!("912CE59144191C1204E64559FE8253a0e49E6548");
    let alice = address!("000000000000000000000000000000000000a11c");

    let v2 = frontrun_calldata::encode_v2_swap_exact_tokens_for_tokens(
        U256::from(SCALE),
        U256::from(3_000_000_000u64),
        &[weth, usdc],
        alice,
        U256::from(12_345),
    )
    .unwrap();
    let decoded_v2 = frontrun_calldata::decode_v2_swap_exact_tokens_for_tokens(&v2).unwrap();
    assert_eq!(U256::from(SCALE), decoded_v2.amount_in);
    assert_eq!(U256::from(3_000_000_000u64), decoded_v2.amount_out_min);
    assert_eq!(vec![weth, usdc], decoded_v2.path);
    assert_eq!(alice, decoded_v2.to);
    assert_eq!(U256::from(12_345), decoded_v2.deadline);
    assert_eq!(
        Err(frontrun_calldata::CalldataError::UnknownSelector([
            0xde, 0xad, 0xbe, 0xef,
        ])),
        frontrun_calldata::decode_v2_swap_exact_tokens_for_tokens(hex!("deadbeef").as_ref())
    );

    let mut v3_single_02 = frontrun_calldata::V3_EXACT_INPUT_SINGLE_02.to_vec();
    push_test_address_word(&mut v3_single_02, weth);
    push_test_address_word(&mut v3_single_02, usdc);
    push_test_u256_word(&mut v3_single_02, U256::from(3000));
    push_test_address_word(&mut v3_single_02, alice);
    push_test_u256_word(&mut v3_single_02, U256::from(2) * U256::from(SCALE));
    push_test_u256_word(&mut v3_single_02, U256::from(6_500_000_000u64));
    push_test_u256_word(&mut v3_single_02, U256::ZERO);
    let decoded_single = frontrun_calldata::decode_v3_exact_input_single(&v3_single_02).unwrap();
    assert_eq!(weth, decoded_single.token_in);
    assert_eq!(usdc, decoded_single.token_out);
    assert_eq!(3000, decoded_single.fee);
    assert_eq!(alice, decoded_single.recipient);
    assert_eq!(U256::ZERO, decoded_single.deadline);
    assert_eq!(U256::from(2) * U256::from(SCALE), decoded_single.amount_in);
    assert_eq!(
        U256::from(6_500_000_000u64),
        decoded_single.amount_out_minimum
    );

    let aave = frontrun_calldata::encode_aave_v3_liquidation_call(
        weth,
        usdc,
        alice,
        U256::from(1_500_000_000u64),
        false,
    );
    let decoded_aave = frontrun_calldata::decode_aave_v3_liquidation_call(&aave).unwrap();
    assert_eq!(weth, decoded_aave.collateral_asset);
    assert_eq!(usdc, decoded_aave.debt_asset);
    assert_eq!(alice, decoded_aave.user);
    assert_eq!(U256::from(1_500_000_000u64), decoded_aave.debt_to_cover);
    assert!(!decoded_aave.receive_a_token);

    let v3_path = frontrun_calldata::encode_v3_path(&[weth, usdc, arb], &[500, 3000]).unwrap();
    let v3_multi =
        frontrun_calldata::encode_v3_exact_input(frontrun_calldata::V3ExactInputParams {
            path: v3_path.clone(),
            recipient: alice,
            deadline: U256::from(99_999),
            amount_in: U256::from(SCALE),
            amount_out_minimum: U256::from(100) * U256::from(SCALE),
        });
    let decoded_multi = frontrun_calldata::decode_v3_exact_input(&v3_multi).unwrap();
    assert_eq!(v3_path, decoded_multi.path);
    assert_eq!(alice, decoded_multi.recipient);
    assert_eq!(U256::from(99_999), decoded_multi.deadline);
    assert_eq!(U256::from(SCALE), decoded_multi.amount_in);
    assert_eq!(
        U256::from(100) * U256::from(SCALE),
        decoded_multi.amount_out_minimum
    );
}

#[test]
fn frontrun_calldata_v3_exact_input_calldata_matches_solidity_fixtures() {
    let weth = address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1");
    let usdc = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");
    let alice = address!("000000000000000000000000000000000000a11c");
    let path = frontrun_calldata::encode_v3_path(&[weth, usdc], &[3000]).unwrap();

    assert_eq!(
        hex!(
            "c04b8d59000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000a11c00000000000000000000000000000000000000000000000000000000000030390000000000000000000000000000000000000000000000000de0b6b3a76400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002b82af49447d8a07e3bd95bd0d56f35241523fbab1000bb8af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000000000000000000000"
        )
        .to_vec(),
        frontrun_calldata::encode_v3_exact_input(frontrun_calldata::V3ExactInputParams {
            path: path.clone(),
            recipient: alice,
            deadline: U256::from(12_345),
            amount_in: U256::from(SCALE),
            amount_out_minimum: U256::ZERO,
        })
    );

    let swap_router_02 =
        frontrun_calldata::encode_v3_exact_input_02(path, alice, U256::from(SCALE), U256::ZERO);
    assert_eq!(
        hex!(
            "b858183f00000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000a11c0000000000000000000000000000000000000000000000000de0b6b3a76400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002b82af49447d8a07e3bd95bd0d56f35241523fbab1000bb8af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000000000000000000000"
        )
        .to_vec(),
        swap_router_02
    );
    let decoded = frontrun_calldata::decode_v3_exact_input(&swap_router_02).unwrap();
    assert_eq!(alice, decoded.recipient);
    assert_eq!(U256::ZERO, decoded.deadline);
    assert_eq!(U256::from(SCALE), decoded.amount_in);
    assert_eq!(U256::ZERO, decoded.amount_out_minimum);
}

#[test]
fn frontrun_calldata_universal_router_decode_matches_solidity_shapes() {
    let weth = address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1");
    let usdc = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");
    let alice = address!("000000000000000000000000000000000000a11c");

    let v2_input = encode_test_ur_v2_input(
        alice,
        U256::from(SCALE),
        U256::from(3_000_000_000u64),
        &[weth, usdc],
        false,
    );
    let encoded = frontrun_calldata::encode_ur_execute(
        &[frontrun_calldata::FLAG_ALLOW_REVERT | frontrun_calldata::CMD_V2_SWAP_EXACT_IN],
        core::slice::from_ref(&v2_input),
        U256::from(99_999),
    );
    let (steps, deadline) = frontrun_calldata::decode_ur_execute(&encoded).unwrap();
    assert_eq!(U256::from(99_999), deadline);
    assert_eq!(1, steps.len());
    assert_eq!(frontrun_calldata::URCommand::V2SwapExactIn, steps[0].kind);
    assert!(steps[0].allow_revert);
    assert_eq!(v2_input, steps[0].raw_input);

    let decoded_v2 = frontrun_calldata::decode_ur_v2_swap_exact_in(&steps[0].raw_input).unwrap();
    assert_eq!(alice, decoded_v2.recipient);
    assert_eq!(U256::from(SCALE), decoded_v2.amount_in);
    assert_eq!(U256::from(3_000_000_000u64), decoded_v2.amount_out_min);
    assert_eq!(vec![weth, usdc], decoded_v2.path);
    assert!(!decoded_v2.payer_is_user);

    let v3_path = frontrun_calldata::encode_v3_path(&[weth, usdc], &[500]).unwrap();
    let v3_input = encode_test_ur_v3_input(
        alice,
        U256::from(2) * U256::from(SCALE),
        U256::from(6_000_000_000u64),
        &v3_path,
        true,
    );
    let encoded_no_deadline = frontrun_calldata::encode_ur_execute_no_deadline(
        &[frontrun_calldata::CMD_V3_SWAP_EXACT_IN],
        core::slice::from_ref(&v3_input),
    );
    let (steps_no_deadline, no_deadline) =
        frontrun_calldata::decode_ur_execute(&encoded_no_deadline).unwrap();
    assert_eq!(U256::ZERO, no_deadline);
    assert_eq!(
        frontrun_calldata::URCommand::V3SwapExactIn,
        steps_no_deadline[0].kind
    );
    let decoded_v3 =
        frontrun_calldata::decode_ur_v3_swap_exact_in(&steps_no_deadline[0].raw_input).unwrap();
    assert_eq!(alice, decoded_v3.recipient);
    assert_eq!(U256::from(2) * U256::from(SCALE), decoded_v3.amount_in);
    assert_eq!(U256::from(6_000_000_000u64), decoded_v3.amount_out_min);
    assert_eq!(v3_path, decoded_v3.path);
    assert!(decoded_v3.payer_is_user);
}

fn encode_test_ur_v2_input(
    recipient: alloy_primitives::Address,
    amount_in: U256,
    amount_out_min: U256,
    path: &[alloy_primitives::Address],
    payer_is_user: bool,
) -> Vec<u8> {
    let mut out = Vec::new();
    push_test_address_word(&mut out, recipient);
    push_test_u256_word(&mut out, amount_in);
    push_test_u256_word(&mut out, amount_out_min);
    push_test_u256_word(&mut out, U256::from(0xa0));
    push_test_bool_word(&mut out, payer_is_user);
    push_test_u256_word(&mut out, U256::from(path.len()));
    for token in path {
        push_test_address_word(&mut out, *token);
    }
    out
}

fn encode_test_ur_v3_input(
    recipient: alloy_primitives::Address,
    amount_in: U256,
    amount_out_min: U256,
    path: &[u8],
    payer_is_user: bool,
) -> Vec<u8> {
    let mut out = Vec::new();
    push_test_address_word(&mut out, recipient);
    push_test_u256_word(&mut out, amount_in);
    push_test_u256_word(&mut out, amount_out_min);
    push_test_u256_word(&mut out, U256::from(0xa0));
    push_test_bool_word(&mut out, payer_is_user);
    push_test_bytes_tail(&mut out, path);
    out
}

fn push_test_address_word(out: &mut Vec<u8>, address: alloy_primitives::Address) {
    out.extend_from_slice(&[0u8; 12]);
    out.extend_from_slice(address.as_slice());
}

fn push_test_u256_word(out: &mut Vec<u8>, value: U256) {
    out.extend_from_slice(&value.to_be_bytes::<32>());
}

fn push_test_bool_word(out: &mut Vec<u8>, value: bool) {
    out.extend_from_slice(&[0u8; 31]);
    out.push(u8::from(value));
}

fn push_test_bytes_tail(out: &mut Vec<u8>, bytes: &[u8]) {
    push_test_u256_word(out, U256::from(bytes.len()));
    out.extend_from_slice(bytes);
    let padding = (32 - bytes.len() % 32) % 32;
    out.extend(core::iter::repeat_n(0, padding));
}

fn read_test_u256_word(data: &[u8], offset: usize) -> U256 {
    U256::from_be_slice(&data[offset..offset + 32])
}

#[test]
fn frontrun_calldata_v2_amount_out_math_matches_solidity() {
    assert_eq!(
        Ok(U256::ZERO),
        frontrun_calldata::get_amount_out(
            U256::ZERO,
            U256::from(1000),
            U256::from(1000),
            U256::from(30)
        )
    );
    assert_eq!(
        Ok(U256::from(90)),
        frontrun_calldata::get_amount_out(
            U256::from(100),
            U256::from(1000),
            U256::from(1000),
            U256::from(30)
        )
    );

    assert_eq!(
        Err(frontrun_calldata::FrontrunMathError::InvalidReserves),
        frontrun_calldata::get_amount_out(
            U256::from(1),
            U256::ZERO,
            U256::from(1000),
            U256::from(30)
        )
    );
    assert_eq!(
        Err(frontrun_calldata::FrontrunMathError::InvalidFeeBps(
            U256::from(10_000)
        )),
        frontrun_calldata::get_amount_out(
            U256::from(1),
            U256::from(1000),
            U256::from(1000),
            U256::from(10_000)
        )
    );
}

#[test]
fn frontrun_calldata_optimal_v2_boundaries_and_worked_example_match_solidity() {
    let reserve_in = U256::from(1000) * U256::from(SCALE);
    let reserve_out = U256::from(1000) * U256::from(SCALE);
    let victim_in = U256::from(SCALE);
    let fee_bps = U256::from(30);

    assert_eq!(
        Ok(U256::ZERO),
        frontrun_calldata::optimal_v2_frontrun_amount(
            U256::ZERO,
            U256::from(1),
            reserve_in,
            reserve_out,
            fee_bps,
            U256::ZERO
        )
    );
    assert_eq!(
        Err(frontrun_calldata::FrontrunMathError::InvalidMarginBps(
            U256::from(10_000)
        )),
        frontrun_calldata::optimal_v2_frontrun_amount(
            victim_in,
            U256::from(1),
            reserve_in,
            reserve_out,
            fee_bps,
            U256::from(10_000)
        )
    );

    let baseline =
        frontrun_calldata::get_amount_out(victim_in, reserve_in, reserve_out, fee_bps).unwrap();
    assert_eq!(
        Ok(U256::ZERO),
        frontrun_calldata::optimal_v2_frontrun_amount(
            victim_in,
            baseline,
            reserve_in,
            reserve_out,
            fee_bps,
            U256::ZERO
        )
    );

    let no_margin = frontrun_calldata::optimal_v2_frontrun_amount(
        victim_in,
        baseline / U256::from(2),
        reserve_in,
        reserve_out,
        fee_bps,
        U256::ZERO,
    )
    .unwrap();
    let with_margin = frontrun_calldata::optimal_v2_frontrun_amount(
        victim_in,
        baseline / U256::from(2),
        reserve_in,
        reserve_out,
        fee_bps,
        U256::from(100),
    )
    .unwrap();
    assert!(no_margin > U256::ZERO);
    assert_eq!(
        (no_margin * U256::from(9900)) / U256::from(10_000),
        with_margin
    );

    let usdc_reserve = U256::from(10_000_000_000u64);
    let weth_reserve = U256::from(3_333_333_333_333_333_333u128);
    let victim_usdc_in = U256::from(100_000_000u64);
    let usdc_baseline =
        frontrun_calldata::get_amount_out(victim_usdc_in, usdc_reserve, weth_reserve, fee_bps)
            .unwrap();
    let victim_min_out = (usdc_baseline * U256::from(9000)) / U256::from(10_000);
    let amount = frontrun_calldata::optimal_v2_frontrun_amount(
        victim_usdc_in,
        victim_min_out,
        usdc_reserve,
        weth_reserve,
        fee_bps,
        U256::ZERO,
    )
    .unwrap();

    let analytical = U256::from(544_429_534u64);
    let diff = if amount > analytical {
        amount - analytical
    } else {
        analytical - amount
    };
    assert!(diff * U256::from(100) <= analytical * U256::from(5));
}

#[test]
fn lp_transfer_lib_selectors_and_kind_tags_match_solidity() {
    assert_eq!(0, lp_transfer_lib::LpKind::V2Erc20 as u8);
    assert_eq!(1, lp_transfer_lib::LpKind::V3Nft as u8);
    assert_eq!(2, lp_transfer_lib::LpKind::V4Erc6909 as u8);

    assert_eq!([0xa9, 0x05, 0x9c, 0xbb], lp_transfer_lib::ERC20_TRANSFER);
    assert_eq!(
        [0x42, 0x84, 0x2e, 0x0e],
        lp_transfer_lib::ERC721_SAFE_TRANSFER_FROM
    );
    assert_eq!([0x09, 0x5b, 0xcd, 0xb6], lp_transfer_lib::ERC6909_TRANSFER);
    assert_eq!(
        [0x55, 0x8a, 0x72, 0x97],
        lp_transfer_lib::ERC6909_SET_OPERATOR
    );
}

#[test]
fn lp_transfer_lib_rejects_zero_contract_or_recipient_like_solidity() {
    let pool = address!("2222222222222222222222222222222222222222");
    let to = address!("3333333333333333333333333333333333333333");

    assert_eq!(Ok(()), lp_transfer_lib::validate_move(pool, to));
    assert_eq!(
        Err(lp_transfer_lib::LpTransferError::InvalidParams),
        lp_transfer_lib::validate_move(address!("0000000000000000000000000000000000000000"), to)
    );
    assert_eq!(
        Err(lp_transfer_lib::LpTransferError::InvalidParams),
        lp_transfer_lib::validate_move(pool, address!("0000000000000000000000000000000000000000"))
    );
    assert_eq!(Ok(()), lp_transfer_lib::validate_set_operator(pool, to));
    assert_eq!(
        Err(lp_transfer_lib::LpTransferError::InvalidParams),
        lp_transfer_lib::validate_set_operator(
            pool,
            address!("0000000000000000000000000000000000000000")
        )
    );
}

#[test]
fn lp_transfer_lib_encodes_forwarding_payloads_byte_exact() {
    let from = address!("1111111111111111111111111111111111111111");
    let to = address!("2222222222222222222222222222222222222222");
    let amount = U256::from(42);
    let token_id = U256::from(7);

    assert_eq!(
        hex!(
            "a9059cbb0000000000000000000000002222222222222222222222222222222222222222000000000000000000000000000000000000000000000000000000000000002a"
        )
        .to_vec(),
        lp_transfer_lib::encode_v2_transfer(to, amount)
    );
    assert_eq!(
        hex!(
            "42842e0e000000000000000000000000111111111111111111111111111111111111111100000000000000000000000022222222222222222222222222222222222222220000000000000000000000000000000000000000000000000000000000000007"
        )
        .to_vec(),
        lp_transfer_lib::encode_v3_safe_transfer_from(from, to, token_id)
    );
    assert_eq!(
        hex!(
            "095bcdb600000000000000000000000022222222222222222222222222222222222222220000000000000000000000000000000000000000000000000000000000000007000000000000000000000000000000000000000000000000000000000000002a"
        )
        .to_vec(),
        lp_transfer_lib::encode_v4_transfer(to, token_id, amount)
    );
    assert_eq!(
        hex!(
            "558a729700000000000000000000000022222222222222222222222222222222222222220000000000000000000000000000000000000000000000000000000000000001"
        )
        .to_vec(),
        lp_transfer_lib::encode_v4_set_operator(to, true)
    );
}

#[test]
fn interface_surfaces_flash_protocols_and_selectors_match_solidity() {
    assert_eq!(0, interface_surfaces::FlashProtocol::AaveV3 as u8);
    assert_eq!(1, interface_surfaces::FlashProtocol::MorphoBlue as u8);
    assert_eq!(2, interface_surfaces::FlashProtocol::Erc3156 as u8);
    assert_eq!(3, interface_surfaces::FlashProtocol::UniswapV3 as u8);
    assert_eq!(4, interface_surfaces::FlashProtocol::UniswapV2 as u8);
    assert_eq!(5, interface_surfaces::FlashProtocol::UniswapV4 as u8);

    assert_eq!(
        [0x31, 0xf5, 0x70, 0x72],
        interface_surfaces::ON_MORPHO_FLASH_LOAN
    );
    assert_eq!(
        [0x79, 0x87, 0x70, 0x91],
        interface_surfaces::ON_MORPHO_LIQUIDATE
    );
    assert_eq!(
        [0x92, 0x0f, 0x5c, 0x84],
        interface_surfaces::AAVE_EXECUTE_OPERATION
    );
    assert_eq!(
        [0x1b, 0x11, 0xd0, 0xff],
        interface_surfaces::AAVE_SIMPLE_EXECUTE_OPERATION
    );
    assert_eq!(
        [0x91, 0xdd, 0x73, 0x46],
        interface_surfaces::V4_UNLOCK_CALLBACK
    );
    assert_eq!(
        [0xe9, 0xcb, 0xaf, 0xb0],
        interface_surfaces::V3_FLASH_CALLBACK
    );
    assert_eq!(
        [0xfa, 0x46, 0x1e, 0x33],
        interface_surfaces::V3_SWAP_CALLBACK
    );
    assert_eq!(
        [0x10, 0xd1, 0xe8, 0x5c],
        interface_surfaces::V2_FLASH_CALLBACK
    );
    assert_eq!(
        [0x23, 0xe3, 0x0c, 0x8b],
        interface_surfaces::ERC3156_ON_FLASH_LOAN
    );
    assert_eq!(
        [0x0d, 0xae, 0x46, 0x86],
        interface_surfaces::COW_BORROWER_CALLBACK
    );
    assert_eq!(
        [0x58, 0x5d, 0xa6, 0x28],
        interface_surfaces::UNISWAPX_REACTOR_CALLBACK
    );
    assert_eq!(
        [0x0d, 0x81, 0x8d, 0x48],
        interface_surfaces::ROUTE_FLASH_LOAN
    );
    assert_eq!(
        [0x79, 0x9d, 0x1e, 0x57],
        interface_surfaces::ROUTE_INTENT_FLASH_LOAN
    );
    assert_eq!(
        [0x87, 0x51, 0x7c, 0x45],
        interface_surfaces::PERMIT2_APPROVE
    );
    assert_eq!(
        [0x36, 0xc7, 0x85, 0x16],
        interface_surfaces::PERMIT2_TRANSFER_FROM
    );
}

#[test]
fn interface_surfaces_v4_hook_flags_match_solidity_constants() {
    assert_eq!(0x3fff, interface_surfaces::ALL_HOOK_MASK);
    assert_eq!(1 << 13, interface_surfaces::BEFORE_INITIALIZE_FLAG);
    assert_eq!(1 << 12, interface_surfaces::AFTER_INITIALIZE_FLAG);
    assert_eq!(1 << 11, interface_surfaces::BEFORE_ADD_LIQUIDITY_FLAG);
    assert_eq!(1 << 10, interface_surfaces::AFTER_ADD_LIQUIDITY_FLAG);
    assert_eq!(1 << 9, interface_surfaces::BEFORE_REMOVE_LIQUIDITY_FLAG);
    assert_eq!(1 << 8, interface_surfaces::AFTER_REMOVE_LIQUIDITY_FLAG);
    assert_eq!(1 << 7, interface_surfaces::BEFORE_SWAP_FLAG);
    assert_eq!(1 << 6, interface_surfaces::AFTER_SWAP_FLAG);
    assert_eq!(1 << 5, interface_surfaces::BEFORE_DONATE_FLAG);
    assert_eq!(1 << 4, interface_surfaces::AFTER_DONATE_FLAG);
    assert_eq!(1 << 3, interface_surfaces::BEFORE_SWAP_RETURNS_DELTA_FLAG);
    assert_eq!(1 << 2, interface_surfaces::AFTER_SWAP_RETURNS_DELTA_FLAG);
    assert_eq!(
        1 << 1,
        interface_surfaces::AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG
    );
    assert_eq!(
        1,
        interface_surfaces::AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG
    );

    let before_swap_hook = address!("0000000000000000000000000000000000000080");
    let after_swap_hook = address!("0000000000000000000000000000000000000040");
    assert!(interface_surfaces::has_v4_hook_flag(
        before_swap_hook,
        interface_surfaces::BEFORE_SWAP_FLAG
    ));
    assert!(!interface_surfaces::has_v4_hook_flag(
        after_swap_hook,
        interface_surfaces::BEFORE_SWAP_FLAG
    ));
    assert_eq!(0x40, interface_surfaces::v4_hook_flags(after_swap_hook));
}

#[test]
fn interface_surfaces_executor_and_pathfinder_ordinals_match_solidity() {
    assert_eq!(0, interface_surfaces::DexKind::UniswapV2 as u8);
    assert_eq!(1, interface_surfaces::DexKind::UniswapV3 as u8);
    assert_eq!(2, interface_surfaces::DexKind::UniswapV4 as u8);
    assert_eq!(3, interface_surfaces::DexKind::Curve as u8);
    assert_eq!(4, interface_surfaces::DexKind::ReservedAerodrome as u8);
    assert_eq!(5, interface_surfaces::DexKind::Aggregator as u8);
    assert_eq!(6, interface_surfaces::DexKind::MorphoBlue as u8);
    assert_eq!(7, interface_surfaces::DexKind::Algebra as u8);
    assert_eq!(8, interface_surfaces::DexKind::Solidly as u8);
    assert_eq!(9, interface_surfaces::DexKind::CurveNg as u8);
    assert_eq!(10, interface_surfaces::DexKind::BalancerV2 as u8);
    assert_eq!(28, interface_surfaces::DexKind::Native as u8);
    assert_eq!(
        Some(interface_surfaces::DexKind::Squid),
        interface_surfaces::DexKind::from_u8(24)
    );
    assert_eq!(None, interface_surfaces::DexKind::from_u8(29));

    assert_eq!(0, interface_surfaces::PathFinderVenue::V2 as u8);
    assert_eq!(1, interface_surfaces::PathFinderVenue::V3 as u8);
    assert_eq!(2, interface_surfaces::PathFinderVenue::V4 as u8);
    assert_eq!(3, interface_surfaces::PathFinderVenue::Curve as u8);
    assert_eq!(5, interface_surfaces::PathFinderVenue::Aggregator as u8);
    assert_eq!(6, interface_surfaces::PathFinderVenue::Morpho as u8);
    assert_eq!(8, interface_surfaces::PathFinderVenue::Solidly as u8);
    assert_eq!(9, interface_surfaces::PathFinderVenue::Balancer as u8);
    assert_eq!(
        Some(interface_surfaces::DexKind::UniswapV2),
        interface_surfaces::PathFinderVenue::Solidly.executor_dex_kind()
    );
    assert_eq!(
        Some(interface_surfaces::DexKind::Aggregator),
        interface_surfaces::PathFinderVenue::Balancer.executor_dex_kind()
    );
}

#[test]
fn interface_surfaces_pathfinder_route_return_encoding_matches_solidity_abi() {
    let route = interface_surfaces::Route {
        path: vec![
            address!("0000000000000000000000000000000000000001"),
            address!("0000000000000000000000000000000000000002"),
            address!("0000000000000000000000000000000000000003"),
        ],
        venues: vec![
            interface_surfaces::DexKind::UniswapV2 as u8,
            interface_surfaces::DexKind::Aggregator as u8,
        ],
        fees: vec![500, 0],
        amount_out: U256::from(123_456_789u64),
    };

    let expected = hex!(
        "0000000000000000000000000000000000000000000000000000000000000020\
         0000000000000000000000000000000000000000000000000000000000000080\
         0000000000000000000000000000000000000000000000000000000000000100\
         0000000000000000000000000000000000000000000000000000000000000160\
         00000000000000000000000000000000000000000000000000000000075bcd15\
         0000000000000000000000000000000000000000000000000000000000000003\
         0000000000000000000000000000000000000000000000000000000000000001\
         0000000000000000000000000000000000000000000000000000000000000002\
         0000000000000000000000000000000000000000000000000000000000000003\
         0000000000000000000000000000000000000000000000000000000000000002\
         0000000000000000000000000000000000000000000000000000000000000000\
         0000000000000000000000000000000000000000000000000000000000000005\
         0000000000000000000000000000000000000000000000000000000000000002\
         00000000000000000000000000000000000000000000000000000000000001f4\
         0000000000000000000000000000000000000000000000000000000000000000"
    );

    assert_eq!(
        expected.to_vec(),
        interface_surfaces::encode_route_return(&route).unwrap()
    );
}

#[test]
fn interface_surfaces_pathfinder_route_encoding_rejects_shape_mismatches() {
    let route = interface_surfaces::Route {
        path: vec![
            address!("0000000000000000000000000000000000000001"),
            address!("0000000000000000000000000000000000000002"),
        ],
        venues: vec![],
        fees: vec![0],
        amount_out: U256::from(1),
    };

    assert_eq!(
        Err(interface_surfaces::RouteAbiError::VenueLengthMismatch),
        interface_surfaces::encode_route_return(&route)
    );
}

#[test]
fn interface_surfaces_executor_pathfinder_and_registry_selectors_match_solidity() {
    assert_eq!(
        [0xf6, 0xf6, 0xad, 0xd1],
        interface_surfaces::EXECUTE_NATIVE_ARB
    );
    assert_eq!(
        [0xba, 0x44, 0x42, 0x0d],
        interface_surfaces::EXECUTE_OWNED_SWAPS
    );
    assert_eq!([0x5f, 0x18, 0x86, 0x78], interface_surfaces::MATCH_INTERNAL);
    assert_eq!(
        [0x72, 0xc0, 0x46, 0x9b],
        interface_surfaces::COMPOSE_FOUR_LEG
    );
    assert_eq!(
        [0x2e, 0x13, 0x86, 0xcc],
        interface_surfaces::EXECUTE_UNISWAPX_FILL
    );
    assert_eq!(
        [0x90, 0x08, 0x66, 0xce],
        interface_surfaces::TRIGGER_COW_FLASH_LOAN_ROUTER
    );
    assert_eq!(
        [0x45, 0x15, 0xdd, 0x0f],
        interface_surfaces::TRANSFER_TO_SETTLEMENT
    );
    assert_eq!(
        [0x1a, 0x42, 0x8b, 0x49],
        interface_surfaces::SET_UNIVERSAL_ROUTER_PERMIT2_APPROVAL
    );
    assert_eq!([0x21, 0xbf, 0x9f, 0x26], interface_surfaces::FIND_ROUTE);
    assert_eq!(
        [0xc0, 0x36, 0xc8, 0xea],
        interface_surfaces::FIND_ROUTE_WITH_HINTS
    );

    assert_eq!(
        [0x1a, 0xa3, 0xa0, 0x08],
        interface_surfaces::IDENTITY_REGISTER
    );
    assert_eq!(
        [0xf2, 0xc2, 0x98, 0xbe],
        interface_surfaces::IDENTITY_REGISTER_WITH_URI
    );
    assert_eq!(
        [0x8e, 0xa4, 0x22, 0x86],
        interface_surfaces::IDENTITY_REGISTER_WITH_METADATA
    );
    assert_eq!(
        [0x0a, 0xf2, 0x8b, 0xd3],
        interface_surfaces::IDENTITY_SET_AGENT_URI
    );
    assert_eq!(
        [0x46, 0x66, 0x48, 0xda],
        interface_surfaces::IDENTITY_SET_METADATA
    );
    assert_eq!(
        [0x2d, 0x1e, 0xf5, 0xae],
        interface_surfaces::IDENTITY_SET_AGENT_WALLET
    );
    assert_eq!(
        [0x3f, 0xdd, 0xcf, 0x19],
        interface_surfaces::IDENTITY_UNSET_AGENT_WALLET
    );
    assert_eq!(
        [0xcb, 0x47, 0x99, 0xf2],
        interface_surfaces::IDENTITY_GET_METADATA
    );
    assert_eq!(
        [0x00, 0x33, 0x95, 0x09],
        interface_surfaces::IDENTITY_GET_AGENT_WALLET
    );
    assert_eq!(
        [0xd9, 0x5e, 0x72, 0xbe],
        interface_surfaces::IDENTITY_IS_AUTHORIZED_OR_OWNER
    );

    assert_eq!(
        [0x3c, 0x03, 0x6a, 0x7e],
        interface_surfaces::REPUTATION_GIVE_FEEDBACK
    );
    assert_eq!(
        [0x4a, 0xb3, 0xca, 0x99],
        interface_surfaces::REPUTATION_REVOKE_FEEDBACK
    );
    assert_eq!(
        [0xc2, 0x34, 0x9a, 0xb2],
        interface_surfaces::REPUTATION_APPEND_RESPONSE
    );
    assert_eq!(
        [0x81, 0xbb, 0xba, 0x58],
        interface_surfaces::REPUTATION_GET_SUMMARY
    );
    assert_eq!(
        [0x23, 0x2b, 0x08, 0x10],
        interface_surfaces::REPUTATION_READ_FEEDBACK
    );
    assert_eq!(
        [0x6e, 0x04, 0xca, 0xcd],
        interface_surfaces::REPUTATION_GET_RESPONSE_COUNT
    );
    assert_eq!(
        [0x42, 0xdd, 0x51, 0x9c],
        interface_surfaces::REPUTATION_GET_CLIENTS
    );
}

#[test]
fn executor_abi_native_arb_calldata_matches_ts_fixture() {
    let params = executor_abi::NativeArbParams {
        flash_lender: address!("794a61358D6845594F94dc1DB02A252b5b4814aD"),
        flash_protocol: 0,
        flash_token: address!("af88d065e77c8cC2239327C5EDb3A432268e5831"),
        flash_amount: U256::from(1_000_000_000u64),
        swaps: vec![fixture_swap_step()],
        min_profit: U256::from(1_000_000u64),
        deadline: U256::from(1_730_000_000u64),
    };

    assert_eq!(
        hex!(
            "f6f6add10000000000000000000000000000000000000000000000000000000000000020000000000000000000000000794a61358d6845594f94dc1db02a252b5b4814ad0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000000000000000000000000000000000003b9aca0000000000000000000000000000000000000000000000000000000000000000e000000000000000000000000000000000000000000000000000000000000f424000000000000000000000000000000000000000000000000000000000671db480000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000001000000000000000000000000111111125421ca6dc452d289314280a0f8842a6500000000000000000000000000000000000000000000000000000000000000e0000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e583100000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000000000000000000000000000000000003b9aca0000000000000000000000000000000000000000000000000003782dace9d900000000000000000000000000000000000000000000000000000000000000000004deadbeef00000000000000000000000000000000000000000000000000000000"
        )
        .to_vec(),
        executor_abi::encode_execute_native_arb_calldata(&params)
    );
}

#[test]
fn executor_abi_match_internal_calldata_matches_ts_fixture() {
    let params = executor_abi::MatchParams {
        cow_settlement_calldata: hex!("1111").to_vec(),
        uniswapx_batch_calldata: hex!("2222").to_vec(),
        expected_token_inflows: vec![
            address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
            address!("af88d065e77c8cC2239327C5EDb3A432268e5831"),
        ],
        expected_token_inflow_min: vec![
            U256::from(1_000_000_000_000_000_000u64),
            U256::from(3_000_000_000u64),
        ],
        flash_lender: address!("794a61358D6845594F94dc1DB02A252b5b4814aD"),
        flash_protocol: 0,
        flash_token: address!("af88d065e77c8cC2239327C5EDb3A432268e5831"),
        flash_amount: U256::from(10_000_000_000u64),
        min_profit: U256::from(5_000_000u64),
        deadline: U256::from(1_730_000_000u64),
    };

    assert_eq!(
        hex!(
            "5f18867800000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000140000000000000000000000000000000000000000000000000000000000000018000000000000000000000000000000000000000000000000000000000000001c00000000000000000000000000000000000000000000000000000000000000220000000000000000000000000794a61358d6845594f94dc1db02a252b5b4814ad0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e583100000000000000000000000000000000000000000000000000000002540be40000000000000000000000000000000000000000000000000000000000004c4b4000000000000000000000000000000000000000000000000000000000671db4800000000000000000000000000000000000000000000000000000000000000002111100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000022222000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e583100000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000de0b6b3a764000000000000000000000000000000000000000000000000000000000000b2d05e00"
        )
        .to_vec(),
        executor_abi::encode_match_internal_calldata(&params)
    );
}

#[test]
fn executor_abi_compose_four_leg_calldata_matches_ts_fixture() {
    let params = executor_abi::ComposeParams {
        across_fill_calldata: hex!("a1a1a1a1").to_vec(),
        arb_swaps: vec![
            fixture_swap_step(),
            executor_abi::SwapStep {
                dex_kind: 5,
                router: address!("6131B5fae19EA4f9D964eAc0408E4408b66337b5"),
                call_data: hex!("cafef00d").to_vec(),
                token_in: address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
                token_out: address!("Fd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"),
                amount_in: U256::ZERO,
                amount_out_min: U256::from(1_001_000_000u64),
            },
        ],
        cow_fill_calldata: hex!("b2b2b2b2").to_vec(),
        uniswapx_rebalance_calldata: hex!("c3c3c3c3").to_vec(),
        flash_lender: address!("794a61358D6845594F94dc1DB02A252b5b4814aD"),
        flash_protocol: 0,
        flash_token: address!("af88d065e77c8cC2239327C5EDb3A432268e5831"),
        flash_amount: U256::from(50_000_000_000u64),
        min_profit: U256::from(50_000_000u64),
        deadline: U256::from(1_730_000_000u64),
    };

    assert_eq!(
        hex!(
            "72c0469b00000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000140000000000000000000000000000000000000000000000000000000000000018000000000000000000000000000000000000000000000000000000000000004200000000000000000000000000000000000000000000000000000000000000460000000000000000000000000794a61358d6845594f94dc1db02a252b5b4814ad0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e58310000000000000000000000000000000000000000000000000000000ba43b74000000000000000000000000000000000000000000000000000000000002faf08000000000000000000000000000000000000000000000000000000000671db4800000000000000000000000000000000000000000000000000000000000000004a1a1a1a1000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000001600000000000000000000000000000000000000000000000000000000000000001000000000000000000000000111111125421ca6dc452d289314280a0f8842a6500000000000000000000000000000000000000000000000000000000000000e0000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e583100000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000000000000000000000000000000000003b9aca0000000000000000000000000000000000000000000000000003782dace9d900000000000000000000000000000000000000000000000000000000000000000004deadbeef0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000050000000000000000000000006131b5fae19ea4f9d964eac0408e4408b66337b500000000000000000000000000000000000000000000000000000000000000e000000000000000000000000082af49447d8a07e3bd95bd0d56f35241523fbab1000000000000000000000000fd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb90000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003baa0c400000000000000000000000000000000000000000000000000000000000000004cafef00d000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004b2b2b2b2000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004c3c3c3c300000000000000000000000000000000000000000000000000000000"
        )
        .to_vec(),
        executor_abi::encode_compose_four_leg_calldata(&params)
    );
}

#[test]
fn executor_abi_uniswapx_fill_and_callback_offsets_match_viem_shape() {
    let executor = address!("000000000000000000000000000000000000beef");
    let reactor = address!("6000da47483062A0D734Ba3dc7576Ce6A0B645C4");
    let step = executor_abi::SwapStep {
        dex_kind: 5,
        router: address!("111111125421cA6dc452d289314280a0f8842A65"),
        call_data: hex!("5678").to_vec(),
        token_in: address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
        token_out: address!("af88d065e77c8cC2239327C5EDb3A432268e5831"),
        amount_in: U256::from(1_000u64),
        amount_out_min: U256::from(900u64),
    };
    let callback_data = executor_abi::encode_uniswapx_callback_data(
        &[step],
        executor,
        U256::from(1_800_000_060u64),
    );

    assert_eq!(U256::from(96), read_test_u256_word(&callback_data, 0));
    assert_eq!(executor.as_slice(), &callback_data[44..64]);
    assert_eq!(
        U256::from(1_800_000_060u64),
        read_test_u256_word(&callback_data, 64)
    );
    assert_eq!(U256::from(1), read_test_u256_word(&callback_data, 96));
    assert_eq!(U256::from(32), read_test_u256_word(&callback_data, 128));

    let direct =
        executor_abi::encode_execute_uniswapx_fill_calldata(reactor, &hex!("1234"), &callback_data);
    assert_eq!(
        interface_surfaces::EXECUTE_UNISWAPX_FILL,
        [direct[0], direct[1], direct[2], direct[3]]
    );
    assert_eq!(reactor.as_slice(), &direct[16..36]);
    assert_eq!(U256::from(96), read_test_u256_word(&direct, 36));
    assert_eq!(U256::from(160), read_test_u256_word(&direct, 68));
    assert_eq!(U256::from(2), read_test_u256_word(&direct, 100));
    assert_eq!(hex!("1234").as_slice(), &direct[132..134]);
}

#[test]
fn interface_surfaces_erc8004_addresses_match_arbitrum_canonicals() {
    assert_eq!(
        address!("8004A169FB4a3325136EB29fA0ceB6D2e539a432"),
        interface_surfaces::IDENTITY_REGISTRY
    );
    assert_eq!(
        address!("8004BAa17C55a88189AE136b182e5fdA19dE9b63"),
        interface_surfaces::REPUTATION_REGISTRY
    );
}
