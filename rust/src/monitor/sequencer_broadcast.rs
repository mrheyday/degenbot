//! Arbitrum sequencer broadcast feed schema mirror.
//!
//! Source-of-truth: `OffchainLabs/nitro` at
//! `broadcaster/message/message.go` (master @ 2026-05-08). The sequencer
//! publishes a stream of `BroadcastMessage` envelopes over its public WS
//! endpoint (`wss://arb1.arbitrum.io/feed`); each envelope carries one or
//! more `BroadcastFeedMessage`s plus optional confirmation metadata.
//!
//! For T-3 sub-10 ms reaction (per `docs/architecture/04-SYSTEM-ARCHITECTURE.md`
//! and the jaredbot-mev-mempool-relay skill), this is the canonical entry
//! point: parse the envelope, extract the L2 message bodies, RLP-decode the
//! transactions, and dispatch to the strategy layer.
//!
//! # Cross-language parity
//! Mirrored byte-for-byte by [`coordinator/src/feeds/sequencer-broadcast.ts`].
//! Field names + JSON tags MUST stay in sync with upstream Go.
//!
//! # Wire format
//! `[]byte` fields (`Signature`, `BlockMetadata`) are encoded by Go's
//! `encoding/json` as base64 strings (`encoding/base64.StdEncoding`).
//! The serde adapters below decode that representation directly.
//!
//! # Stability
//! `Message` is held as `serde_json::Value` for now — `MessageWithMetadata`
//! has deep nesting (`L1IncomingMessage` → `Header` + `L2msg`) and the
//! exact decoder belongs in a follow-up that wires `alloy_consensus::TxEnvelope`
//! against the Arbitrum L2 RLP framing.

use base64::engine::general_purpose::STANDARD;
use base64::Engine;
use serde::{Deserialize, Deserializer, Serialize, Serializer};

/// One envelope carried over the sequencer WS feed.
///
/// Mirrors `broadcaster/message.BroadcastMessage` (Go).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BroadcastMessage {
    /// Wire-format version. Increment on breaking changes.
    pub version: i64,

    /// Zero or more sequenced messages in this envelope.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub messages: Option<Vec<BroadcastFeedMessage>>,

    /// Confirmation marker (sent independently of `messages`).
    #[serde(
        rename = "confirmedSequenceNumberMessage",
        default,
        skip_serializing_if = "Option::is_none"
    )]
    pub confirmed_sequence_number_message: Option<ConfirmedSequenceNumberMessage>,
}

/// One sequenced L2 message.
///
/// Mirrors `broadcaster/message.BroadcastFeedMessage` (Go).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BroadcastFeedMessage {
    /// L2 message index (`arbutil.MessageIndex` = `uint64`).
    #[serde(rename = "sequenceNumber")]
    pub sequence_number: u64,

    /// L2 message envelope. Held opaque pending nested decoder.
    pub message: serde_json::Value,

    /// L2 block hash; `None` for pre-Pectra messages.
    #[serde(rename = "blockHash", default, skip_serializing_if = "Option::is_none")]
    pub block_hash: Option<String>,

    /// Sequencer signature over the message. Wire form: base64 string.
    #[serde(rename = "signatureV2", with = "base64_bytes")]
    pub signature: Vec<u8>,

    /// Express-lane / Timeboost block metadata. Wire form: base64 string.
    #[serde(
        rename = "blockMetadata",
        default,
        skip_serializing_if = "Option::is_none",
        with = "base64_bytes_opt"
    )]
    pub block_metadata: Option<Vec<u8>>,
    // `CumulativeSumMsgSize` is `json:"-"` in Go — internal counter, never
    // crosses the wire. Intentionally omitted from this mirror.
}

/// Confirmation of a previously broadcast sequence number.
///
/// Mirrors `broadcaster/message.ConfirmedSequenceNumberMessage` (Go).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfirmedSequenceNumberMessage {
    #[serde(rename = "sequenceNumber")]
    pub sequence_number: u64,
}

mod base64_bytes {
    use super::*;

    pub fn serialize<S: Serializer>(val: &Vec<u8>, ser: S) -> Result<S::Ok, S::Error> {
        ser.serialize_str(&STANDARD.encode(val))
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(de: D) -> Result<Vec<u8>, D::Error> {
        let s = String::deserialize(de)?;
        STANDARD.decode(s).map_err(serde::de::Error::custom)
    }
}

mod base64_bytes_opt {
    use super::*;

    pub fn serialize<S: Serializer>(val: &Option<Vec<u8>>, ser: S) -> Result<S::Ok, S::Error> {
        match val {
            Some(b) => ser.serialize_str(&STANDARD.encode(b)),
            None => ser.serialize_none(),
        }
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(de: D) -> Result<Option<Vec<u8>>, D::Error> {
        let opt: Option<String> = Option::deserialize(de)?;
        opt.map(|s| STANDARD.decode(s).map_err(serde::de::Error::custom))
            .transpose()
    }
}

/// Errors surfaced when decoding a sequencer broadcast.
#[derive(Debug, thiserror::Error)]
pub enum BroadcastError {
    #[error("parse: {0}")]
    Parse(#[from] serde_json::Error),

    #[error("envelope contained no messages and no confirmation")]
    EmptyEnvelope,
}

/// Parse a JSON envelope received over the sequencer WS feed.
pub fn parse_envelope(raw: &[u8]) -> Result<BroadcastMessage, BroadcastError> {
    let env: BroadcastMessage = serde_json::from_slice(raw)?;
    if env.messages.as_ref().map(|m| m.is_empty()).unwrap_or(true)
        && env.confirmed_sequence_number_message.is_none()
    {
        return Err(BroadcastError::EmptyEnvelope);
    }
    Ok(env)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `base64("\x01\x02\x03\x04") == "AQIDBA=="` — locks the byte adapter
    /// against the upstream Go `encoding/json` representation.
    #[test]
    fn parse_envelope_with_one_message() {
        let raw = br#"{
            "version": 1,
            "messages": [
                {
                    "sequenceNumber": 12345,
                    "message": {"some": "opaque"},
                    "blockHash": "0xab",
                    "signatureV2": "AQIDBA==",
                    "blockMetadata": "CQk="
                }
            ]
        }"#;

        let env = parse_envelope(raw).expect("decode envelope");
        assert_eq!(env.version, 1);
        let msgs = env.messages.expect("messages present");
        assert_eq!(msgs.len(), 1);
        assert_eq!(msgs[0].sequence_number, 12345);
        assert_eq!(msgs[0].signature, vec![1, 2, 3, 4]);
        assert_eq!(msgs[0].block_metadata.as_deref(), Some(&[9u8, 9][..]));
    }

    #[test]
    fn parse_envelope_with_only_confirmation() {
        let raw = br#"{
            "version": 1,
            "confirmedSequenceNumberMessage": {"sequenceNumber": 42}
        }"#;

        let env = parse_envelope(raw).expect("decode confirmation");
        assert!(env.messages.is_none());
        assert_eq!(
            env.confirmed_sequence_number_message
                .expect("confirmation")
                .sequence_number,
            42
        );
    }

    #[test]
    fn empty_envelope_rejected() {
        let raw = br#"{"version": 1}"#;
        assert!(matches!(
            parse_envelope(raw),
            Err(BroadcastError::EmptyEnvelope)
        ));
    }

    #[test]
    fn round_trip_serialize_then_parse() {
        let original = BroadcastMessage {
            version: 1,
            messages: Some(vec![BroadcastFeedMessage {
                sequence_number: 99,
                message: serde_json::json!({"opaque": true}),
                block_hash: Some("0xdeadbeef".to_string()),
                signature: vec![0xaa, 0xbb, 0xcc],
                block_metadata: Some(vec![0xde, 0xad]),
            }]),
            confirmed_sequence_number_message: None,
        };
        let json = serde_json::to_vec(&original).expect("serialize");
        let parsed = parse_envelope(&json).expect("parse");
        let msg = &parsed.messages.unwrap()[0];
        assert_eq!(msg.signature, vec![0xaa, 0xbb, 0xcc]);
        assert_eq!(msg.block_metadata.as_deref(), Some(&[0xde, 0xad][..]));
    }

    #[test]
    fn rejects_non_base64_signature() {
        let raw = br#"{
            "version": 1,
            "messages": [
                {
                    "sequenceNumber": 1,
                    "message": {},
                    "signatureV2": "!!! not base64 !!!"
                }
            ]
        }"#;
        assert!(matches!(parse_envelope(raw), Err(BroadcastError::Parse(_))));
    }
}
