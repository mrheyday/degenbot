# Debug Aave Verification

Use this command for Aave update, event processing, and exact-accounting verification failures.

## Core Premise

Database values and on-chain behavior are evidence. A local verification mismatch usually means
degenbot processing failed to model the contract path exactly.

## Process

1. Do not edit files during the investigation unless the user asks for a fix.
2. Capture issue metadata:

```bash
uv run python scripts/aave_debug_helper.py --market-id <MARKET_ID>
```

3. Run or inspect the failing update command. For fresh reproduction, prefer:

```bash
DEGENBOT_DEBUG=1 DEGENBOT_PROGRESS_BAR=0 uv run degenbot aave update
```

4. Search the output for:

```bash
grep -i "verification failed" <log>
grep -i "mismatch" <log>
grep -E "block [0-9]+" <log>
grep -iE "(supply|borrow|repay|withdraw|liquidation|mint_to_treasury)" <log>
```

5. Investigate the transaction with `evm-transaction-investigator` when a tx hash is known.
6. Compare against:
   - `docs/aave/`
   - `contract_reference/aave/`
   - prior reports in `debug/aave/`
   - relevant code under `src/degenbot/aave`

## Report Format

Create a report in `debug/aave/` only when the user asks for a durable report or the investigation
produces a new root cause.

```markdown
# [four digit id] - [issue title]

**Issue:** [brief title]
**Date:** [date]
**Symptom:** [error verbatim]
**Root Cause:** [technical explanation]
**Transaction Details:** [hash, block, type, user, asset]
**Fix:** [file, function, line-level target]
**Key Insight:** [lesson for future debugging]
**Refactoring:** [optional cleanup direction]
```

## Rules

- No tolerance-based verification fixes.
- Distinguish on-chain fact, database fact, and local hypothesis.
- Preserve all existing Aave invariants unless a test proves they are wrong.
