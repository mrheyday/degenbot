# Stylus Porting Status

Source root: MEV-Arbitrum `contracts/src` at the time of port
(`../../../contracts/src` when this checkout is vendored under
`mev-arbitrum`).

The Solidity source tree contains 62 `.sol` files across auth, executors,
interfaces, libraries, POCs, reverse-engineered runtimes, and swappers.

This directory is degenbot's Stylus migration target. Ports here must compile with
`cargo stylus check` and must not be treated as executable replacements until
their ABI and behavior are proven against the Solidity source they replace.

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
- `libraries/MegaMEVOptimizationLib.sol` CLZ/CTZ, bit-length, power-of-two, sqrt, full-precision `fullMulDiv`/`fullMulDivUp`-style fixed-point helpers, and reserve-shape heuristics -> `core::mega_mev_optimization`
- `libraries/RouterRegistry.sol` -> `core::router_registry`
- `libraries/SingletonArrays.sol` -> `core::singleton_arrays`
- `libraries/StepMerging.sol` pure route-merge algorithm -> `core::step_merging`
- `libraries/TokenRiskFilter.sol` flag namespace, Arbitrum major-token whitelist, and deterministic probe-result reducer -> `core::token_risk_filter`
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
- Stylus upgrade invariants -> `core::upgrade_policy`

## Not Yet Semantically Ported

- `auth/*` storage mutation, signature recovery/validator calls, ERC-4337
  EntryPoint calls, token custody, and runtime external-call behavior not
  covered by the `auth_semantics` and `account_semantics` fragments
- `executors/*` runtime token-flow, EIP-1153 transient writes/reads, live
  flash-loan callbacks, external protocol calls, approvals/transfers, and
  balance/profit accounting beyond the static `executor_semantics` fragment
- `poc/CometLiquidatorPOC.sol` runtime Balancer/Comet/SwapRouter token-flow
  behavior beyond static plan validation
- `reverse/*`
- `swappers/MultiHopCaller.sol` Universal Router execution, Permit2 approvals,
  V2/V3/V4 quote calls, native rescue, and token-flow runtime behavior beyond
  the pure `swapper_semantics` fragment
- remaining executor/callback runtime calls and string-heavy dynamic codecs
- `libraries/FrontrunCalldata.sol` V3 approximate sizing and any above-tested-envelope arithmetic
- `libraries/LpTransferLib.sol` runtime ERC-20/ERC-721/ERC-6909 calls and return-value/revert normalization
- `libraries/TokenRiskFilter.sol` live token `staticcall` probes, cache storage, cache timestamp freshness, and external batch/cache ABI
- EIP-1153 `tload`/`tstore` runtime behavior behind `TransientStorage` and `TransientReentrancy`

Those contracts include authorization, callback, transient-storage, token-flow,
flash-loan, and external-protocol semantics. A mechanical rewrite without
contract-by-contract parity tests would be unsafe.
