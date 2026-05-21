//! `PyO3` bindings for deterministic signed-order admission.

use crate::signed_order_admission::evaluate_prediction_fx_match_json;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Evaluate a Prediction-FX style signed-order match from JSON.
#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
#[pyo3(name = "evaluate_prediction_fx_match_json")]
#[pyo3(signature = (input_json))]
pub fn evaluate_prediction_fx_match_json_py(
    py: Python<'_>,
    input_json: String,
) -> PyResult<String> {
    py.detach(|| evaluate_prediction_fx_match_json(&input_json))
        .map_err(|err| PyValueError::new_err(err.to_string()))
}

/// Add signed-order admission bindings to the Python module.
pub fn add_signed_order_admission_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(evaluate_prediction_fx_match_json_py, m)?)?;
    Ok(())
}
