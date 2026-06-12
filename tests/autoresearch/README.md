# Autoresearch Tests

This folder is the canonical lane for contract-shape and gas-optimization experiments.

## Layout

- `AR_TASK_MANIFEST.md`: objective map for mixed-path AR targets.
- `test_*.py`: lane tests for V2/V3/V4 synthetic arbitrage scenarios.
- `_fake_arbitrage_world.py`: deterministic fake-world and executor helpers.

## Execution

- Run this lane only:
  - `just test-autoresearch`
- Keep benchmark output machine-readable by preserving:
  - `METRIC gas_used=<value>`

## Contract fixture

- `contracts/command_executor.vy` holds the Vyper fixture contract that the legacy lane
  originally exercised. Update both harness and contract together whenever shape
  assumptions change.

