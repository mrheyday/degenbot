//! Live subscriber for the Arbitrum sequencer broadcast feed.
//!
//! Connects to the public WS endpoint (`wss://arb1.arbitrum.io/feed` by
//! default), parses [`BroadcastMessage`] envelopes via
//! [`parse_envelope`], and forwards each individual
//! [`BroadcastFeedMessage`] onto a caller-provided `mpsc::Sender`.
//! Confirmation markers (`ConfirmedSequenceNumberMessage`) are forwarded
//! through a separate channel so consumers that only care about new
//! messages don't pay an `if` per frame.
//!
//! Reconnect on transport error with exponential backoff (capped at 30s).
//! The loop runs until the supplied `CancellationToken` fires or the
//! sender side closes (`SendError`).

use std::time::Duration;

use eyre::{Result, WrapErr};
use futures::{SinkExt, StreamExt};
use tokio::net::TcpStream;
use tokio::sync::mpsc;
use tokio_tungstenite::tungstenite::client::IntoClientRequest;
use tokio_tungstenite::tungstenite::Message;
use tokio_tungstenite::{connect_async, MaybeTlsStream, WebSocketStream};
use tracing::{debug, info, warn};

use crate::monitor::sequencer_broadcast::{
    parse_envelope, BroadcastFeedMessage, BroadcastMessage, ConfirmedSequenceNumberMessage,
};

/// Public Arbitrum One sequencer feed URL.
pub const ARBITRUM_ONE_FEED_URL: &str = "wss://arb1.arbitrum.io/feed";

/// Initial reconnect delay; doubles per failure up to [`MAX_BACKOFF`].
const INITIAL_BACKOFF: Duration = Duration::from_millis(500);
const MAX_BACKOFF: Duration = Duration::from_secs(30);

/// Configuration for the subscriber.
#[derive(Debug, Clone)]
pub struct SubscriberConfig {
    pub url: String,
    /// Forward every individual `BroadcastFeedMessage` to this channel.
    /// Per-frame `messages` arrays are flattened.
    pub messages_capacity: usize,
    /// Forward confirmations here. Optional — set capacity to 0 to
    /// disable.
    pub confirmations_capacity: usize,
    /// Forward parse errors here for observability. Optional.
    pub errors_capacity: usize,
}

impl Default for SubscriberConfig {
    fn default() -> Self {
        Self {
            url: ARBITRUM_ONE_FEED_URL.to_string(),
            messages_capacity: 1024,
            confirmations_capacity: 32,
            errors_capacity: 32,
        }
    }
}

/// Channels exposed to the consumer side.
pub struct SubscriberHandles {
    pub messages: mpsc::Receiver<BroadcastFeedMessage>,
    pub confirmations: mpsc::Receiver<ConfirmedSequenceNumberMessage>,
    pub errors: mpsc::Receiver<eyre::Report>,
}

/// Inner sender side, owned by the subscriber loop.
struct SubscriberSinks {
    messages: mpsc::Sender<BroadcastFeedMessage>,
    confirmations: mpsc::Sender<ConfirmedSequenceNumberMessage>,
    errors: mpsc::Sender<eyre::Report>,
}

/// Spawn the subscriber loop. Returns the consumer-side handles
/// immediately; the loop runs until the cancellation token fires or
/// every receiver is dropped (which makes `SendError` shut us down).
pub fn spawn(cfg: SubscriberConfig, cancel: tokio_util_compat::CancelToken) -> SubscriberHandles {
    let (msg_tx, msg_rx) = mpsc::channel(cfg.messages_capacity);
    let (conf_tx, conf_rx) = mpsc::channel(cfg.confirmations_capacity);
    let (err_tx, err_rx) = mpsc::channel(cfg.errors_capacity);

    let sinks = SubscriberSinks {
        messages: msg_tx,
        confirmations: conf_tx,
        errors: err_tx,
    };

    tokio::spawn(run_loop(cfg, sinks, cancel));

    SubscriberHandles {
        messages: msg_rx,
        confirmations: conf_rx,
        errors: err_rx,
    }
}

async fn run_loop(
    cfg: SubscriberConfig,
    sinks: SubscriberSinks,
    cancel: tokio_util_compat::CancelToken,
) {
    let mut backoff = INITIAL_BACKOFF;
    loop {
        if cancel.is_cancelled() {
            info!("sequencer subscriber: cancellation requested, exiting");
            return;
        }
        match connect_once(&cfg.url, &sinks, &cancel).await {
            Ok(()) => {
                debug!("sequencer subscriber: clean disconnect, reconnecting");
                backoff = INITIAL_BACKOFF;
            }
            Err(err) => {
                warn!(err = %err, backoff_ms = backoff.as_millis() as u64,
                      "sequencer subscriber: connection failed, retrying");
                let _ = sinks.errors.try_send(err);
                tokio::select! {
                    _ = tokio::time::sleep(backoff) => {}
                    _ = cancel.cancelled() => return,
                }
                backoff = (backoff * 2).min(MAX_BACKOFF);
            }
        }
    }
}

async fn connect_once(
    url: &str,
    sinks: &SubscriberSinks,
    cancel: &tokio_util_compat::CancelToken,
) -> Result<()> {
    let req = url
        .into_client_request()
        .wrap_err_with(|| format!("invalid WS URL: {url}"))?;
    let (mut ws, resp) = connect_async(req).await.wrap_err("WS connect failed")?;
    info!(url = %url, status = resp.status().as_u16(), "sequencer feed connected");

    loop {
        tokio::select! {
            _ = cancel.cancelled() => {
                let _ = ws.close(None).await;
                return Ok(());
            }
            frame = ws.next() => {
                match frame {
                    Some(Ok(Message::Text(text))) => dispatch_envelope(text.as_bytes(), sinks).await?,
                    Some(Ok(Message::Binary(bytes))) => dispatch_envelope(&bytes, sinks).await?,
                    Some(Ok(Message::Ping(p))) => {
                        ws.send(Message::Pong(p)).await.wrap_err("pong send failed")?;
                    }
                    Some(Ok(Message::Pong(_))) | Some(Ok(Message::Frame(_))) => {}
                    Some(Ok(Message::Close(_))) | None => return Ok(()),
                    Some(Err(e)) => return Err(eyre::eyre!("ws read error: {e}")),
                }
            }
        }
    }
}

async fn dispatch_envelope(raw: &[u8], sinks: &SubscriberSinks) -> Result<()> {
    let env: BroadcastMessage = match parse_envelope(raw) {
        Ok(e) => e,
        Err(e) => {
            // Treat parse errors as observable but non-fatal; upstream
            // occasionally sends keep-alive frames or partial envelopes.
            let _ = sinks.errors.try_send(eyre::eyre!("parse: {e}"));
            return Ok(());
        }
    };

    if let Some(msgs) = env.messages {
        for m in msgs {
            // `send` (not `try_send`) so we apply backpressure when the
            // strategy layer is slow — we'd rather drop frames at the
            // socket level than reorder them in the consumer.
            if sinks.messages.send(m).await.is_err() {
                return Err(eyre::eyre!("messages receiver dropped"));
            }
        }
    }
    if let Some(conf) = env.confirmed_sequence_number_message {
        // Confirmations are low-volume; a try_send is fine.
        let _ = sinks.confirmations.try_send(conf);
    }
    Ok(())
}

/// Lightweight cancellation primitive. Avoids pulling in
/// `tokio-util` for one type.
pub mod tokio_util_compat {
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;

    use tokio::sync::Notify;

    /// One-shot cancellation token: clone-able, thread-safe.
    #[derive(Clone, Default)]
    pub struct CancelToken {
        cancelled: Arc<AtomicBool>,
        notify: Arc<Notify>,
    }

    impl CancelToken {
        pub fn new() -> Self {
            Self::default()
        }

        pub fn cancel(&self) {
            self.cancelled.store(true, Ordering::Relaxed);
            self.notify.notify_waiters();
        }

        pub fn is_cancelled(&self) -> bool {
            self.cancelled.load(Ordering::Relaxed)
        }

        pub async fn cancelled(&self) {
            if self.is_cancelled() {
                return;
            }
            self.notify.notified().await;
        }
    }
}

// Helper retained for type-pinning / future trait-object work.
#[allow(dead_code)]
type WsStream = WebSocketStream<MaybeTlsStream<TcpStream>>;

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn dispatch_forwards_messages_and_confirmations() {
        let (msg_tx, mut msg_rx) = mpsc::channel(8);
        let (conf_tx, mut conf_rx) = mpsc::channel(8);
        let (err_tx, _err_rx) = mpsc::channel(8);
        let sinks = SubscriberSinks {
            messages: msg_tx,
            confirmations: conf_tx,
            errors: err_tx,
        };

        let raw = br#"{
            "version": 1,
            "messages": [
                {"sequenceNumber": 1, "message": {}, "signatureV2": ""},
                {"sequenceNumber": 2, "message": {}, "signatureV2": ""}
            ],
            "confirmedSequenceNumberMessage": {"sequenceNumber": 7}
        }"#;

        dispatch_envelope(raw, &sinks).await.unwrap();

        let m1 = msg_rx.recv().await.unwrap();
        let m2 = msg_rx.recv().await.unwrap();
        let c = conf_rx.recv().await.unwrap();
        assert_eq!(m1.sequence_number, 1);
        assert_eq!(m2.sequence_number, 2);
        assert_eq!(c.sequence_number, 7);
    }

    #[tokio::test]
    async fn dispatch_swallows_parse_errors_to_error_channel() {
        let (msg_tx, _msg_rx) = mpsc::channel(8);
        let (conf_tx, _conf_rx) = mpsc::channel(8);
        let (err_tx, mut err_rx) = mpsc::channel(8);
        let sinks = SubscriberSinks {
            messages: msg_tx,
            confirmations: conf_tx,
            errors: err_tx,
        };

        let raw = br#"{ not valid json }"#;
        dispatch_envelope(raw, &sinks).await.unwrap();
        let err = err_rx.recv().await.expect("error reported");
        assert!(format!("{err:?}").contains("parse"));
    }

    #[tokio::test]
    async fn cancel_token_signals_immediately() {
        let tok = tokio_util_compat::CancelToken::new();
        assert!(!tok.is_cancelled());
        let tok2 = tok.clone();
        let h = tokio::spawn(async move { tok2.cancelled().await });
        tok.cancel();
        h.await.unwrap();
        assert!(tok.is_cancelled());
    }
}
