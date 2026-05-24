//! Batched event feed.
//!
//! Aggregates `DecodedEvent`s over a small tumbling window so that the
//! strategy layer can process correlated state changes (e.g., several pools
//! mutated in the same block) as a unit. Per `09-LATENCY-BUDGET.md` §5.2:
//! batching is opt-in for the long tail of low-volume pools — high-volume
//! USDC/USDT/WETH/ARB pairs always run unbatched.

use std::time::{Duration, SystemTime, UNIX_EPOCH};

use eyre::Result;
use tokio::sync::mpsc;
use tokio::time::MissedTickBehavior;

use crate::monitor::sync_event::DecodedEvent;

/// Tunable for the batching window. The default is short (5 ms) so we
/// remain inside the 20 ms p99 budget for state mutation.
pub const DEFAULT_BATCH_WINDOW: Duration = Duration::from_millis(5);

/// One batch of decoded events ready to be applied to the simulation cache.
#[derive(Debug, Clone, Default)]
pub struct EventBatch {
    pub events: Vec<DecodedEvent>,
    pub flushed_at_ns: u64,
}

/// Batches incoming `DecodedEvent`s into `EventBatch`es with a tumbling
/// window.
pub struct Batcher {
    pub window: Duration,
}

impl Batcher {
    pub fn new(window: Duration) -> Self {
        Self { window }
    }

    /// Drive the batcher until `rx` is closed (upstream gone) or `tx` is
    /// closed (downstream gone). On each window tick a non-empty buffer is
    /// flushed as one `EventBatch`; the final partial batch is flushed when
    /// `rx` closes.
    pub async fn run(
        self,
        mut rx: mpsc::Receiver<DecodedEvent>,
        tx: mpsc::Sender<EventBatch>,
    ) -> Result<()> {
        let mut interval = tokio::time::interval(self.window);
        interval.set_missed_tick_behavior(MissedTickBehavior::Delay);
        let mut buffer: Vec<DecodedEvent> = Vec::new();

        loop {
            tokio::select! {
                received = rx.recv() => match received {
                    Some(event) => buffer.push(event),
                    None => {
                        // Upstream closed — flush the remainder and stop.
                        if !buffer.is_empty() {
                            let _ = tx.send(flush(&mut buffer)).await;
                        }
                        return Ok(());
                    }
                },
                _ = interval.tick() => {
                    if !buffer.is_empty() && tx.send(flush(&mut buffer)).await.is_err() {
                        // Downstream closed.
                        return Ok(());
                    }
                }
            }
        }
    }
}

/// Drain `buffer` into a timestamped `EventBatch`.
fn flush(buffer: &mut Vec<DecodedEvent>) -> EventBatch {
    EventBatch {
        events: std::mem::take(buffer),
        flushed_at_ns: now_ns(),
    }
}

fn now_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| u64::try_from(d.as_nanos()).unwrap_or(u64::MAX))
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test(flavor = "multi_thread")]
    async fn batches_events_within_the_window() {
        let (event_tx, event_rx) = mpsc::channel(64);
        let (batch_tx, mut batch_rx) = mpsc::channel(64);
        let batcher = Batcher::new(Duration::from_millis(5));
        let handle = tokio::spawn(batcher.run(event_rx, batch_tx));

        for block in 0..3u64 {
            event_tx
                .send(DecodedEvent::Tip {
                    block_number: block,
                })
                .await
                .unwrap();
        }
        // Close the channel so the final partial batch flushes.
        drop(event_tx);

        let mut total = 0usize;
        while let Some(batch) = batch_rx.recv().await {
            total += batch.events.len();
        }
        assert_eq!(total, 3);
        handle.await.unwrap().unwrap();
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn stops_when_downstream_closes() {
        let (event_tx, event_rx) = mpsc::channel(64);
        let (batch_tx, batch_rx) = mpsc::channel(64);
        let batcher = Batcher::new(Duration::from_millis(1));
        let handle = tokio::spawn(batcher.run(event_rx, batch_tx));

        drop(batch_rx); // downstream gone
        for block in 0..10u64 {
            let _ = event_tx
                .send(DecodedEvent::Tip {
                    block_number: block,
                })
                .await;
        }
        // The batcher must terminate rather than spin forever.
        handle.await.unwrap().unwrap();
    }
}
