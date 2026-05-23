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

- `libraries/BitMath.sol` -> `core::bit_math`
- `interfaces/IExecutor.sol` strategy struct ABI encoders for `executeNativeArb`,
  `executeOwnedSwaps`, `matchInternal`, `composeFourLeg`, `executeUniswapXFill`,
  `triggerCoWFlashLoanRouter`, and UniswapX `reactorCallback` callback data ->
  `core::executor_abi`
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
- Stylus upgrade invariants -> `core::upgrade_policy`

## Not Yet Semantically Ported

- `auth/*`
- `executors/*`
- `poc/*`
- `reverse/*`
- `swappers/*`
- remaining executor/callback runtime calls and string-heavy dynamic codecs
- `libraries/FrontrunCalldata.sol` V3 approximate sizing and any above-tested-envelope arithmetic
- `libraries/LpTransferLib.sol` runtime ERC-20/ERC-721/ERC-6909 calls and return-value/revert normalization
- `libraries/TokenRiskFilter.sol` live token `staticcall` probes, cache storage, cache timestamp freshness, and external batch/cache ABI
- EIP-1153 `tload`/`tstore` runtime behavior behind `TransientStorage` and `TransientReentrancy`

Those contracts include authorization, callback, transient-storage, token-flow,
flash-loan, and external-protocol semantics. A mechanical rewrite without
contract-by-contract parity tests would be unsafe.
