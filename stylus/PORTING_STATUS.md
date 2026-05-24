# Stylus Porting Status

Source root: MEV-Arbitrum `contracts/src` at the time of port
(`../../../contracts/src` when this checkout is vendored under
`mev-arbitrum`).

The Solidity source tree contains 62 `.sol` files across auth, executors,
interfaces, libraries, POCs, reverse-engineered runtimes, and swappers.

This directory is degenbot's Stylus migration target. Ports here must compile with
`cargo stylus check` and must not be treated as executable replacements until
their ABI and behavior are proven against the Solidity source they replace.
The oversized `core` crate is the semantic parity harness; deployable surfaces
are split into activation-sized contracts such as `runtime_adapter/`,
`lp_transfer_adapter/`, `token_risk_adapter/`, and `pool_adapter/`.

## Ported Now

- Full source-coverage manifest for all 62 Solidity files across top-level,
  auth, executors, interfaces, libraries, POCs, reverse runtimes, and swappers
  -> `core::contract_manifest`
- `auth/PermissionToken.sol` pure capability-ID, parameter-gate, ERC-6909
  metadata, and selector invariants -> `core::auth_semantics`
- `auth/StrategyLedger.sol` pure strategy-ID, record-profit parameter gate,
  ERC-6909 metadata, and selector invariants -> `core::auth_semantics`
- `auth/validators/SessionValidator.sol` validator data shape, high-s boundary,
  expiry packing, and selector invariants -> `core::auth_semantics`
- `auth/validators/PasskeyValidator.sol` passkey pubkey/data shape and selector
  invariants -> `core::auth_semantics`
- `auth/MevSafe.sol`, `auth/MevBotDelegate.sol`, `auth/MevSafeFactory.sol`,
  `auth/paymaster/*`, and CoWShed account/proxy/storage surfaces: EntryPoint
  pins, ERC-1271 magic, EIP-7702 markers, ERC-6909 authority-selector blocks,
  multisig threshold gates, finance-plan preconditions, paymaster mode decoding
  and budget/pool guards, and CoWShed initialize/implementation/hook guards ->
  `core::account_semantics`
- `libraries/BitMath.sol` -> `core::bit_math`
- `interfaces/IExecutor.sol` strategy struct ABI encoders for `executeNativeArb`,
  `executeOwnedSwaps`, `matchInternal`, `composeFourLeg`, `executeUniswapXFill`,
  `triggerCoWFlashLoanRouter`, and UniswapX `reactorCallback` callback data ->
  `core::executor_abi`
- `executors/Executor.sol`, `executors/AtomicExecutor.sol`, and
  `executors/LiquidationExecutor.sol` selector invariants, enum ordinals,
  deadline gates, flash-source gates, callback shape checks, swap-step static
  checks, V3 path-shape checks, compressed-payload bounds, and liquidation
  pre-external-call plan guards -> `core::executor_semantics`
- `libraries/FrontrunCalldata.sol` selectors, UR command classifier, V3 packed path encode/parse, V2/Aave/V3-single common encoders and decoders, SwapRouter02 exactInput encoding/decoding, Universal Router execute/input decoders, V2 amount-out, and tested V2 frontrun sizing range -> `core::frontrun_calldata`
- `interfaces/FlashProtocol.sol`, `interfaces/IExecutor.sol` `DexKind` ordinals and strategy selectors, `interfaces/IPathFinder.sol` venue ordinals and selectors, ERC-8004 registry selectors/addresses, callback selectors from `interfaces/IFlashLoanInterfaces.sol`, `interfaces/IFlashLoanRouter.sol`, `interfaces/IReactorCallback.sol`, and `interfaces/IUniswapV4Hook.sol` hook flag constants -> `core::interface_surfaces`
- `interfaces/IPathFinder.sol` `Route` return ABI encoding for `(address[] path, uint8[] venues, uint24[] fees, uint256 amountOut)` -> `core::interface_surfaces`
- `libraries/LibUniswap.sol` -> `core::lib_uniswap`
- `libraries/LpTransferLib.sol` kind tags, selector constants, zero-parameter validation, and byte-exact forwarding payload builders -> `core::lp_transfer_lib`
- `libraries/LpTransferLib.sol` runtime Stylus adapter: guarded ERC-20 LP
  transfer, ERC-721 LP NFT `safeTransferFrom`, ERC-6909 claim transfer,
  ERC-6909 operator updates, no-code target rejection, and deterministic
  revert/false/malformed-return normalization -> deployable
  `lp_transfer_adapter/`
- `libraries/MegaMEVOptimizationLib.sol` CLZ/CTZ, bit-length, power-of-two, sqrt, full-precision `fullMulDiv`/`fullMulDivUp`-style fixed-point helpers, and reserve-shape heuristics -> `core::mega_mev_optimization`
- `libraries/RouterRegistry.sol` -> `core::router_registry`
- `libraries/SingletonArrays.sol` -> `core::singleton_arrays`
- `libraries/StepMerging.sol` pure route-merge algorithm -> `core::step_merging`
- `libraries/TokenRiskFilter.sol` flag namespace, Arbitrum major-token whitelist, and deterministic probe-result reducer -> `core::token_risk_filter`
- `libraries/TokenRiskFilter.sol` live Stylus token-risk adapter: major-token
  fast path, code-size fail-closed check, bounded `owner()`, `transfer`,
  blacklist-selector, and `paused()` static probes, cache storage, freshness
  checks, batch flags/safety ABI, and single-token dynamic `string[]` reason
  diagnostics -> deployable `token_risk_adapter/`
- `libraries/TokenStandardIds.sol` -> `core::token_standard_ids`
- `libraries/TransientStorage.sol` slot namespace -> `core::transient_slots`
- `libraries/TransientReentrancy.sol` flow-kind slot namespace -> `core::transient_slots`
- `poc/CompoundSiloLiquidationPOC.sol`,
  `poc/DolomiteGenericFlashLiquidationPOC.sol`,
  `poc/EulerV2EvcFlashLiquidationPOC.sol`,
  `poc/PendleLimitOrderV4ArbPOC.sol`, and
  `poc/PendlePySyAtomicArbPOC.sol` fail-closed verdict, selector, gate-count,
  evidence-bitmask, and hook-classification semantics -> `core::poc_fail_closed`
- `poc/CometLiquidatorPOC.sol` Arbitrum address constants, supported-Comet set,
  and pre-external-call static parameter validation -> `core::poc_fail_closed`
- `swappers/MultiHopCaller.sol` Arbitrum token/pool constants, selector
  invariants, depth-floor checks, slippage math, and pre-external-call
  entrypoint guards -> `core::swapper_semantics`
- Runtime execution-adapter proof for the live capital path: flash callback
  sender/initiator/transient-plan authentication, borrowed-token settlement,
  premium/min-profit accounting, idle-balance rejection, typed approval/call
  allowlist gates, and receipt digest binding for the accepted off-chain
  dispatch payload -> `core::runtime_adapter` and deployable
  `runtime_adapter/`
- Stylus upgrade invariants -> `core::upgrade_policy`

## Not Yet Semantically Ported

- `auth/*` storage mutation, signature recovery/validator calls, ERC-4337
  EntryPoint calls, token custody, and runtime external-call behavior not
  covered by the `auth_semantics` and `account_semantics` fragments
- `executors/*` host-level external protocol calls, actual Stylus
  `storage`/transient writes, ERC-20 approvals/transfers, and callback
  entrypoint bodies are not yet deployed as live replacements. Their runtime
  adapter invariants are now covered by `core::runtime_adapter`.
- `poc/CometLiquidatorPOC.sol` runtime Balancer/Comet/SwapRouter token-flow
  behavior beyond static plan validation
- `reverse/*`
- `swappers/MultiHopCaller.sol` Universal Router execution, Permit2 approvals,
  V2/V3/V4 quote calls, native rescue, and token-flow runtime behavior beyond
  the pure `swapper_semantics` fragment
- remaining executor/callback host calls and string-heavy dynamic codecs
- `libraries/FrontrunCalldata.sol` V3 approximate sizing and any above-tested-envelope arithmetic
- `libraries/TokenRiskFilter.sol` batch dynamic `RiskVerdict[]` return ABI;
  the deployable Stylus adapter exposes batch flags/safety for execution
  gating and exact single-token `string[]` diagnostics for operator inspection.
- EIP-1153 `tload`/`tstore` host behavior behind `TransientStorage` and
  `TransientReentrancy`; slot constants and runtime proof semantics are covered,
  but actual Stylus host writes are not yet a replacement deployment.
- Monolithic `core` activation on Arbitrum One currently exceeds EIP-170
  single-contract size and falls into the CLI fragment path. Production
  deployment must use split Stylus contracts until fragment activation is a
  verified target in the operator environment.

Those contracts include authorization, callback, transient-storage, token-flow,
flash-loan, and external-protocol semantics. A mechanical rewrite without
contract-by-contract parity tests would be unsafe.
