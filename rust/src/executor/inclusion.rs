//! Inclusion watcher — observes a submitted tx until terminal status
//! (mined, replaced, dropped) or until `deadline_ms` elapses.
//!
//! Hybrid strategy:
//! 1. Attempt `eth_subscribe("newHeads")` for sub-block-time reactivity.
//! 2. On each new head, check `eth_getTransactionReceipt`.
//! 3. Race against a 250ms poll-timeout fallback so HTTP-only providers
//!    (no pubsub) still terminate cleanly.
//! 4. Race against `deadline_ms` so a brief outage doesn't extend our budget.
//!
//! When pubsub is unavailable (HTTP provider, e.g. `connect()` chose HTTP),
//! we degrade to pure polling. Both paths share the same Settlement output.

use std::time::Duration;

use alloy::primitives::{Address, B256, I256, U256};
use alloy::providers::Provider;
use alloy::rpc::types::eth::TransactionReceipt;
use futures::StreamExt;

use super::{InclusionError, InclusionOutcome, InclusionReceipt};

/// Default poll interval. Arbitrum block time is ~250 ms, so this catches
/// inclusion within ~1 block of mining even when pubsub is unavailable.
pub const DEFAULT_POLL_INTERVAL_MS: u64 = 250;

/// Watch for `tx_hash`'s receipt until it appears OR `deadline_ms` elapses
/// (returning `Dropped`).
///
/// First tries `eth_subscribe("newHeads")` and triggers a receipt check on
/// every new head; that gives sub-poll-interval latency on WS providers.
/// On HTTP-only providers (or any pubsub error), gracefully degrades to
/// pure polling.
pub async fn watch<P: Provider>(
    provider: &P,
    tx_hash: B256,
    deadline_ms: u64,
) -> Result<InclusionOutcome, InclusionError> {
    watch_internal(provider, tx_hash, deadline_ms, None).await
}

/// Watch for `tx_hash` with signer/nonce context. If the receipt never
/// appears but the signer account's mined nonce advances past `nonce`, the
/// transaction was replaced by another mined transaction from the same
/// account.
pub async fn watch_with_replacement<P: Provider>(
    provider: &P,
    tx_hash: B256,
    from: Address,
    nonce: u64,
    deadline_ms: u64,
) -> Result<InclusionOutcome, InclusionError> {
    watch_internal(
        provider,
        tx_hash,
        deadline_ms,
        Some(ReplacementProbe { from, nonce }),
    )
    .await
}

#[derive(Debug, Clone, Copy)]
struct ReplacementProbe {
    from: Address,
    nonce: u64,
}

async fn watch_internal<P: Provider>(
    provider: &P,
    tx_hash: B256,
    deadline_ms: u64,
    replacement: Option<ReplacementProbe>,
) -> Result<InclusionOutcome, InclusionError> {
    let poll = Duration::from_millis(DEFAULT_POLL_INTERVAL_MS);

    // Try to attach a head stream. Falls back to None on HTTP / pubsub error.
    let head_stream = match provider.subscribe_blocks().await {
        Ok(sub) => Some(sub.into_stream()),
        Err(e) => {
            tracing::debug!(
                target: "engine::executor::inclusion",
                error = %e,
                "subscribe_blocks unavailable; falling back to poll-only"
            );
            None
        }
    };

    if let Some(mut stream) = head_stream {
        loop {
            if deadline_passed(deadline_ms) {
                return Ok(InclusionOutcome::Dropped);
            }
            if let Some(outcome) = check_receipt(provider, tx_hash).await? {
                return Ok(outcome);
            }
            if let Some(outcome) = check_replacement(provider, replacement).await? {
                return Ok(outcome);
            }
            // Race: new head OR poll timeout OR deadline.
            tokio::select! {
                _ = stream.next() => {}
                _ = tokio::time::sleep(poll) => {}
                _ = tokio::time::sleep(deadline_remaining(deadline_ms)) => {
                    return Ok(InclusionOutcome::Dropped);
                }
            }
        }
    } else {
        loop {
            if deadline_passed(deadline_ms) {
                return Ok(InclusionOutcome::Dropped);
            }
            if let Some(outcome) = check_receipt(provider, tx_hash).await? {
                return Ok(outcome);
            }
            if let Some(outcome) = check_replacement(provider, replacement).await? {
                return Ok(outcome);
            }
            tokio::time::sleep(poll).await;
        }
    }
}

async fn check_replacement<P: Provider>(
    provider: &P,
    replacement: Option<ReplacementProbe>,
) -> Result<Option<InclusionOutcome>, InclusionError> {
    let Some(probe) = replacement else {
        return Ok(None);
    };

    match provider.get_transaction_count(probe.from).await {
        Ok(mined_nonce) if mined_nonce > probe.nonce => Ok(Some(InclusionOutcome::Replaced)),
        Ok(_) => Ok(None),
        Err(e) => Err(InclusionError::Rpc(format!("get_transaction_count: {e}"))),
    }
}

async fn check_receipt<P: Provider>(
    provider: &P,
    tx_hash: B256,
) -> Result<Option<InclusionOutcome>, InclusionError> {
    match provider.get_transaction_receipt(tx_hash).await {
        Ok(Some(receipt)) => Ok(Some(InclusionOutcome::Mined(decode_receipt(receipt)))),
        Ok(None) => Ok(None),
        Err(e) => Err(InclusionError::Rpc(format!("get_receipt: {e}"))),
    }
}

fn deadline_passed(deadline_ms: u64) -> bool {
    now_ms() >= deadline_ms
}

fn deadline_remaining(deadline_ms: u64) -> Duration {
    let now = now_ms();
    if now >= deadline_ms {
        Duration::ZERO
    } else {
        Duration::from_millis(deadline_ms - now)
    }
}

fn now_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(u64::MAX)
}

fn decode_receipt(receipt: TransactionReceipt) -> InclusionReceipt {
    let block_number = receipt.block_number.unwrap_or(0);
    let gas_used = receipt.gas_used;
    let effective_gas_price_wei = U256::from(receipt.effective_gas_price);
    let status = receipt.status();

    InclusionReceipt {
        block_number,
        gas_used,
        effective_gas_price_wei,
        // LiveBackend overwrites this with a pre/post profit-token balance
        // delta after inclusion when submitted-tx context is available.
        realized_balance_delta: I256::ZERO,
        status,
        revert_reason: if status {
            None
        } else {
            Some("reverted; receipt did not expose revert data".to_string())
        },
    }
}
