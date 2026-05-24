//! Source-coverage manifest for the Solidity-to-Stylus migration.
//!
//! This module is intentionally data-only: it pins every Solidity source file
//! that belongs to the migration surface and classifies the current Stylus
//! parity state. Runtime ports must graduate through contract-specific parity
//! tests before replacing the Solidity deployments.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum SourceCategory {
    TopLevel = 0,
    Auth = 1,
    Executor = 2,
    Interface = 3,
    Library = 4,
    Poc = 5,
    Reverse = 6,
    Swapper = 7,
}

impl SourceCategory {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::TopLevel),
            1 => Some(Self::Auth),
            2 => Some(Self::Executor),
            3 => Some(Self::Interface),
            4 => Some(Self::Library),
            5 => Some(Self::Poc),
            6 => Some(Self::Reverse),
            7 => Some(Self::Swapper),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum MigrationStatus {
    SourceManifested = 0,
    AbiParityPorted = 1,
    PureSemanticPorted = 2,
    RuntimePortRequired = 3,
    RuntimeAdapterProofPorted = 4,
}

impl MigrationStatus {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::SourceManifested),
            1 => Some(Self::AbiParityPorted),
            2 => Some(Self::PureSemanticPorted),
            3 => Some(Self::RuntimePortRequired),
            4 => Some(Self::RuntimeAdapterProofPorted),
            _ => None,
        }
    }
}

pub const TOP_LEVEL_SOURCES: &[&str] = &["contracts/src/PathFinder.sol"];

pub const AUTH_SOURCES: &[&str] = &[
    "contracts/src/auth/MevBotDelegate.sol",
    "contracts/src/auth/MevSafe.sol",
    "contracts/src/auth/MevSafeFactory.sol",
    "contracts/src/auth/PermissionToken.sol",
    "contracts/src/auth/StrategyLedger.sol",
    "contracts/src/auth/cowshed/CoWShed.sol",
    "contracts/src/auth/cowshed/CoWShedENS.sol",
    "contracts/src/auth/cowshed/CoWShedFactory.sol",
    "contracts/src/auth/cowshed/CoWShedProxy.sol",
    "contracts/src/auth/cowshed/CoWShedResolver.sol",
    "contracts/src/auth/cowshed/CoWShedStorage.sol",
    "contracts/src/auth/cowshed/ICOWAuthHook.sol",
    "contracts/src/auth/cowshed/LibCoWShedAuthenticatedHooks.sol",
    "contracts/src/auth/paymaster/BaseMevPaymaster.sol",
    "contracts/src/auth/paymaster/Eip7702Support.sol",
    "contracts/src/auth/paymaster/EntryPointAddresses.sol",
    "contracts/src/auth/paymaster/IAggregatorV3.sol",
    "contracts/src/auth/paymaster/MevPaymasterV6.sol",
    "contracts/src/auth/paymaster/MevPaymasterV7.sol",
    "contracts/src/auth/paymaster/MevPaymasterV8.sol",
    "contracts/src/auth/paymaster/MevPaymasterV9.sol",
    "contracts/src/auth/validators/IValidator.sol",
    "contracts/src/auth/validators/PasskeyValidator.sol",
    "contracts/src/auth/validators/SessionValidator.sol",
];

pub const AUTH_SEMANTIC_FRAGMENT_SOURCES: &[&str] = &[
    "contracts/src/auth/PermissionToken.sol",
    "contracts/src/auth/StrategyLedger.sol",
    "contracts/src/auth/validators/PasskeyValidator.sol",
    "contracts/src/auth/validators/SessionValidator.sol",
];

pub const AUTH_CONTROL_FRAGMENT_SOURCES: &[&str] = &[
    "contracts/src/auth/MevBotDelegate.sol",
    "contracts/src/auth/MevSafe.sol",
    "contracts/src/auth/MevSafeFactory.sol",
    "contracts/src/auth/cowshed/CoWShed.sol",
    "contracts/src/auth/cowshed/CoWShedProxy.sol",
    "contracts/src/auth/cowshed/CoWShedStorage.sol",
    "contracts/src/auth/paymaster/BaseMevPaymaster.sol",
    "contracts/src/auth/paymaster/Eip7702Support.sol",
    "contracts/src/auth/paymaster/EntryPointAddresses.sol",
    "contracts/src/auth/paymaster/MevPaymasterV6.sol",
    "contracts/src/auth/paymaster/MevPaymasterV7.sol",
    "contracts/src/auth/paymaster/MevPaymasterV8.sol",
    "contracts/src/auth/paymaster/MevPaymasterV9.sol",
];

pub const EXECUTOR_SOURCES: &[&str] = &[
    "contracts/src/executors/AtomicExecutor.sol",
    "contracts/src/executors/Executor.sol",
    "contracts/src/executors/LiquidationExecutor.sol",
];

pub const EXECUTOR_SEMANTIC_FRAGMENT_SOURCES: &[&str] = EXECUTOR_SOURCES;

pub const INTERFACE_SOURCES: &[&str] = &[
    "contracts/src/interfaces/FlashProtocol.sol",
    "contracts/src/interfaces/IERC3156FlashBorrower.sol",
    "contracts/src/interfaces/IExecutor.sol",
    "contracts/src/interfaces/IFlashLoanInterfaces.sol",
    "contracts/src/interfaces/IFlashLoanReceiver.sol",
    "contracts/src/interfaces/IFlashLoanRouter.sol",
    "contracts/src/interfaces/IIdentityRegistry.sol",
    "contracts/src/interfaces/IMorphoFlashLoanCallback.sol",
    "contracts/src/interfaces/IPathFinder.sol",
    "contracts/src/interfaces/IReactorCallback.sol",
    "contracts/src/interfaces/IReputationRegistry.sol",
    "contracts/src/interfaces/IUniswapV3FlashCallback.sol",
    "contracts/src/interfaces/IUniswapV4Hook.sol",
];

pub const LIBRARY_SOURCES: &[&str] = &[
    "contracts/src/libraries/BitMath.sol",
    "contracts/src/libraries/FrontrunCalldata.sol",
    "contracts/src/libraries/LibUniswap.sol",
    "contracts/src/libraries/LpTransferLib.sol",
    "contracts/src/libraries/MegaMEVOptimizationLib.sol",
    "contracts/src/libraries/RouterRegistry.sol",
    "contracts/src/libraries/SingletonArrays.sol",
    "contracts/src/libraries/StepMerging.sol",
    "contracts/src/libraries/TokenRiskFilter.sol",
    "contracts/src/libraries/TokenStandardIds.sol",
    "contracts/src/libraries/TransientReentrancy.sol",
    "contracts/src/libraries/TransientStorage.sol",
];

pub const POC_SOURCES: &[&str] = &[
    "contracts/src/poc/CometLiquidatorPOC.sol",
    "contracts/src/poc/CompoundSiloLiquidationPOC.sol",
    "contracts/src/poc/DolomiteGenericFlashLiquidationPOC.sol",
    "contracts/src/poc/EulerV2EvcFlashLiquidationPOC.sol",
    "contracts/src/poc/PendleLimitOrderV4ArbPOC.sol",
    "contracts/src/poc/PendlePySyAtomicArbPOC.sol",
];

pub const REVERSE_SOURCES: &[&str] = &[
    "contracts/src/reverse/JaredRuntimeReconstructed.sol",
    "contracts/src/reverse/JaredRuntimeReplica.sol",
];

pub const SWAPPER_SOURCES: &[&str] = &["contracts/src/swappers/MultiHopCaller.sol"];

pub const SWAPPER_SEMANTIC_FRAGMENT_SOURCES: &[&str] =
    &["contracts/src/swappers/MultiHopCaller.sol"];

pub const SOURCE_COUNT: usize = TOP_LEVEL_SOURCES.len()
    + AUTH_SOURCES.len()
    + EXECUTOR_SOURCES.len()
    + INTERFACE_SOURCES.len()
    + LIBRARY_SOURCES.len()
    + POC_SOURCES.len()
    + REVERSE_SOURCES.len()
    + SWAPPER_SOURCES.len();

pub const FULL_SOURCE_COVERAGE_COUNT: usize = 62;

#[must_use]
pub fn category_count(category: SourceCategory) -> usize {
    match category {
        SourceCategory::TopLevel => TOP_LEVEL_SOURCES.len(),
        SourceCategory::Auth => AUTH_SOURCES.len(),
        SourceCategory::Executor => EXECUTOR_SOURCES.len(),
        SourceCategory::Interface => INTERFACE_SOURCES.len(),
        SourceCategory::Library => LIBRARY_SOURCES.len(),
        SourceCategory::Poc => POC_SOURCES.len(),
        SourceCategory::Reverse => REVERSE_SOURCES.len(),
        SourceCategory::Swapper => SWAPPER_SOURCES.len(),
    }
}

#[must_use]
pub fn status_count(status: MigrationStatus) -> usize {
    match status {
        MigrationStatus::SourceManifested => SOURCE_COUNT,
        MigrationStatus::AbiParityPorted => INTERFACE_SOURCES.len() + EXECUTOR_SOURCES.len(),
        MigrationStatus::PureSemanticPorted => {
            LIBRARY_SOURCES.len()
                + (POC_SOURCES.len() - 1)
                + AUTH_SEMANTIC_FRAGMENT_SOURCES.len()
                + AUTH_CONTROL_FRAGMENT_SOURCES.len()
                + EXECUTOR_SEMANTIC_FRAGMENT_SOURCES.len()
                + SWAPPER_SEMANTIC_FRAGMENT_SOURCES.len()
        }
        MigrationStatus::RuntimePortRequired => {
            TOP_LEVEL_SOURCES.len()
                + AUTH_SOURCES.len()
                + EXECUTOR_SOURCES.len()
                + REVERSE_SOURCES.len()
                + SWAPPER_SOURCES.len()
                + 1
        }
        MigrationStatus::RuntimeAdapterProofPorted => EXECUTOR_SOURCES.len(),
    }
}

#[must_use]
pub fn has_full_source_coverage() -> bool {
    SOURCE_COUNT == FULL_SOURCE_COVERAGE_COUNT
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    #[test]
    fn manifest_covers_exact_solidity_source_count() {
        assert_eq!(FULL_SOURCE_COVERAGE_COUNT, SOURCE_COUNT);
        assert!(has_full_source_coverage());
    }

    #[test]
    fn category_counts_match_current_tree_shape() {
        assert_eq!(1, category_count(SourceCategory::TopLevel));
        assert_eq!(24, category_count(SourceCategory::Auth));
        assert_eq!(3, category_count(SourceCategory::Executor));
        assert_eq!(13, category_count(SourceCategory::Interface));
        assert_eq!(12, category_count(SourceCategory::Library));
        assert_eq!(6, category_count(SourceCategory::Poc));
        assert_eq!(2, category_count(SourceCategory::Reverse));
        assert_eq!(1, category_count(SourceCategory::Swapper));
    }

    #[test]
    fn manifest_has_no_duplicate_sources() {
        let mut seen = BTreeSet::new();
        for source in TOP_LEVEL_SOURCES
            .iter()
            .chain(AUTH_SOURCES)
            .chain(EXECUTOR_SOURCES)
            .chain(INTERFACE_SOURCES)
            .chain(LIBRARY_SOURCES)
            .chain(POC_SOURCES)
            .chain(REVERSE_SOURCES)
            .chain(SWAPPER_SOURCES)
        {
            assert!(seen.insert(*source), "duplicate source: {source}");
        }
        assert_eq!(FULL_SOURCE_COVERAGE_COUNT, seen.len());
    }

    #[test]
    fn status_counts_are_explicit_policy_not_completion_claims() {
        assert_eq!(62, status_count(MigrationStatus::SourceManifested));
        assert_eq!(16, status_count(MigrationStatus::AbiParityPorted));
        assert_eq!(38, status_count(MigrationStatus::PureSemanticPorted));
        assert_eq!(32, status_count(MigrationStatus::RuntimePortRequired));
        assert_eq!(3, status_count(MigrationStatus::RuntimeAdapterProofPorted));
    }
}
