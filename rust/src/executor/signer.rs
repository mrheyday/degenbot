//! `PRIVATE_KEY` custodian — sole copy of the bot's signing key under
//! ADR-026's three-layer split.

use alloy::primitives::Address;
use alloy::signers::local::PrivateKeySigner;

use super::SubmitError;

/// Wrapper around `alloy::signers::local::PrivateKeySigner`. Loads the key
/// from the `PRIVATE_KEY` environment variable on construction. Once built,
/// the inner signer is used both for tx signing (via `EthereumWallet`) and
/// for resolving the bot's address in nonce / balance queries.
#[derive(Clone)]
pub struct ExecutorSigner {
    signer: PrivateKeySigner,
}

impl ExecutorSigner {
    /// Read `PRIVATE_KEY` from env and parse. Returns `Err` if the var is
    /// unset or malformed — the engine MUST refuse to boot the executor task
    /// without a valid key.
    pub fn from_env() -> Result<Self, SubmitError> {
        let key = std::env::var("PRIVATE_KEY")
            .map_err(|_| SubmitError::Signer("PRIVATE_KEY not set".into()))?;
        let signer: PrivateKeySigner = key
            .parse()
            .map_err(|e| SubmitError::Signer(format!("PRIVATE_KEY parse error: {e}")))?;
        Ok(Self { signer })
    }

    /// Build from a literal hex string. Used by tests that spawn anvil with
    /// a known account and don't want to mutate process env.
    #[cfg(test)]
    pub fn from_hex(hex: &str) -> Result<Self, SubmitError> {
        let signer: PrivateKeySigner = hex
            .parse()
            .map_err(|e| SubmitError::Signer(format!("hex parse error: {e}")))?;
        Ok(Self { signer })
    }

    pub fn address(&self) -> Address {
        self.signer.address()
    }

    pub fn inner(&self) -> &PrivateKeySigner {
        &self.signer
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Anvil's default test account #0 — well-known unfunded-elsewhere key.
    /// Safe to commit; same key is in every Foundry tutorial.
    const ANVIL_KEY_0: &str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
    const ANVIL_ADDRESS_0: &str = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266";

    #[test]
    fn parses_and_recovers_anvil_address() {
        let s = ExecutorSigner::from_hex(ANVIL_KEY_0).unwrap();
        assert_eq!(format!("{}", s.address()), ANVIL_ADDRESS_0);
    }

    #[test]
    fn rejects_garbage_key() {
        assert!(ExecutorSigner::from_hex("not-a-key").is_err());
        assert!(ExecutorSigner::from_hex("").is_err());
    }
}
