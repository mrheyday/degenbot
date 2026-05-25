//! Submission-lane dispatcher (ADR-005, ADR-017).
//!
//! Maps `Plan.submission_lane` to the configured RPC endpoint URL. The
//! Default lane is the engine's primary Arbitrum RPC; PrivateRelay is a
//! protected relay/RPC endpoint selected by degenbot admission; Kairos is the
//! resold-priority secondary market; Timeboost is the express-lane auction
//! winner endpoint.

use crate::monitor::Lane;

/// Per-lane RPC endpoints. All optional except `default_http`; lane requests
/// for an unconfigured lane fall back to the default with a warning.
#[derive(Debug, Clone, Default)]
pub struct LaneEndpoints {
    pub default_http: String,
    pub private_relay_http: Option<String>,
    pub kairos_http: Option<String>,
    pub timeboost_http: Option<String>,
}

impl LaneEndpoints {
    /// Resolve a lane to its configured URL; falls back to default_http if
    /// the requested lane has no override.
    pub fn endpoint_for(&self, lane: &Lane) -> &str {
        match lane {
            Lane::Default => &self.default_http,
            Lane::PrivateRelay => self
                .private_relay_http
                .as_deref()
                .unwrap_or(&self.default_http),
            Lane::Kairos => self.kairos_http.as_deref().unwrap_or(&self.default_http),
            Lane::Timeboost => self.timeboost_http.as_deref().unwrap_or(&self.default_http),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lane_dispatch_uses_specific_endpoint_when_set() {
        let eps = LaneEndpoints {
            default_http: "https://default".into(),
            private_relay_http: Some("https://private".into()),
            kairos_http: Some("https://kairos".into()),
            timeboost_http: Some("https://timeboost".into()),
        };
        assert_eq!(eps.endpoint_for(&Lane::Default), "https://default");
        assert_eq!(eps.endpoint_for(&Lane::PrivateRelay), "https://private");
        assert_eq!(eps.endpoint_for(&Lane::Kairos), "https://kairos");
        assert_eq!(eps.endpoint_for(&Lane::Timeboost), "https://timeboost");
    }

    #[test]
    fn lane_dispatch_falls_back_to_default_when_unset() {
        let eps = LaneEndpoints {
            default_http: "https://default".into(),
            ..Default::default()
        };
        assert_eq!(eps.endpoint_for(&Lane::PrivateRelay), "https://default");
        assert_eq!(eps.endpoint_for(&Lane::Kairos), "https://default");
        assert_eq!(eps.endpoint_for(&Lane::Timeboost), "https://default");
    }
}
