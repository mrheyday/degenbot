//! Minimal metrics facade for the optional Rust/Alloy adapter scaffold.
//!
//! The production execution layer is degenbot. Keep this module dependency-free
//! until the adapter has a concrete Prometheus exporter contract.

use std::sync::atomic::{AtomicU64, Ordering};

static TASKS_CRASHED_TOTAL: AtomicU64 = AtomicU64::new(0);
static OPPORTUNITIES_EMITTED_TOTAL: AtomicU64 = AtomicU64::new(0);
static FRONTRUN_CANDIDATES_EMITTED_TOTAL: AtomicU64 = AtomicU64::new(0);

/// Increment the adapter task-crash counter.
pub fn inc_tasks_crashed() {
    TASKS_CRASHED_TOTAL.fetch_add(1, Ordering::Relaxed);
}

/// Increment the emitted-opportunity counter.
pub fn inc_opportunities_emitted() {
    OPPORTUNITIES_EMITTED_TOTAL.fetch_add(1, Ordering::Relaxed);
}

/// Increment the frontrun-candidate-emission counter. Bumped by the
/// `monitor::sequencer_feed` analyser for every selector / address match
/// that lands on the engine→coordinator broadcast bus. Paired with the
/// structured tracing log so the per-event detail isn't lost when no
/// Prometheus scraper is bound — see `monitor::sequencer_feed::run_analysis`.
pub fn inc_frontrun_candidates_emitted() {
    FRONTRUN_CANDIDATES_EMITTED_TOTAL.fetch_add(1, Ordering::Relaxed);
}

/// Snapshot counters for tests or an eventual exporter.
pub fn snapshot() -> MetricsSnapshot {
    MetricsSnapshot {
        tasks_crashed_total: TASKS_CRASHED_TOTAL.load(Ordering::Relaxed),
        opportunities_emitted_total: OPPORTUNITIES_EMITTED_TOTAL.load(Ordering::Relaxed),
        frontrun_candidates_emitted_total: FRONTRUN_CANDIDATES_EMITTED_TOTAL
            .load(Ordering::Relaxed),
    }
}

/// Dependency-free metric values.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MetricsSnapshot {
    pub tasks_crashed_total: u64,
    pub opportunities_emitted_total: u64,
    pub frontrun_candidates_emitted_total: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    // The counters are process-global atomics; this single test owns every
    // mutation so it asserts exact deltas rather than absolute values.
    #[test]
    fn counters_increment_and_snapshot_reflects_the_deltas() {
        let before = snapshot();

        inc_tasks_crashed();
        inc_opportunities_emitted();
        inc_frontrun_candidates_emitted();
        inc_frontrun_candidates_emitted();

        let after = snapshot();
        assert_eq!(after.tasks_crashed_total - before.tasks_crashed_total, 1);
        assert_eq!(
            after.opportunities_emitted_total - before.opportunities_emitted_total,
            1
        );
        assert_eq!(
            after.frontrun_candidates_emitted_total - before.frontrun_candidates_emitted_total,
            2
        );
    }

    #[test]
    fn snapshot_is_copy_eq_and_debug() {
        let snap = snapshot();
        let copied = snap;
        assert_eq!(copied, snap);
        assert!(format!("{snap:?}").contains("tasks_crashed_total"));
    }
}
