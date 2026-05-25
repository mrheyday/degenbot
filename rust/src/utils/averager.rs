//! Continuous-time exponentially-weighted moving average.
//!
//! Ported from `ava-labs/avalanchego` `utils/math/continuous_averager.go`
//! (BSD-licensed) — the algorithm, not the code. Each observation decays
//! the running average with a configurable half-life, so recent samples
//! dominate. Backs [`super::adaptive_timeout::AdaptiveTimeout`]; usable
//! standalone for latency / gas / profit-rate signals.
//!
//! Time is supplied explicitly as a monotonic [`Instant`] so the average
//! is deterministic under test.

use std::time::{Duration, Instant};

use eyre::{eyre, Result};

/// Tracks a continuous-time EWMA of observed `f64` values.
#[derive(Debug, Clone)]
pub struct Averager {
    /// Half-life in nanoseconds, pre-divided by `ln(2)` so the per-sample
    /// decay weight is `exp(-elapsed / halflife)`.
    halflife: f64,
    weighted_sum: f64,
    normalizer: f64,
    last_updated: Instant,
}

impl Averager {
    /// Create an averager seeded with `initial_prediction`, decaying with
    /// the given `halflife`. Errors if `halflife` is zero.
    pub fn new(initial_prediction: f64, halflife: Duration, now: Instant) -> Result<Self> {
        if halflife.is_zero() {
            return Err(eyre!("averager: halflife must be positive"));
        }
        Ok(Self {
            halflife: duration_nanos_f64(halflife) / std::f64::consts::LN_2,
            weighted_sum: initial_prediction,
            normalizer: 1.0,
            last_updated: now,
        })
    }

    /// Fold `value` (observed at `now`) into the average.
    pub fn observe(&mut self, value: f64, now: Instant) {
        if now > self.last_updated {
            let elapsed = duration_nanos_f64(now.duration_since(self.last_updated));
            let decay = (-elapsed / self.halflife).exp();
            self.weighted_sum = value + decay * self.weighted_sum;
            self.normalizer = 1.0 + decay * self.normalizer;
            self.last_updated = now;
        } else {
            // `Instant` is monotonic, so `now` can only equal `last_updated`
            // here — fold in without re-scaling.
            self.weighted_sum += value;
            self.normalizer += 1.0;
        }
    }

    /// The current decayed average.
    pub fn read(&self) -> f64 {
        self.weighted_sum / self.normalizer
    }
}

/// `Duration` as `f64` nanoseconds. `u128 -> f64` is lossy only above
/// ~2^53 ns (~104 days) — far beyond any timeout/latency this carries.
fn duration_nanos_f64(d: Duration) -> f64 {
    d.as_nanos() as f64
}

#[cfg(test)]
mod tests {
    use super::*;

    fn approx(a: f64, b: f64, tol: f64) -> bool {
        (a - b).abs() <= tol
    }

    #[test]
    fn rejects_zero_halflife() {
        assert!(Averager::new(0.0, Duration::ZERO, Instant::now()).is_err());
    }

    #[test]
    fn converges_toward_a_steady_observation() {
        let start = Instant::now();
        let mut avg = Averager::new(0.0, Duration::from_secs(1), start).unwrap();
        // Observe a constant 100 every half-life for many steps.
        let mut t = start;
        for _ in 0..40 {
            t += Duration::from_secs(1);
            avg.observe(100.0, t);
        }
        assert!(approx(avg.read(), 100.0, 1.0), "read={}", avg.read());
    }

    #[test]
    fn recent_samples_dominate_old_ones() {
        let start = Instant::now();
        let mut avg = Averager::new(0.0, Duration::from_secs(1), start).unwrap();
        let mut t = start;
        // A long run of low values, then one half-life of a high value.
        for _ in 0..20 {
            t += Duration::from_secs(1);
            avg.observe(10.0, t);
        }
        let before = avg.read();
        t += Duration::from_secs(1);
        avg.observe(1_000.0, t);
        // One fresh high sample pulls the average up sharply.
        assert!(
            avg.read() > before * 5.0,
            "before={before}, after={}",
            avg.read()
        );
    }

    #[test]
    fn same_instant_observations_average_unweighted() {
        let t = Instant::now();
        let mut avg = Averager::new(0.0, Duration::from_secs(1), t).unwrap();
        avg.observe(10.0, t);
        avg.observe(20.0, t);
        avg.observe(30.0, t);
        // (0 + 10 + 20 + 30) / (1 + 1 + 1 + 1)
        assert!(approx(avg.read(), 15.0, 1e-9), "read={}", avg.read());
    }
}
