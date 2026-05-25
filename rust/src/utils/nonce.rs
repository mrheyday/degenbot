//! Atomic nonce manager.
//!
//! The submitter lives in the coordinator (TS) per ADR-009; the engine
//! does not actually broadcast transactions. This module exists for the
//! `--simulate` harness path and for any future engine-side relay pilot
//! (e.g., Pick B fast path with co-located Timeboost bid logic).
//!
//! Reconciles against `eth_getTransactionCount(latest)` on startup; drifts
//! are detected and re-anchored before the next broadcast.

use std::sync::atomic::{AtomicU64, Ordering};

use alloy::primitives::Address;
use alloy::providers::{Provider, ProviderBuilder};
use eyre::{eyre, Result, WrapErr};

/// In-memory monotonically-increasing nonce.
pub struct NonceManager {
    inner: AtomicU64,
}

/// Outcome of comparing the in-memory nonce against the live chain nonce.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum NonceSync {
    /// In-memory value is consistent with the chain (equal, or exactly one
    /// ahead — a single in-flight transaction).
    InSync,
    /// The chain has advanced past the in-memory value; re-anchor to it.
    Reanchor(u64),
    /// The in-memory value is two or more ahead of the chain — an in-flight
    /// transaction has likely been dropped and needs replacement.
    DriftAhead { local: u64, chain: u64 },
}

/// Classify the in-memory (`local`) nonce against the on-chain (`chain`)
/// nonce. Pure — the RPC fetch lives in [`NonceManager::reconcile`].
fn evaluate(local: u64, chain: u64) -> NonceSync {
    if chain > local {
        NonceSync::Reanchor(chain)
    } else if local > chain + 1 {
        NonceSync::DriftAhead { local, chain }
    } else {
        NonceSync::InSync
    }
}

impl NonceManager {
    /// Construct anchored at the supplied on-chain nonce.
    pub fn new(initial: u64) -> Self {
        Self {
            inner: AtomicU64::new(initial),
        }
    }

    /// Reserve and return the next nonce. Lock-free.
    pub fn acquire(&self) -> u64 {
        self.inner.fetch_add(1, Ordering::AcqRel)
    }

    /// Re-anchor to a fresh on-chain value (called after RPC reconciliation
    /// or after a tx replacement collapses an outstanding gap).
    pub fn reset(&self, value: u64) {
        self.inner.store(value, Ordering::Release);
    }

    /// Reconcile against the live on-chain nonce for `address`. Re-anchors
    /// silently when the chain has advanced; returns `Err` when the
    /// in-memory value has drifted two or more ahead of the chain (an
    /// in-flight tx disappeared from the mempool, requiring replacement).
    pub async fn reconcile(&self, arb_rpc_http: &str, address: Address) -> Result<()> {
        let url = arb_rpc_http
            .parse()
            .wrap_err("invalid Arbitrum RPC HTTP URL")?;
        let provider = ProviderBuilder::new().connect_http(url);
        let chain = provider
            .get_transaction_count(address)
            .await
            .wrap_err("eth_getTransactionCount(latest) failed")?;

        match evaluate(self.inner.load(Ordering::Acquire), chain) {
            NonceSync::InSync => Ok(()),
            NonceSync::Reanchor(value) => {
                self.reset(value);
                Ok(())
            }
            NonceSync::DriftAhead { local, chain } => Err(eyre!(
                "nonce drift: in-memory {local} is {} ahead of chain {chain}; \
                 an in-flight tx needs replacement",
                local - chain
            )),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn acquire_is_monotonic() {
        let nonce = NonceManager::new(7);
        assert_eq!(nonce.acquire(), 7);
        assert_eq!(nonce.acquire(), 8);
        nonce.reset(20);
        assert_eq!(nonce.acquire(), 20);
    }

    #[test]
    fn evaluate_classifies_nonce_states() {
        // Equal, or exactly one ahead (single in-flight tx) — in sync.
        assert_eq!(evaluate(5, 5), NonceSync::InSync);
        assert_eq!(evaluate(6, 5), NonceSync::InSync);
        // Chain advanced past us — re-anchor.
        assert_eq!(evaluate(5, 6), NonceSync::Reanchor(6));
        assert_eq!(evaluate(5, 9), NonceSync::Reanchor(9));
        // Two or more ahead of the chain — drift.
        assert_eq!(evaluate(7, 5), NonceSync::DriftAhead { local: 7, chain: 5 },);
    }

    #[test]
    fn nonce_sync_derives_debug_and_eq() {
        let drift = NonceSync::DriftAhead { local: 9, chain: 4 };
        assert_eq!(drift, drift);
        assert!(format!("{drift:?}").contains("DriftAhead"));
    }

    #[tokio::test]
    async fn reconcile_rejects_an_invalid_rpc_url() {
        let nonce = NonceManager::new(1);
        let err = nonce
            .reconcile("not-a-valid-url", Address::ZERO)
            .await
            .expect_err("an unparseable RPC URL must fail reconciliation");
        assert!(err.to_string().contains("invalid Arbitrum RPC HTTP URL"));
    }
}
