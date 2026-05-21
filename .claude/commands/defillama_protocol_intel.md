# DefiLlama Protocol Intel

Use this command when adding or reviewing protocol intelligence from DefiLlama sources.

## Source Priority

1. `DefiLlama/DefiLlama-Adapters` for TVL adapter configs, helper ABIs, deployment blocks, and
   blacklists.
2. `DefiLlama/dimension-adapters` for DEX volume, fees, revenue, event signatures, and fee split
   methodology.
3. `DefiLlama/chainlist` for numeric chain id to DefiLlama slug and RPC privacy metadata.
4. `DefiLlama/defillama-app` for public API/UI usage patterns only.

## Workflow

1. Refresh or inspect the reference checkouts. The helper script prints and runs the sparse clone
   recipe:

```bash
bash scripts/defillama_reference_checkout.sh
```

2. Record upstream commit hashes:

```bash
git -C /private/tmp/defillama-reference/DefiLlama-Adapters rev-parse HEAD
git -C /private/tmp/defillama-reference/dimension-adapters rev-parse HEAD
git -C /private/tmp/defillama-reference/chainlist rev-parse HEAD
git -C /private/tmp/defillama-reference/defillama-app rev-parse HEAD
```

3. Extract facts:
   - protocol slug and category;
   - chain slug and chain id;
   - factory/router/pool/market/gauge/voter addresses;
   - `fromBlock` / start timestamp;
   - event ABI and topic;
   - blacklisted tokens, users, markets, and exploit comments;
   - helper ABI fragments.

4. Validate facts for degenbot use:
   - `cast code <address> --rpc-url <RPC>` for contracts;
   - `cast --to-checksum-address <address>` for EIP-55 normalization;
   - compare chain slug with `chainlist/constants/chainIds.js`;
   - keep exploit blacklists as denylist candidates until explicitly reviewed.

5. Place durable output in the right degenbot home:
   - protocol adapter or signal logic: `src/degenbot/<protocol>/` or
     `src/degenbot/strategy_signals/`;
   - Rust hot-path helper: `rust/src`;
   - durable rationale: `docs/architecture/` or protocol docs;
   - parent TypeScript/Solidity only when the parent repo owns the behavior.

## Report Template

```markdown
## DefiLlama Intel: [protocol]

### Upstream Snapshot
- DefiLlama-Adapters:
- dimension-adapters:
- chainlist:
- defillama-app:

### Extracted Facts
- Chain slug / chain id:
- Addresses:
- fromBlock / start:
- Event ABI / topic:
- Blacklists:

### Degenbot Plan
- target files:
- tests:
- validation commands:

### Boundaries
- analytics-only facts:
- not execution-backed:
- license constraints:
```

## Rules

- Do not copy adapter code into degenbot.
- Do not treat DefiLlama prices, TVL, or frontend routes as execution gates.
- Do not skip on-chain validation for addresses used in live processing.
- Do not hide unknown facts; record them as open questions.
