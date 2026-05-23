use alloy_primitives::fixed_bytes;
use stylus_sdk::alloy_primitives::{FixedBytes, keccak256};

pub const EXPECTED_LENDER_SLOT: FixedBytes<32> =
    fixed_bytes!("0x2a51345724187232c4a2728b319ec298553f3eb52eb998941ca7a0ec47b3f640");
pub const FLOW_ID_SLOT: FixedBytes<32> =
    fixed_bytes!("0xa3fe3d870bd7283af33a8ef894ee9932b4710ce472ac6e764a3f66aaeb33fcf4");
pub const CUMULATIVE_HASH_SLOT: FixedBytes<32> =
    fixed_bytes!("0xa6e7f4e8d6ba213eb0af2b30ea68b8d88ba85042d5b0eda49086f4f9964944a1");
pub const EXECUTING_SLOT: FixedBytes<32> =
    fixed_bytes!("0xee8264938d1089b5222497e075a783e89a24fbe45931de68fb25b0c8f71a0c8f");
pub const EXPECTED_REACTOR_SLOT: FixedBytes<32> =
    fixed_bytes!("0xb8d1bfe6c5e3c6955ae7b64549c13f6ebfdf63c5756ec1676c5d22189a3db090");
pub const EXPECTED_V3_POOL_SLOT: FixedBytes<32> =
    fixed_bytes!("0xa297b7842bb27d1df6b58814cd9c628fad9558edf61186370124926f9ce1df5a");

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum FlowKind {
    Flash = 0,
    Settlement = 1,
    Unlock = 2,
    Composition = 3,
}

impl FlowKind {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::Flash),
            1 => Some(Self::Settlement),
            2 => Some(Self::Unlock),
            3 => Some(Self::Composition),
            _ => None,
        }
    }
}

pub fn identity_slot(kind: u8) -> Option<FixedBytes<32>> {
    match kind {
        0 => Some(EXPECTED_LENDER_SLOT),
        1 => Some(FLOW_ID_SLOT),
        2 => Some(CUMULATIVE_HASH_SLOT),
        3 => Some(EXECUTING_SLOT),
        4 => Some(EXPECTED_REACTOR_SLOT),
        5 => Some(EXPECTED_V3_POOL_SLOT),
        _ => None,
    }
}

pub fn reentrancy_slot(kind: FlowKind) -> FixedBytes<32> {
    match kind {
        FlowKind::Flash => keccak256(b"mev-arbitrum.TransientReentrancy.v1.flash"),
        FlowKind::Settlement => keccak256(b"mev-arbitrum.TransientReentrancy.v1.settlement"),
        FlowKind::Unlock => keccak256(b"mev-arbitrum.TransientReentrancy.v1.unlock"),
        FlowKind::Composition => keccak256(b"mev-arbitrum.TransientReentrancy.v1.composition"),
    }
}
