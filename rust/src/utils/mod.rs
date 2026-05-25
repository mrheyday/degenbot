//! Cross-cutting utilities used by multiple modules.
//!
//! Kept deliberately small — anything strategy-specific belongs under the
//! relevant module, not here.

pub mod adaptive_timeout;
pub mod averager;
pub mod metrics;
pub mod nonce;
pub mod u256;
pub mod window;
