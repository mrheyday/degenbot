//! Adaptive request timeout.
//!
//! Ported from `ava-labs/avalanchego` `utils/timer/adaptive_timeout_manager.go`
//! (BSD-licensed) — the timeout-adaptation core only. avalanchego's full
//! manager also owns a registry of outstanding requests, a deadline heap,
//! and a background firing loop; that machinery is networking-specific and
//! omitted. What remains is the useful part: an EWMA of observed latency
//! that yields a request timeout `clamp(coefficient * avg_latency, min, max)`.
//!
//! Usage: time an RPC call, `observe_latency` the elapsed time, and bound
//! the next call with `current_timeout`.

use std::time::{Duration, Instant};

use eyre::{eyre, Result};

use crate::utils::averager::Averager;

/// Tracks observed request latency and derives an adaptive timeout.
#[derive(Debug, Clone)]
pub struct AdaptiveTimeout {
    latency: Averager,
    minimum: Duration,
    maximum: Duration,
    /// Timeout multiplier over average latency; must be `>= 1`.
    coefficient: f64,
    current: Duration,
}

impl AdaptiveTimeout {
    /// Construct an adaptive timeout.
    ///
    /// - `initial` seeds both the current timeout and the latency average;
    ///   it must lie within `[minimum, maximum]`.
    /// - `halflife` controls how fast old latency samples decay.
    /// - `coefficient` (`>= 1`) scales average latency into the timeout.
    pub fn new(
        initial: Duration,
        minimum: Duration,
        maximum: Duration,
        halflife: Duration,
        coefficient: f64,
        now: Instant,
    ) -> Result<Self> {
        if coefficient < 1.0 {
            return Err(eyre!("adaptive_timeout: coefficient must be >= 1"));
        }
        if minimum > maximum {
            return Err(eyre!("adaptive_timeout: minimum exceeds maximum"));
        }
        if initial < minimum {
            return Err(eyre!("adaptive_timeout: initial timeout below minimum"));
        }
        if initial > maximum {
            return Err(eyre!("adaptive_timeout: initial timeout above maximum"));
        }
        let latency = Averager::new(initial.as_nanos() as f64, halflife, now)?;
        Ok(Self {
            latency,
            minimum,
            maximum,
            coefficient,
            current: initial,
        })
    }

    /// The timeout to apply to the next request.
    pub fn current_timeout(&self) -> Duration {
        self.current
    }

    /// Register an observed request latency and recompute the timeout.
    pub fn observe_latency(&mut self, latency: Duration, now: Instant) {
        self.latency.observe(latency.as_nanos() as f64, now);
        let scaled = self.coefficient * self.latency.read();
        // `scaled` is f64 nanoseconds; the clamp bounds any saturation.
        let candidate = Duration::from_nanos(scaled.max(0.0) as u64);
        self.current = candidate.clamp(self.minimum, self.maximum);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn timeout() -> AdaptiveTimeout {
        AdaptiveTimeout::new(
            Duration::from_secs(1),
            Duration::from_millis(100),
            Duration::from_secs(10),
            Duration::from_secs(1),
            2.0,
            Instant::now(),
        )
        .unwrap()
    }

    #[test]
    fn rejects_invalid_config() {
        let now = Instant::now();
        // coefficient < 1
        assert!(AdaptiveTimeout::new(
            Duration::from_secs(1),
            Duration::from_millis(100),
            Duration::from_secs(10),
            Duration::from_secs(1),
            0.5,
            now,
        )
        .is_err());
        // initial above maximum
        assert!(AdaptiveTimeout::new(
            Duration::from_secs(20),
            Duration::from_millis(100),
            Duration::from_secs(10),
            Duration::from_secs(1),
            2.0,
            now,
        )
        .is_err());
    }

    #[test]
    fn starts_at_the_initial_timeout() {
        assert_eq!(timeout().current_timeout(), Duration::from_secs(1));
    }

    #[test]
    fn slow_responses_grow_the_timeout() {
        let mut t = timeout();
        let start = Instant::now();
        let mut clock = start;
        for _ in 0..20 {
            clock += Duration::from_secs(1);
            t.observe_latency(Duration::from_secs(3), clock);
        }
        // avg latency -> 3s, timeout -> 2 * 3s = 6s, within [0.1s, 10s].
        let current = t.current_timeout();
        assert!(
            current > Duration::from_secs(5) && current < Duration::from_secs(7),
            "current={current:?}"
        );
    }

    #[test]
    fn timeout_is_clamped_to_the_maximum() {
        let mut t = timeout();
        let start = Instant::now();
        let mut clock = start;
        for _ in 0..20 {
            clock += Duration::from_secs(1);
            // 2 * 30s = 60s, far above the 10s maximum.
            t.observe_latency(Duration::from_secs(30), clock);
        }
        assert_eq!(t.current_timeout(), Duration::from_secs(10));
    }

    #[test]
    fn timeout_is_clamped_to_the_minimum() {
        let mut t = timeout();
        let start = Instant::now();
        let mut clock = start;
        for _ in 0..20 {
            clock += Duration::from_secs(1);
            // 2 * 1ms = 2ms, below the 100ms minimum.
            t.observe_latency(Duration::from_millis(1), clock);
        }
        assert_eq!(t.current_timeout(), Duration::from_millis(100));
    }
}
