//! `PyO3` bindings for deterministic execution-engine job composition.

use crate::execution_engine::compose_engine_job_json;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Compose and validate a Rust execution-engine job from JSON payloads.
#[pyfunction]
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
    Ok(())
}
