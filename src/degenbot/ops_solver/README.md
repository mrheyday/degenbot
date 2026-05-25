# `driver.ops` — ApeWorx operational scripts

This directory hosts ApeWorx-based scripts that interact with the
deployed `Executor.sol` from Python. It is **not** on the solver hot
path — it must never be imported by `driver.main` or any module that
runs inside the auction loop.

## Why ApeWorx here?

Foundry is the canonical contract development framework per
`CLAUDE.md`. ApeWorx is the Python-side ops complement: it lets
operators run repeatable Python flows (load Executor at address, query
immutables, propose Safe txs) without re-implementing the Foundry
toolchain inside the solver process.

## Use cases

- **`deploy_verify.py`** — load the deployed `Executor` at
  `EXECUTOR_ADDRESS`, query its immutables (owner, settlement, reactor,
  whitelisted aggregator routers), assert against the expected config
  in `contracts/script/config/arbitrum-one.json`. Runs after every
  redeploy (ADR-015 immutable redeploy model). Concrete (not a scaffold)
  - exits non-zero on immutable drift, unexpected pause state, or missing
    delegatees listed in `DELEGATEE_ADDRESSES`.
- **`anomaly_response.py`** — on anomaly trigger (P&L deviation > 3σ,
  per `CLAUDE.md` kill switches), verify `owner == SAFE_ADDRESS`,
  check `paused()`, and emit a deterministic owner-Safe action payload
  for `Executor.pause()`. Concrete (not a scaffold) - no hot-key
  signing or broadcast path is embedded in the script.
- **`treasury_sweep.py`** — query the Executor's idle balance and
  propose a `rescueToken` Safe transaction.
- **`verify_liquidator.py`** — load the deployed `LiquidationExecutor`
  at `LIQUIDATOR_ADDRESS`, assert the hard-coded constants
  (`AAVE_V3_POOL`, `BALANCER_VAULT`, `UNIV3_ROUTER`) match the verified
  anchors at block 460,140,172, and verify owner == `SAFE_ADDRESS`,
  `paused == false`, plus any expected delegatees in
  `DELEGATEE_ADDRESSES`. Concrete (not a scaffold) — exits non-zero on
  mismatch so it can gate post-deploy CI. Set `OUTPUT_PATH` to archive a
  pure JSON report for `readiness_gate.py --strict-mainnet`.
- **`delegatee_verify.py`** — query `delegatees(address)` on both
  `Executor` and `LiquidationExecutor` for every expected bot signer in
  `DELEGATEE_ADDRESSES`. Concrete (not a scaffold) — exits non-zero if
  any signer is missing and writes the strict-mainnet evidence artifact
  when `OUTPUT_PATH` is set.
- **`readiness_gate.py`** — repository-local production-ready POC gate.
  It verifies the machine-readable execution workflows and strategy
  intelligence profiles: live workflows must have complete execution
  bottles and no blockers; gated workflows must carry concrete blockers
  and remediation. It exits zero for POC readiness and non-zero under
  `--strict-mainnet` until external deployment, owner, delegatee, and
  secrets-policy evidence gates are closed.

## Install

ApeWorx is an opt-in dependency group:

```sh
cd solver
uv sync --extra ops
```

This pulls in `eth-ape` and `ape-arbitrum`. **Note:** `eth-ape`'s
transitive `web3` requirement may conflict with the runtime pin
(`web3>=6.20,<8`) — verify the lock resolves cleanly before relying
on the ops scripts.

## Configuration

`ape-config.yaml` in this directory; minimal Arbitrum One setup. Chainstack is the standard
`ARB_RPC_HTTP` provider for repository fork checks; Ape's Alchemy network alias is retained for the
verification plugin path and can be overridden via env var.

## Run

```sh
EXECUTOR_ADDRESS=0x... \
DELEGATEE_ADDRESSES=0x...,0x... \
OUTPUT_PATH=../docs/runbooks/deployments/mainnet/executor-verification.json \
ape run driver/ops/deploy_verify.py --network arbitrum:mainnet:alchemy
```

Incident pause payload:

```sh
EXECUTOR_ADDRESS=0x... \
SAFE_ADDRESS=0x... \
ANOMALY_REASON="pnl deviation > 3 sigma" \
INCIDENT_ID=inc-2026-05-14-001 \
OUTPUT_PATH=./pause-plan.json \
ape run driver/ops/anomaly_response.py --network arbitrum:mainnet:alchemy
```

Optional overrides:

```sh
CONFIG_PATH=../contracts/script/config/arbitrum-one.json \
DELEGATEE_ADDRESSES=0x... \
EXECUTOR_ADDRESS=0x... \
OUTPUT_PATH=../docs/runbooks/deployments/mainnet/executor-verification.json \
ape run driver/ops/deploy_verify.py --network arbitrum:mainnet:alchemy
```

LiquidationExecutor verification:

```sh
LIQUIDATOR_ADDRESS=0x... \
SAFE_ADDRESS=0x... \
DELEGATEE_ADDRESSES=0x...,0x... \
OUTPUT_PATH=../docs/runbooks/deployments/mainnet/liquidation-executor-verification.json \
ape run driver/ops/verify_liquidator.py --network arbitrum:mainnet:alchemy
```

Delegatee-only verification:

```sh
EXECUTOR_ADDRESS=0x... \
LIQUIDATOR_ADDRESS=0x... \
DELEGATEE_ADDRESSES=0x...,0x... \
OUTPUT_PATH=../docs/runbooks/deployments/mainnet/delegatee-verification.json \
ape run driver/ops/delegatee_verify.py --network arbitrum:mainnet:alchemy
```

Production-ready POC gate:

```sh
cd ..
.venv/bin/python -m driver.ops.readiness_gate

# JSON report
.venv/bin/python -m driver.ops.readiness_gate --json

# Print every individual finding when investigating a failure.
.venv/bin/python -m driver.ops.readiness_gate --verbose

# Fails until Safe ownership, post-deploy verification, delegatee
# verification, and secrets-policy evidence gates are closed.
.venv/bin/python -m driver.ops.readiness_gate --strict-mainnet
```
