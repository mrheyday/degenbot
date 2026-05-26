//! `PyO3` bindings for executor calldata construction.

use crate::alloy_py::extract_python_u256;
use crate::execution::{
    encode_compose_four_leg_calldata, encode_match_internal_calldata, encode_native_arb_calldata,
    ComposeParams, DexKind, FlashProtocol, MatchParams, NativeArbParams, SwapStep,
};
use alloy::primitives::{Address, Bytes};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyBytes, PyDict, PyList};

fn parse_address(value: &Bound<'_, PyAny>) -> PyResult<Address> {
    let address = value.extract::<String>()?;
    crate::address_utils::parse_address(&address).map_err(Into::into)
}

fn parse_bytes(value: &Bound<'_, PyAny>) -> PyResult<Bytes> {
    if let Ok(bytes) = value.extract::<&[u8]>() {
        return Ok(Bytes::from(bytes.to_vec()));
    }

    let text = value.extract::<String>()?;
    let stripped = text.strip_prefix("0x").unwrap_or(&text);
    let bytes = alloy::hex::decode(stripped)
        .map_err(|e| PyValueError::new_err(format!("Invalid hex bytes '{text}': {e}")))?;
    Ok(Bytes::from(bytes))
}

fn parse_flash_protocol(value: &str) -> PyResult<FlashProtocol> {
    match value.to_ascii_lowercase().as_str() {
        "aave" => Ok(FlashProtocol::Aave),
        "morpho" => Ok(FlashProtocol::Morpho),
        "erc3156" | "erc-3156" => Ok(FlashProtocol::ERC3156),
        "univ3" | "uniswapv3" | "uni_v3" => Ok(FlashProtocol::UniV3),
        other => Err(PyValueError::new_err(format!(
            "Unknown flash protocol '{other}'"
        ))),
    }
}

fn parse_dex_kind(value: &str) -> PyResult<DexKind> {
    match value.to_ascii_lowercase().as_str() {
        "univ2" | "uniswapv2" | "uni_v2" => Ok(DexKind::UniV2),
        "univ3" | "uniswapv3" | "uni_v3" => Ok(DexKind::UniV3),
        "univ4" | "uniswapv4" | "uni_v4" => Ok(DexKind::UniV4),
        "curve" => Ok(DexKind::Curve),
        "reserved" => Ok(DexKind::Reserved),
        "aggregatorv6" | "aggregator_v6" => Ok(DexKind::AggregatorV6),
        "morpho" | "morphoblue" => Ok(DexKind::MorphoBlue),
        "algebra" => Ok(DexKind::Algebra),
        "solidly" => Ok(DexKind::Solidly),
        "curveng" | "curve_ng" => Ok(DexKind::CurveNG),
        "balancerv2" | "balancer_v2" => Ok(DexKind::BalancerV2),
        "maverickv2" | "maverick_v2" => Ok(DexKind::MaverickV2),
        "dodopmm" | "dodo_pmm" => Ok(DexKind::DodoPmm),
        "fluiddex" | "fluid_dex" => Ok(DexKind::FluidDex),
        "balancerv3" | "balancer_v3" => Ok(DexKind::BalancerV3),
        "kyberelastic" | "kyber_elastic" => Ok(DexKind::KyberElastic),
        "lfj" | "liquiditybook" | "lfjliquiditybook" | "lfj_liquidity_book" => {
            Ok(DexKind::LFJLiquidityBook)
        }
        "gmxv2" | "gmx_v2" => Ok(DexKind::GMXV2),
        "wombat" => Ok(DexKind::Wombat),
        "bebop" => Ok(DexKind::Bebop),
        "hashflow" => Ok(DexKind::Hashflow),
        "woofi" => Ok(DexKind::WooFi),
        "okxdex" | "okx" | "okx_dex" => Ok(DexKind::OKXDex),
        "enso" => Ok(DexKind::Enso),
        "squid" => Ok(DexKind::Squid),
        "lifi" | "li.fi" | "li_fi" => Ok(DexKind::LIFI),
        "rango" => Ok(DexKind::Rango),
        "rubic" => Ok(DexKind::Rubic),
        "native" => Ok(DexKind::Native),
        other => Err(PyValueError::new_err(format!("Unknown dex kind '{other}'"))),
    }
}

fn required_item<'py>(dict: &'py Bound<'py, PyDict>, key: &str) -> PyResult<Bound<'py, PyAny>> {
    dict.get_item(key)?
        .ok_or_else(|| PyValueError::new_err(format!("swap step missing '{key}'")))
}

fn parse_swap_step(step: &Bound<'_, PyAny>) -> PyResult<SwapStep> {
    let dict = step.cast::<PyDict>()?;

    let dex_kind = required_item(dict, "dex_kind")?
        .extract::<String>()
        .and_then(|s| parse_dex_kind(&s))?;
    let router = parse_address(&required_item(dict, "router")?)?;
    let call_data = parse_bytes(&required_item(dict, "call_data")?)?;
    let token_in = parse_address(&required_item(dict, "token_in")?)?;
    let token_out = parse_address(&required_item(dict, "token_out")?)?;
    let amount_in = extract_python_u256(&required_item(dict, "amount_in")?)?;
    let amount_out_min = extract_python_u256(&required_item(dict, "amount_out_min")?)?;

    Ok(SwapStep {
        dex_kind,
        router,
        call_data,
        token_in,
        token_out,
        amount_in,
        amount_out_min,
    })
}

fn parse_swap_steps(swaps: &Bound<'_, PyList>) -> PyResult<Vec<SwapStep>> {
    swaps.iter().map(|step| parse_swap_step(&step)).collect()
}

fn execution_error_to_py(err: &crate::errors::ExecutionError) -> PyErr {
    PyValueError::new_err(err.to_string())
}

/// Encode `Executor.executeNativeArb` calldata from Python values.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(name = "encode_native_arb_calldata")]
#[pyo3(signature = (
    flash_lender,
    flash_protocol,
    flash_token,
    flash_amount,
    swaps,
    min_profit,
    deadline
))]
pub fn encode_native_arb_calldata_py<'py>(
    py: Python<'py>,
    flash_lender: &Bound<'_, PyAny>,
    flash_protocol: &str,
    flash_token: &Bound<'_, PyAny>,
    flash_amount: &Bound<'_, PyAny>,
    swaps: &Bound<'_, PyList>,
    min_profit: &Bound<'_, PyAny>,
    deadline: &Bound<'_, PyAny>,
) -> PyResult<Bound<'py, PyBytes>> {
    let params = NativeArbParams {
        flash_lender: parse_address(flash_lender)?,
        flash_protocol: parse_flash_protocol(flash_protocol)?,
        flash_token: parse_address(flash_token)?,
        flash_amount: extract_python_u256(flash_amount)?,
        swaps: parse_swap_steps(swaps)?,
        min_profit: extract_python_u256(min_profit)?,
        deadline: extract_python_u256(deadline)?,
    };

    let calldata = py
        .detach(|| encode_native_arb_calldata(&params))
        .map_err(|err| execution_error_to_py(&err))?;
    Ok(PyBytes::new(py, calldata.as_ref()))
}

/// Encode `Executor.matchInternal` calldata from Python values.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(name = "encode_match_internal_calldata")]
#[pyo3(signature = (
    cow_settlement_calldata,
    uniswapx_batch_calldata,
    expected_token_inflows,
    expected_token_inflow_min,
    flash_lender,
    flash_protocol,
    flash_token,
    flash_amount,
    min_profit,
    deadline
))]
pub fn encode_match_internal_calldata_py<'py>(
    py: Python<'py>,
    cow_settlement_calldata: &Bound<'_, PyAny>,
    uniswapx_batch_calldata: &Bound<'_, PyAny>,
    expected_token_inflows: &Bound<'_, PyList>,
    expected_token_inflow_min: &Bound<'_, PyList>,
    flash_lender: &Bound<'_, PyAny>,
    flash_protocol: &str,
    flash_token: &Bound<'_, PyAny>,
    flash_amount: &Bound<'_, PyAny>,
    min_profit: &Bound<'_, PyAny>,
    deadline: &Bound<'_, PyAny>,
) -> PyResult<Bound<'py, PyBytes>> {
    let token_inflows: Vec<Address> = expected_token_inflows
        .iter()
        .map(|token| parse_address(&token))
        .collect::<PyResult<_>>()?;
    let token_inflow_min = expected_token_inflow_min
        .iter()
        .map(|amount| extract_python_u256(&amount))
        .collect::<PyResult<Vec<_>>>()?;

    let params = MatchParams {
        cow_settlement_calldata: parse_bytes(cow_settlement_calldata)?,
        uniswapx_batch_calldata: parse_bytes(uniswapx_batch_calldata)?,
        expected_token_inflows: token_inflows,
        expected_token_inflow_min: token_inflow_min,
        flash_lender: parse_address(flash_lender)?,
        flash_protocol: parse_flash_protocol(flash_protocol)?,
        flash_token: parse_address(flash_token)?,
        flash_amount: extract_python_u256(flash_amount)?,
        min_profit: extract_python_u256(min_profit)?,
        deadline: extract_python_u256(deadline)?,
    };

    let calldata = py
        .detach(|| encode_match_internal_calldata(&params))
        .map_err(|err| execution_error_to_py(&err))?;
    Ok(PyBytes::new(py, calldata.as_ref()))
}

/// Encode `Executor.composeFourLeg` calldata from Python values.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(name = "encode_compose_four_leg_calldata")]
#[pyo3(signature = (
    across_fill_calldata,
    arb_swaps,
    cow_fill_calldata,
    uniswapx_rebalance_calldata,
    flash_lender,
    flash_protocol,
    flash_token,
    flash_amount,
    min_profit,
    deadline
))]
pub fn encode_compose_four_leg_calldata_py<'py>(
    py: Python<'py>,
    across_fill_calldata: &Bound<'_, PyAny>,
    arb_swaps: &Bound<'_, PyList>,
    cow_fill_calldata: &Bound<'_, PyAny>,
    uniswapx_rebalance_calldata: &Bound<'_, PyAny>,
    flash_lender: &Bound<'_, PyAny>,
    flash_protocol: &str,
    flash_token: &Bound<'_, PyAny>,
    flash_amount: &Bound<'_, PyAny>,
    min_profit: &Bound<'_, PyAny>,
    deadline: &Bound<'_, PyAny>,
) -> PyResult<Bound<'py, PyBytes>> {
    let params = ComposeParams {
        across_fill_calldata: parse_bytes(across_fill_calldata)?,
        arb_swaps: parse_swap_steps(arb_swaps)?,
        cow_fill_calldata: parse_bytes(cow_fill_calldata)?,
        uniswapx_rebalance_calldata: parse_bytes(uniswapx_rebalance_calldata)?,
        flash_lender: parse_address(flash_lender)?,
        flash_protocol: parse_flash_protocol(flash_protocol)?,
        flash_token: parse_address(flash_token)?,
        flash_amount: extract_python_u256(flash_amount)?,
        min_profit: extract_python_u256(min_profit)?,
        deadline: extract_python_u256(deadline)?,
    };

    let calldata = py
        .detach(|| encode_compose_four_leg_calldata(&params))
        .map_err(|err| execution_error_to_py(&err))?;
    Ok(PyBytes::new(py, calldata.as_ref()))
}

use crate::simulation::curve::CurveSnapshot;
use crate::simulation::curve_optimize::optimal_input_2pool_curve;
use crate::simulation::uniswap_v3_math::v3_mid_price_x96;
use crate::simulation::v2_optimize::{
    apply_gap_to_price_x96, optimal_input_2pool, optimal_v2_frontrun_amount,
    synthetic_victim_amount_in, v2_mid_price_x96, v2_optimal_sandwich_size, v2_sandwich_max_size,
};

/// Calculate the mid-price in Q64.96 for a V2 pool.
#[pyfunction]
#[pyo3(name = "v2_mid_price_x96")]
pub fn v2_mid_price_x96_py(
    reserve_in: &Bound<'_, PyAny>,
    reserve_out: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let result = v2_mid_price_x96(
        extract_python_u256(reserve_in)?,
        extract_python_u256(reserve_out)?,
    );
    Ok(result.to_string())
}

/// Calculate the mid-price in Q64.96 for a V3 pool.
#[pyfunction]
#[pyo3(name = "v3_mid_price_x96")]
pub fn v3_mid_price_x96_py(sqrt_price_x96: &Bound<'_, PyAny>) -> PyResult<String> {
    let result = v3_mid_price_x96(extract_python_u256(sqrt_price_x96)?);
    Ok(result.to_string())
}

/// Apply the gap to a price.
#[pyfunction]
#[pyo3(name = "apply_gap_to_price_x96")]
pub fn apply_gap_to_price_x96_py(price_x96: &Bound<'_, PyAny>, gap_bps: i32) -> PyResult<String> {
    let result = apply_gap_to_price_x96(extract_python_u256(price_x96)?, gap_bps);
    Ok(result.to_string())
}

/// Synthetic victim swap size.
#[pyfunction]
#[pyo3(name = "synthetic_victim_amount_in")]
pub fn synthetic_victim_amount_in_py(
    gap_bps: i32,
    reserve_in: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let result = synthetic_victim_amount_in(gap_bps, extract_python_u256(reserve_in)?);
    Ok(result.to_string())
}

/// Calculate the optimal frontrun amount for a sandwich attack.
#[pyfunction]
#[pyo3(name = "optimal_v2_frontrun_amount")]
pub fn optimal_v2_frontrun_amount_py(
    victim_amount_in: &Bound<'_, PyAny>,
    victim_min_out: &Bound<'_, PyAny>,
    reserve_in: &Bound<'_, PyAny>,
    reserve_out: &Bound<'_, PyAny>,
    fee_bps: u32,
    margin_bps: u32,
) -> PyResult<String> {
    let result = optimal_v2_frontrun_amount(
        extract_python_u256(victim_amount_in)?,
        extract_python_u256(victim_min_out)?,
        extract_python_u256(reserve_in)?,
        extract_python_u256(reserve_out)?,
        fee_bps,
        margin_bps,
    )
    .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(result.to_string())
}

/// Largest frontrun size `a` such that the victim's post-distortion
/// fill is exactly `victim_min_out`.
#[pyfunction]
#[pyo3(name = "v2_sandwich_max_size")]
pub fn v2_sandwich_max_size_py(
    victim_amount_in: &Bound<'_, PyAny>,
    victim_min_out: &Bound<'_, PyAny>,
    reserve_in: &Bound<'_, PyAny>,
    reserve_out: &Bound<'_, PyAny>,
    fee_bps: u32,
) -> PyResult<String> {
    let result = v2_sandwich_max_size(
        extract_python_u256(victim_amount_in)?,
        extract_python_u256(victim_min_out)?,
        extract_python_u256(reserve_in)?,
        extract_python_u256(reserve_out)?,
        fee_bps,
    )
    .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(result.to_string())
}

/// Find the unconstrained optimal frontrun size using golden-section search.
#[pyfunction]
#[pyo3(name = "v2_optimal_sandwich_size")]
pub fn v2_optimal_sandwich_size_py(
    victim_amount_in: &Bound<'_, PyAny>,
    reserve_in: &Bound<'_, PyAny>,
    reserve_out: &Bound<'_, PyAny>,
    fee_bps: u32,
    a_max: &Bound<'_, PyAny>,
) -> PyResult<String> {
    let result = v2_optimal_sandwich_size(
        extract_python_u256(victim_amount_in)?,
        extract_python_u256(reserve_in)?,
        extract_python_u256(reserve_out)?,
        fee_bps,
        extract_python_u256(a_max)?,
    )
    .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(result.to_string())
}
use crate::simulation::v3::V3Snapshot;
use crate::simulation::v3_optimize::optimal_input_2pool_v3;
use alloy::primitives::U256;

/// Calculate the optimal input amount for a 2-pool Uniswap V2 arbitrage cycle.
#[pyfunction]
#[pyo3(name = "optimal_input_2pool")]
pub fn optimal_input_2pool_py(
    r_a1: &Bound<'_, PyAny>,
    r_b1: &Bound<'_, PyAny>,
    fee_bps1: u32,
    r_b2: &Bound<'_, PyAny>,
    r_a2: &Bound<'_, PyAny>,
    fee_bps2: u32,
) -> PyResult<String> {
    let result = optimal_input_2pool(
        extract_python_u256(r_a1)?,
        extract_python_u256(r_b1)?,
        fee_bps1,
        extract_python_u256(r_b2)?,
        extract_python_u256(r_a2)?,
        fee_bps2,
    )
    .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(result.to_string())
}

/// Calculate the optimal input amount for a 2-pool V3 arbitrage cycle.
#[pyfunction]
#[pyo3(name = "optimal_input_2pool_v3")]
pub fn optimal_input_2pool_v3_py(
    pool1_v3_json: String,
    pool1_zero_for_one: bool,
    pool2_v3_json: Option<String>,
    pool2_v2_data: Option<(String, String, u32)>,
) -> PyResult<String> {
    let p1: V3Snapshot = serde_json::from_str(&pool1_v3_json)
        .map_err(|e| PyValueError::new_err(format!("invalid p1 json: {e}")))?;

    let p2v3: Option<V3Snapshot> = if let Some(json) = pool2_v3_json {
        Some(
            serde_json::from_str(&json)
                .map_err(|e| PyValueError::new_err(format!("invalid p2 json: {e}")))?,
        )
    } else {
        None
    };

    let p2v2: Option<(U256, U256, u32)> = if let Some(data) = pool2_v2_data {
        Some((
            U256::from_str_radix(&data.0, 10).map_err(|e| PyValueError::new_err(e.to_string()))?,
            U256::from_str_radix(&data.1, 10).map_err(|e| PyValueError::new_err(e.to_string()))?,
            data.2,
        ))
    } else {
        None
    };

    let result = optimal_input_2pool_v3(&p1, pool1_zero_for_one, p2v3.as_ref(), p2v2)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    Ok(result.to_string())
}

/// Calculate the optimal input amount for a 2-pool Curve arbitrage cycle.
#[pyfunction]
#[pyo3(name = "optimal_input_2pool_curve")]
pub fn optimal_input_2pool_curve_py(
    pool_curve_json: String,
    i: usize,
    j: usize,
    pool2_v2_data: Option<(String, String, u32)>,
) -> PyResult<String> {
    let p_curve: CurveSnapshot = serde_json::from_str(&pool_curve_json)
        .map_err(|e| PyValueError::new_err(format!("invalid curve json: {e}")))?;

    let p2v2: Option<(U256, U256, u32)> = if let Some(data) = pool2_v2_data {
        Some((
            U256::from_str_radix(&data.0, 10).map_err(|e| PyValueError::new_err(e.to_string()))?,
            U256::from_str_radix(&data.1, 10).map_err(|e| PyValueError::new_err(e.to_string()))?,
            data.2,
        ))
    } else {
        None
    };

    let result = optimal_input_2pool_curve(&p_curve, i, j, p2v2)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    Ok(result.to_string())
}

/// Add executor module to Python module.
pub fn add_execution_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(encode_native_arb_calldata_py, m)?)?;
    m.add_function(wrap_pyfunction!(encode_match_internal_calldata_py, m)?)?;
    m.add_function(wrap_pyfunction!(encode_compose_four_leg_calldata_py, m)?)?;
    m.add_function(wrap_pyfunction!(optimal_input_2pool_py, m)?)?;
    m.add_function(wrap_pyfunction!(optimal_input_2pool_v3_py, m)?)?;
    m.add_function(wrap_pyfunction!(optimal_input_2pool_curve_py, m)?)?;
    m.add_function(wrap_pyfunction!(optimal_v2_frontrun_amount_py, m)?)?;
    m.add_function(wrap_pyfunction!(v2_mid_price_x96_py, m)?)?;
    m.add_function(wrap_pyfunction!(v3_mid_price_x96_py, m)?)?;
    m.add_function(wrap_pyfunction!(apply_gap_to_price_x96_py, m)?)?;
    m.add_function(wrap_pyfunction!(synthetic_victim_amount_in_py, m)?)?;
    m.add_function(wrap_pyfunction!(v2_sandwich_max_size_py, m)?)?;
    m.add_function(wrap_pyfunction!(v2_optimal_sandwich_size_py, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used, clippy::expect_used)]

    use super::*;
    use crate::execution::{
        encode_native_arb_calldata, DexKind, FlashProtocol, NativeArbParams, SwapStep,
    };
    use alloy::primitives::{Address, Bytes, U256};
    use pyo3::types::{PyBytes, PyDict, PyInt, PyList, PyString};

    fn with_python<R>(f: impl for<'py> FnOnce(Python<'py>) -> R) -> R {
        crate::with_python_for_tests(f)
    }

    fn sample_swap_step() -> SwapStep {
        SwapStep {
            dex_kind: DexKind::UniV3,
            router: Address::repeat_byte(0x11),
            call_data: Bytes::from(vec![0xaa, 0xbb, 0xcc]),
            token_in: Address::repeat_byte(0x22),
            token_out: Address::repeat_byte(0x33),
            amount_in: U256::from(456u64),
            amount_out_min: U256::from(789u64),
        }
    }

    fn sample_native_arb_params() -> NativeArbParams {
        NativeArbParams {
            flash_lender: Address::repeat_byte(0x44),
            flash_protocol: FlashProtocol::Aave,
            flash_token: Address::repeat_byte(0x55),
            flash_amount: U256::from(1234u64),
            swaps: vec![sample_swap_step()],
            min_profit: U256::from(42u64),
            deadline: U256::from(999_999u64),
        }
    }

    #[test]
    fn native_arb_py_binding_matches_core() {
        with_python(|py| {
            let params = sample_native_arb_params();

            let swaps = PyList::empty(py);
            let swap = PyDict::new(py);
            swap.set_item("dex_kind", "univ3").unwrap();
            swap.set_item("router", format!("{:#x}", params.swaps[0].router))
                .unwrap();
            swap.set_item("call_data", PyBytes::new(py, &[0xaa, 0xbb, 0xcc]))
                .unwrap();
            swap.set_item("token_in", format!("{:#x}", params.swaps[0].token_in))
                .unwrap();
            swap.set_item("token_out", format!("{:#x}", params.swaps[0].token_out))
                .unwrap();
            swap.set_item("amount_in", 456u64).unwrap();
            swap.set_item("amount_out_min", 789u64).unwrap();
            swaps.append(swap).unwrap();

            let flash_lender = PyString::new(py, &format!("{:#x}", params.flash_lender)).into_any();
            let flash_token = PyString::new(py, &format!("{:#x}", params.flash_token)).into_any();
            let flash_amount = PyInt::new(py, 1234).into_any();
            let min_profit = PyInt::new(py, 42).into_any();
            let deadline = PyInt::new(py, 999_999).into_any();

            let calldata = encode_native_arb_calldata_py(
                py,
                &flash_lender,
                "aave",
                &flash_token,
                &flash_amount,
                &swaps,
                &min_profit,
                &deadline,
            )
            .unwrap();

            let expected = encode_native_arb_calldata(&params).unwrap();
            let actual: &[u8] = calldata.extract().unwrap();
            assert_eq!(actual, expected.as_ref());
        });
    }

    #[test]
    fn match_internal_py_binding_matches_core() {
        with_python(|py| {
            let params = MatchParams {
                cow_settlement_calldata: Bytes::from_static(b"cow"),
                uniswapx_batch_calldata: Bytes::from_static(b"uni"),
                expected_token_inflows: vec![Address::repeat_byte(0xaa)],
                expected_token_inflow_min: vec![U256::from(1u64)],
                flash_lender: Address::repeat_byte(0x44),
                flash_protocol: FlashProtocol::Morpho,
                flash_token: Address::repeat_byte(0x55),
                flash_amount: U256::from(1234u64),
                min_profit: U256::from(42u64),
                deadline: U256::from(999_999u64),
            };

            let expected_token_inflows = PyList::empty(py);
            expected_token_inflows
                .append(PyString::new(
                    py,
                    &format!("{:#x}", params.expected_token_inflows[0]),
                ))
                .unwrap();

            let expected_token_inflow_min = PyList::empty(py);
            expected_token_inflow_min.append(PyInt::new(py, 1)).unwrap();

            let cow_settlement_calldata = PyBytes::new(py, b"cow").into_any();
            let uniswapx_batch_calldata = PyBytes::new(py, b"uni").into_any();
            let flash_lender = PyString::new(py, &format!("{:#x}", params.flash_lender)).into_any();
            let flash_token = PyString::new(py, &format!("{:#x}", params.flash_token)).into_any();
            let flash_amount = PyInt::new(py, 1234).into_any();
            let min_profit = PyInt::new(py, 42).into_any();
            let deadline = PyInt::new(py, 999_999).into_any();

            let calldata = encode_match_internal_calldata_py(
                py,
                &cow_settlement_calldata,
                &uniswapx_batch_calldata,
                &expected_token_inflows,
                &expected_token_inflow_min,
                &flash_lender,
                "morpho",
                &flash_token,
                &flash_amount,
                &min_profit,
                &deadline,
            )
            .unwrap();

            let expected = encode_match_internal_calldata(&params).unwrap();
            let actual: &[u8] = calldata.extract().unwrap();
            assert_eq!(actual, expected.as_ref());
        });
    }

    #[test]
    fn compose_four_leg_py_binding_matches_core() {
        with_python(|py| {
            let params = ComposeParams {
                across_fill_calldata: Bytes::from_static(b"across"),
                arb_swaps: vec![sample_swap_step()],
                cow_fill_calldata: Bytes::from_static(b"cow"),
                uniswapx_rebalance_calldata: Bytes::from_static(b"uni"),
                flash_lender: Address::repeat_byte(0x44),
                flash_protocol: FlashProtocol::ERC3156,
                flash_token: Address::repeat_byte(0x55),
                flash_amount: U256::from(1234u64),
                min_profit: U256::from(42u64),
                deadline: U256::from(999_999u64),
            };

            let arb_swaps = PyList::empty(py);
            let swap = PyDict::new(py);
            swap.set_item("dex_kind", "univ3").unwrap();
            swap.set_item("router", format!("{:#x}", params.arb_swaps[0].router))
                .unwrap();
            swap.set_item("call_data", PyBytes::new(py, &[0xaa, 0xbb, 0xcc]))
                .unwrap();
            swap.set_item("token_in", format!("{:#x}", params.arb_swaps[0].token_in))
                .unwrap();
            swap.set_item("token_out", format!("{:#x}", params.arb_swaps[0].token_out))
                .unwrap();
            swap.set_item("amount_in", 456u64).unwrap();
            swap.set_item("amount_out_min", 789u64).unwrap();
            arb_swaps.append(swap).unwrap();

            let across_fill_calldata = PyBytes::new(py, b"across").into_any();
            let cow_fill_calldata = PyBytes::new(py, b"cow").into_any();
            let uniswapx_rebalance_calldata = PyBytes::new(py, b"uni").into_any();
            let flash_lender = PyString::new(py, &format!("{:#x}", params.flash_lender)).into_any();
            let flash_token = PyString::new(py, &format!("{:#x}", params.flash_token)).into_any();
            let flash_amount = PyInt::new(py, 1234).into_any();
            let min_profit = PyInt::new(py, 42).into_any();
            let deadline = PyInt::new(py, 999_999).into_any();

            let calldata = encode_compose_four_leg_calldata_py(
                py,
                &across_fill_calldata,
                &arb_swaps,
                &cow_fill_calldata,
                &uniswapx_rebalance_calldata,
                &flash_lender,
                "erc3156",
                &flash_token,
                &flash_amount,
                &min_profit,
                &deadline,
            )
            .unwrap();

            let expected = encode_compose_four_leg_calldata(&params).unwrap();
            let actual: &[u8] = calldata.extract().unwrap();
            assert_eq!(actual, expected.as_ref());
        });
    }
}
