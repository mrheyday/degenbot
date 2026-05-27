//! `PyO3` bindings for REVM-backed simulation.

use alloy::primitives::{Address, Bytes, U256};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyList};
use std::str::FromStr;

use crate::alloy_py::extract_python_u256;
use crate::simulation::revm_db::RevmDb;

#[pyclass(name = "RevmDb")]
pub struct PyRevmDb {
    inner: RevmDb,
}

#[pymethods]
impl PyRevmDb {
    #[new]
    #[pyo3(signature = (arb_rpc_http, seed_pools=None))]
    pub fn new(arb_rpc_http: String, seed_pools: Option<Bound<'_, PyList>>) -> PyResult<Self> {
        let pools: Vec<Address> = if let Some(p_list) = seed_pools {
            p_list
                .iter()
                .map(|item| {
                    let s = item.extract::<String>()?;
                    Address::from_str(&s).map_err(|e| PyValueError::new_err(e.to_string()))
                })
                .collect::<PyResult<_>>()?
        } else {
            Vec::new()
        };

        let runtime = crate::runtime::get_runtime();
        let inner = runtime
            .block_on(async { RevmDb::new(&arb_rpc_http, &pools).await })
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        Ok(Self { inner })
    }

    #[pyo3(signature = (from_addr, to_addr, calldata, value=None))]
    pub fn call<'py>(
        &self,
        from_addr: String,
        to_addr: String,
        calldata: Bound<'py, PyBytes>,
        value: Option<Bound<'py, PyAny>>,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let from =
            Address::from_str(&from_addr).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let to = Address::from_str(&to_addr).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let data = Bytes::from(calldata.as_bytes().to_vec());
        let val = if let Some(v) = value {
            extract_python_u256(&v)?
        } else {
            U256::ZERO
        };

        let result = self
            .inner
            .call_with_value(from, to, data, val)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        Ok(PyBytes::new(calldata.py(), result.as_ref()))
    }
}

pub fn add_simulation_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyRevmDb>()?;
    Ok(())
}
