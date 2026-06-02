//! Pending-nonce manager.
//!
//! Caches the next-to-use nonce for the executor's signer address so we
//! don't round-trip to RPC on every Plan. Reconciles against the on-chain
//! `eth_getTransactionCount(addr, "pending")` after a configured TTL or on
//! any nonce-related submit failure.

use parking_lot::Mutex;
use std::sync::Arc;

#[derive(Debug, Default)]
struct State {
    pending: Option<u64>,
    last_refresh_unix_ms: u64,
}

/// Pending-nonce cache. Shareable across the actor and lane dispatchers.
#[derive(Clone, Default)]
pub struct PendingNonceCache {
    state: Arc<Mutex<State>>,
}

#[allow(dead_code)]
impl PendingNonceCache {
    pub fn new() -> Self {
        Self::default()
    }

    /// Take the current pending nonce and atomically increment. Returns
    /// `None` if the cache has never been primed — caller should fetch from
    /// RPC and `prime`.
    pub fn take_and_increment(&self) -> Option<u64> {
        let mut s = self.state.lock();
        let n = s.pending?;
        s.pending = Some(n + 1);
        Some(n)
    }

    /// Take the cached nonce only if the cache was refreshed within `ttl_ms`.
    /// Stale state is cleared so callers must reconcile against RPC before
    /// submitting.
    pub fn take_and_increment_if_fresh(&self, now_unix_ms: u64, ttl_ms: u64) -> Option<u64> {
        let mut s = self.state.lock();
        let n = s.pending?;
        if now_unix_ms.saturating_sub(s.last_refresh_unix_ms) > ttl_ms {
            s.pending = None;
            return None;
        }
        s.pending = Some(n + 1);
        Some(n)
    }

    /// Reset the cache to a fresh value (e.g., after a stale-nonce error or
    /// scheduled TTL refresh). Caller is responsible for fetching from RPC.
    pub fn prime(&self, pending: u64, refresh_unix_ms: u64) {
        let mut s = self.state.lock();
        s.pending = Some(pending);
        s.last_refresh_unix_ms = refresh_unix_ms;
    }

    /// Drop the cached nonce after an RPC rejection or explicit
    /// reconciliation signal. The next caller must fetch fresh pending
    /// nonce state from RPC before submitting.
    pub fn clear(&self) {
        let mut s = self.state.lock();
        s.pending = None;
        s.last_refresh_unix_ms = 0;
    }

    /// Inspect the current cache state without mutating.
    pub fn peek(&self) -> Option<u64> {
        self.state.lock().pending
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_cache_returns_none() {
        let c = PendingNonceCache::new();
        assert_eq!(c.take_and_increment(), None);
    }

    #[test]
    fn prime_then_take_advances_monotonically() {
        let c = PendingNonceCache::new();
        c.prime(42, 0);
        assert_eq!(c.take_and_increment(), Some(42));
        assert_eq!(c.take_and_increment(), Some(43));
        assert_eq!(c.take_and_increment(), Some(44));
        assert_eq!(c.peek(), Some(45));
    }

    #[test]
    fn re_prime_overrides_existing() {
        let c = PendingNonceCache::new();
        c.prime(10, 0);
        c.take_and_increment();
        c.prime(100, 1);
        assert_eq!(c.take_and_increment(), Some(100));
    }

    #[test]
    fn clear_forces_next_caller_to_refresh_from_rpc() {
        let c = PendingNonceCache::new();
        c.prime(7, 0);
        assert_eq!(c.peek(), Some(7));

        c.clear();

        assert_eq!(c.peek(), None);
        assert_eq!(c.take_and_increment(), None);
    }

    #[test]
    fn stale_take_clears_cache_and_forces_refresh() {
        let c = PendingNonceCache::new();
        c.prime(42, 1_000);

        assert_eq!(c.take_and_increment_if_fresh(1_200, 500), Some(42));

        c.prime(100, 1_000);
        assert_eq!(c.take_and_increment_if_fresh(1_501, 500), None);
        assert_eq!(c.peek(), None);
    }
}
