#![cfg_attr(
    not(any(test, feature = "export-abi", feature = "native-test")),
    no_main
)]
#![cfg_attr(feature = "contract-client-gen", allow(unused_imports))]
#![cfg_attr(feature = "native-test", allow(dead_code))]

extern crate alloc;

use alloc::string::String;
use alloc::vec::Vec;

use stylus_sdk::alloy_primitives::{Address, U256};

#[path = "../../core/src/token_risk_filter.rs"]
pub mod token_risk_filter;

#[cfg(all(not(any(test, feature = "native-test")), not(target_arch = "wasm32")))]
mod native_hostio_shims {
    include!("../../test_hostio_shims.rs");
}

#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::{
    call::RawCall,
    prelude::*,
    stylus_core::host::{AccountAccess, BlockAccess},
};

#[cfg(not(any(test, feature = "native-test")))]
const OWNER_SELECTOR: [u8; 4] = [0x8d, 0xa5, 0xcb, 0x5b];
const TRANSFER_SELECTOR: [u8; 4] = [0xa9, 0x05, 0x9c, 0xbb];
#[cfg(not(any(test, feature = "native-test")))]
const BLACKLIST_SELECTOR: [u8; 4] = [0x8e, 0xcf, 0xd9, 0xa7];
#[cfg(not(any(test, feature = "native-test")))]
const PAUSED_SELECTOR: [u8; 4] = [0x5c, 0x97, 0x5a, 0xbb];
const TRANSFER_PROBE_AMOUNT: u128 = 1_000_000_000_000_000_000;

#[cfg(not(any(test, feature = "native-test")))]
sol_storage! {
    #[entrypoint]
    pub struct TokenRiskAdapter {
        mapping(address => uint256) cached_risk;
        mapping(address => uint256) cache_timestamp;
    }
}

#[cfg(not(any(test, feature = "native-test")))]
#[public]
impl TokenRiskAdapter {
    pub fn is_major(&self, token: Address) -> bool {
        token_risk_filter::is_major(token)
    }

    pub fn known_risk_mask(&self) -> U256 {
        token_risk_filter::known_risk_mask()
    }

    pub fn cache_ttl_seconds(&self) -> U256 {
        U256::from(token_risk_filter::CACHE_TTL_SECONDS)
    }

    pub fn risk_staticcall_gas(&self) -> U256 {
        U256::from(token_risk_filter::RISK_STATICCALL_GAS)
    }

    pub fn is_safe_flags(&self, flags: U256) -> bool {
        token_risk_filter::is_safe_flags(flags)
    }

    pub fn assess_external(&self, token: Address) -> (U256, bool) {
        let verdict = self.assess(token);
        (verdict.flags, verdict.is_safe)
    }

    pub fn assess_external_with_reasons(&self, token: Address) -> (U256, bool, Vec<String>) {
        let verdict = self.assess(token);
        (
            verdict.flags,
            verdict.is_safe,
            reason_strings(&verdict.reasons),
        )
    }

    pub fn assess_batch(&self, tokens: Vec<Address>) -> (Vec<U256>, Vec<bool>) {
        let mut flags = Vec::with_capacity(tokens.len());
        let mut safe = Vec::with_capacity(tokens.len());
        for token in tokens {
            let verdict = self.assess(token);
            flags.push(verdict.flags);
            safe.push(verdict.is_safe);
        }
        (flags, safe)
    }

    pub fn assess_batch_with_reasons(
        &self,
        tokens: Vec<Address>,
    ) -> (Vec<U256>, Vec<bool>, Vec<Vec<String>>) {
        let mut flags = Vec::with_capacity(tokens.len());
        let mut safe = Vec::with_capacity(tokens.len());
        let mut reasons = Vec::with_capacity(tokens.len());
        for token in tokens {
            let verdict = self.assess(token);
            flags.push(verdict.flags);
            safe.push(verdict.is_safe);
            reasons.push(reason_strings(&verdict.reasons));
        }
        (flags, safe, reasons)
    }

    pub fn update_cache(&mut self, token: Address) -> (U256, bool) {
        let verdict = self.assess(token);
        self.cached_risk.insert(token, verdict.flags);
        self.cache_timestamp
            .insert(token, U256::from(self.vm().block_timestamp()));
        (verdict.flags, verdict.is_safe)
    }

    pub fn get_cached_verdict(&self, token: Address) -> (U256, bool) {
        let timestamp = self.cache_timestamp.get(token);
        let now = U256::from(self.vm().block_timestamp());
        let is_fresh = timestamp != U256::ZERO
            && now >= timestamp
            && now - timestamp < U256::from(token_risk_filter::CACHE_TTL_SECONDS);
        if is_fresh {
            (self.cached_risk.get(token), true)
        } else {
            (U256::ZERO, false)
        }
    }
}

#[cfg(not(any(test, feature = "native-test")))]
impl TokenRiskAdapter {
    fn assess(&self, token: Address) -> token_risk_filter::RiskVerdict {
        if token_risk_filter::is_major(token) {
            return token_risk_filter::assess_probe(
                token,
                token_risk_filter::ProbeVerdict {
                    has_code: true,
                    owner_renounced: None,
                    transfer_result: token_risk_filter::TransferProbe::EmptyReturn,
                    has_blacklist: false,
                    paused: Some(false),
                },
            );
        }

        if self.vm().code_size(token) == 0 {
            return token_risk_filter::assess_probe(
                token,
                token_risk_filter::ProbeVerdict::no_code(),
            );
        }

        let owner_renounced = self
            .bounded_static_call(token, &OWNER_SELECTOR)
            .ok()
            .and_then(|data| decode_abi_address(&data))
            .map(|owner| owner == Address::ZERO);

        let transfer_result = match self
            .bounded_static_call(token, &encode_transfer_probe(self.vm().contract_address()))
        {
            Ok(data) if data.is_empty() => token_risk_filter::TransferProbe::EmptyReturn,
            Ok(data) if data.len() == 32 => decode_abi_bool(&data)
                .map(token_risk_filter::TransferProbe::ReturnedBool)
                .unwrap_or(token_risk_filter::TransferProbe::MalformedReturn),
            Ok(_) => token_risk_filter::TransferProbe::MalformedReturn,
            Err(_) => token_risk_filter::TransferProbe::Unavailable,
        };

        let has_blacklist = self.bounded_static_call(token, &BLACKLIST_SELECTOR).is_ok();

        let paused = self
            .bounded_static_call(token, &PAUSED_SELECTOR)
            .ok()
            .and_then(|data| decode_abi_bool(&data));

        token_risk_filter::assess_probe(
            token,
            token_risk_filter::ProbeVerdict {
                has_code: true,
                owner_renounced,
                transfer_result,
                has_blacklist,
                paused,
            },
        )
    }

    fn bounded_static_call(&self, token: Address, calldata: &[u8]) -> Result<Vec<u8>, Vec<u8>> {
        unsafe {
            RawCall::new_static(self.vm())
                .gas(token_risk_filter::RISK_STATICCALL_GAS)
                .limit_return_data(0, 32)
                .call(token, calldata)
        }
    }
}

fn encode_transfer_probe(recipient: Address) -> Vec<u8> {
    let mut out = Vec::with_capacity(68);
    out.extend_from_slice(&TRANSFER_SELECTOR);
    push_address_word(&mut out, recipient);
    push_u256_word(&mut out, U256::from(TRANSFER_PROBE_AMOUNT));
    out
}

fn decode_abi_address(data: &[u8]) -> Option<Address> {
    if data.len() != 32 || data[..12].iter().any(|byte| *byte != 0) {
        return None;
    }
    Some(Address::from_slice(&data[12..]))
}

fn decode_abi_bool(data: &[u8]) -> Option<bool> {
    if data.len() != 32 || data[..31].iter().any(|byte| *byte != 0) {
        return None;
    }
    match data[31] {
        0 => Some(false),
        1 => Some(true),
        _ => None,
    }
}

fn reason_strings(reasons: &[token_risk_filter::RiskReason]) -> Vec<String> {
    reasons.iter().map(|reason| reason.to_label()).collect()
}

fn push_address_word(out: &mut Vec<u8>, value: Address) {
    out.extend_from_slice(&[0_u8; 12]);
    out.extend_from_slice(value.as_slice());
}

fn push_u256_word(out: &mut Vec<u8>, value: U256) {
    out.extend_from_slice(&value.to_be_bytes::<32>());
}

#[cfg(test)]
mod tests {
    use super::*;
    use stylus_sdk::alloy_primitives::Address;

    #[test]
    fn transfer_probe_calldata_matches_solidity_shape() {
        let recipient = Address::repeat_byte(0x11);
        let calldata = encode_transfer_probe(recipient);

        assert_eq!(68, calldata.len());
        assert_eq!(TRANSFER_SELECTOR, calldata[..4]);
        assert_eq!([0_u8; 12], calldata[4..16]);
        assert_eq!(recipient.as_slice(), &calldata[16..36]);
        assert_eq!(
            U256::from(TRANSFER_PROBE_AMOUNT).to_be_bytes::<32>(),
            calldata[36..]
        );
    }

    #[test]
    fn abi_decoders_are_strict() {
        let address = Address::repeat_byte(0x22);
        let mut word = [0_u8; 32];
        word[12..].copy_from_slice(address.as_slice());
        assert_eq!(Some(address), decode_abi_address(&word));
        word[0] = 1;
        assert_eq!(None, decode_abi_address(&word));

        let mut bool_word = [0_u8; 32];
        assert_eq!(Some(false), decode_abi_bool(&bool_word));
        bool_word[31] = 1;
        assert_eq!(Some(true), decode_abi_bool(&bool_word));
        bool_word[31] = 2;
        assert_eq!(None, decode_abi_bool(&bool_word));
    }

    #[test]
    fn reason_strings_match_solidity_literals() {
        assert_eq!(
            vec![
                String::from("token_has_no_code"),
                String::from("transfer_failed_or_tax"),
                String::from("has_blacklist_function"),
                String::from("transfers_are_paused"),
            ],
            reason_strings(&[
                token_risk_filter::RiskReason::TokenHasNoCode,
                token_risk_filter::RiskReason::TransferFailedOrTax,
                token_risk_filter::RiskReason::HasBlacklistFunction,
                token_risk_filter::RiskReason::TransfersArePaused,
            ])
        );
    }

    #[test]
    fn batch_reason_strings_preserve_per_token_grouping() {
        let reason_groups = [
            vec![token_risk_filter::RiskReason::TokenHasNoCode],
            vec![
                token_risk_filter::RiskReason::TransferSimulationUnavailable,
                token_risk_filter::RiskReason::HasBlacklistFunction,
            ],
            Vec::new(),
        ];
        let rendered: Vec<Vec<String>> = reason_groups
            .iter()
            .map(|group| reason_strings(group))
            .collect();

        assert_eq!(
            vec![
                vec![String::from("token_has_no_code")],
                vec![
                    String::from("transfer_simulation_unavailable"),
                    String::from("has_blacklist_function"),
                ],
                Vec::<String>::new(),
            ],
            rendered
        );
    }
}
