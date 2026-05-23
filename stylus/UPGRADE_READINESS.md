# Stylus Upgrade Readiness

This workspace uses Stylus as the migration target for `contracts/src`.
Contracts here are not production replacements until they pass ABI parity,
state-layout review, and upgrade-path tests against the Solidity source they
replace.

## Upgrade Pattern

- Prefer UUPS for singleton implementations.
- Prefer Beacon only when many proxies must share one implementation.
- Keep ERC-1967 proxy storage slots isolated from implementation state.
- Guard every upgrade call with explicit access control.
- Route `upgrade_to_and_call` only through proxy context.

## Stylus-Specific Requirements

- Implementation constructors set Stylus logic-context state only.
- Proxy initialization must write the implementation version into proxy storage.
- Existing storage fields must never be reordered, removed, or type-changed.
- New storage fields may only be appended.
- WASM implementations must be reactivated at least every 365 days and after
  Stylus protocol upgrades.

## Required Proof Before Promotion

- Local Arbitrum devnet deployment of V1 implementation and proxy.
- State written through V1 remains readable after upgrade to V2.
- Unauthorized callers cannot upgrade.
- `proxiable_uuid` matches the ERC-1967 implementation slot.
- ABI exported by Stylus matches the intended Solidity replacement surface.
- Contract-specific invariant tests pass for callback, token-flow, flash-loan,
  and account-abstraction paths.
