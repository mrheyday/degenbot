# DefiLlama Source Intelligence

Date: 2026-05-21

DefiLlama sources are useful for degenbot as discovery and validation evidence, not as executable
trading logic. This repo should mine them for protocol facts, chain names, adapter methodology, and
blacklists, then re-implement any required behavior in degenbot's Python/Rust code with local tests.

## Upstream Snapshots Inspected

- `DefiLlama/DefiLlama-Adapters` at `dc72d71466e0b3317ea519d9921f00c65a37e446`
- `DefiLlama/dimension-adapters` at `d3c4578b0dcf9d8aec7d5fe2fa902c895c25caaa`
- `DefiLlama/chainlist` at `fe3cd910a1a440aa3806664eeb4ef6f38a490349`
- `DefiLlama/defillama-app` at `1d0d09d181cc35ccf26a28fde8878f7ce0c6750d`

## What To Use

### TVL Adapters

`DefiLlama-Adapters` is the best source for:

- protocol contract addresses by chain;
- pool data provider, factory, market, vault, or gauge addresses;
- deployment `fromBlock` values;
- token, user, and market blacklists;
- helper ABI fragments;
- adapter methodology buckets: `tvl`, `staking`, `pool2`, `borrowed`, and `ownTokens`.

For degenbot, these facts belong in protocol adapters, source provenance records, strategy signal
inputs, and denylist candidates. They do not replace live chain reads.

### Dimension Adapters

`dimension-adapters` is the best source for:

- swap event signatures;
- factory discovery strategy;
- volume, fee, revenue, holder revenue, and supply-side revenue formulas;
- per-chain start times;
- pool/gauge/voter relationships for ve-style DEXs.

Use this for analytics and event-model validation. Re-implement formulas with integer-safe local
code before using them in a signal or accounting path.

### Chainlist

`chainlist` gives the canonical DefiLlama chain slug for a numeric chain id. The active mappings for
this project include:

| Chain ID | DefiLlama slug |
| --- | --- |
| 1 | `ethereum` |
| 10 | `optimism` |
| 56 | `binance` |
| 100 | `xdai` |
| 130 | `unichain` |
| 137 | `polygon` |
| 42161 | `arbitrum` |
| 8453 | `base` |
| 999 | `hyperliquid` |

Use the slug for DefiLlama API coin keys and adapter config lookup. Do not invent alternate slugs
such as `bnb` or `gnosis` when DefiLlama expects `binance` or `xdai`.

`constants/extraRpcs.js` is useful for RPC privacy review, but privacy statements are provider
claims. Validate chain id and operational behavior before using any RPC in a hot path.

### DefiLlama App

`defillama-app` is useful for public endpoint and UI behavior evidence. Examples:

- `src/containers/DimensionAdapters/api.ts` shows metrics and chart endpoint shapes under the v2
  server.
- `src/components/BuyOnLlamaswap.tsx` builds `https://swap.defillama.com` URLs for frontend buy
  links.
- `src/containers/LlamaAI/api.ts` shows suggested-question endpoint usage.

Treat these as analytics/UI references. `swap.defillama.com` is not a verified backend execution
API for degenbot.

## Import Boundary

Allowed:

- summarize facts with file and commit references;
- use addresses, event signatures, chain slugs, and blacklists as source evidence;
- add local tests proving degenbot behavior against the extracted facts;
- use adapter methodology to design local Python/Rust implementations.

Not allowed:

- copy GPL-licensed `defillama-app` code into degenbot;
- copy adapter implementations wholesale;
- use DefiLlama cached prices, TVL, or volumes as a live trade execution gate;
- ignore exploit comments, blacklists, or bad-debt exclusions;
- ship an address or event model without on-chain validation.

## Required Validation

For every protocol fact promoted into degenbot:

1. Record `repo@commit:path` as source provenance.
2. Verify contract addresses with `cast code <address> --rpc-url <RPC>`.
3. Normalize addresses with `cast --to-checksum-address <address>`.
4. Confirm chain id and slug.
5. Add or update a focused test in `tests/` or `rust/tests/`.
6. Keep DefiLlama-derived blacklists visible to the strategy or risk layer until intentionally
   accepted, transformed, or rejected.

## Local Reference Checkouts

Use:

```bash
bash scripts/defillama_reference_checkout.sh
```

The script creates sparse read-only working copies under `/private/tmp/defillama-reference/` for the
specific DefiLlama paths this repo cares about.
