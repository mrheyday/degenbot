//! `PyO3` bindings for deterministic execution-engine job composition.

use crate::decision::evaluate_sandoo_idea;
use crate::execution_engine::compose_engine_job_json;
use crate::matching::find_best_match;
use crate::monitor::{AggregatorQuote, MatchCandidate, Opportunity};
use alloy::primitives::U256;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Evaluate a Sandoo-style candidate idea from JSON.
#[pyfunction]
#[pyo3(name = "evaluate_sandoo_idea_json")]
pub fn evaluate_sandoo_idea_json_py(
    py: Python<'_>,
    opp_json: String,
    best_quote_json: Option<String>,
    max_gas_price_gwei: u64,
    flash_loan_fee_wei_str: String,
) -> PyResult<String> {
    let opp: Opportunity = serde_json::from_str(&opp_json)
        .map_err(|e| PyValueError::new_err(format!("invalid opp json: {e}")))?;
    
    let best_quote: Option<AggregatorQuote> = if let Some(json) = best_quote_json {
        Some(serde_json::from_str(&json)
            .map_err(|e| PyValueError::new_err(format!("invalid quote json: {e}")))?)
    } else {
        None
    };

    let flash_loan_fee_wei = U256::from_str_radix(&flash_loan_fee_wei_str, 10)
        .map_err(|e| PyValueError::new_err(format!("invalid flash fee: {e}")))?;

    let signal = py.detach(|| {
        evaluate_sandoo_idea(
            &opp,
            best_quote.as_ref(),
            max_gas_price_gwei,
            flash_loan_fee_wei,
        )
    });

    serde_json::to_string(&signal)
        .map_err(|e| PyValueError::new_err(format!("failed to serialize signal: {e}")))
}

/// Find the best match from a queue of candidates.
#[pyfunction]
#[pyo3(name = "find_best_match_json")]
pub fn find_best_match_json_py(
    py: Python<'_>,
    outbound_json: String,
    counters_json: String,
) -> PyResult<Option<String>> {
    let outbound: Vec<MatchCandidate> = serde_json::from_str(&outbound_json)
        .map_err(|e| PyValueError::new_err(format!("invalid outbound json: {e}")))?;
    
    let counters: Vec<MatchCandidate> = serde_json::from_str(&counters_json)
        .map_err(|e| PyValueError::new_err(format!("invalid counters json: {e}")))?;

    let best = py.detach(|| {
        find_best_match(&outbound, &counters)
    });

    if let Some(pair) = best {
        Ok(Some(serde_json::to_string(&pair)
            .map_err(|e| PyValueError::new_err(format!("failed to serialize pair: {e}")))?))
    } else {
        Ok(None)
    }
}

/// Compose and validate a Rust execution-engine job from JSON payloads.
#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
#[pyo3(name = "compose_engine_job_json")]
#[pyo3(signature = (
    plan_json,
    policy_json,
    sources_json,
    gates_json,
    simulation_json,
    now_ms
))]
pub fn compose_engine_job_json_py(
    py: Python<'_>,
    plan_json: String,
    policy_json: String,
    sources_json: String,
    gates_json: String,
    simulation_json: String,
    now_ms: u64,
) -> PyResult<String> {
    py.detach(|| {
        compose_engine_job_json(
            &plan_json,
            &policy_json,
            &sources_json,
            &gates_json,
            &simulation_json,
            now_ms,
        )
    })
    .map_err(|err| PyValueError::new_err(err.to_string()))
}

/// Add execution-engine composition bindings to the Python module.
pub fn add_execution_engine_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compose_engine_job_json_py, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_sandoo_idea_json_py, m)?)?;
    m.add_function(wrap_pyfunction!(find_best_match_json_py, m)?)?;
    Ok(())
}
