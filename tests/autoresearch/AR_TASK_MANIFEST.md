# Autoresearch Task Manifest

## Canonical mixed-path objectives

Use these files as the baseline targets for AR loop setup and metric extraction.

- `test_v2_v2_v2_keep_stream.py`
  - Keep-stream v2 parser/dispatch harness baseline.
- `test_v2_v2_v2_zero_balance.py`
  - Zero-balance triangle arbitrage baseline.
- `test_v2_v4_v4.py`
  - V2→V4→V4 mixed callback slice.
- `test_v3_v3_v3.py`
  - V3→V3→V3 mixed callback slice.
- `test_v3_v4_v4.py`
  - V3→V4→V4 mixed callback slice.
- `test_v4_v2_v2.py`
  - V4→V2→V2 mixed callback slice.
- `test_v4_v2_v4.py`
  - V4→V2→V4 mixed callback slice.
- `test_v4_v3_v2.py`
  - V4→V3→V2 mixed callback slice.
- `test_v4_v3_v2_zero_balance.py`
  - V4→V3→V2 next objective: no executor pre-funded WETH, same callback ordering.
- `test_v4_v3_v3.py`
  - V4→V3→V3 mixed callback slice.
- `test_v4_v3_v4.py`
  - V4→V3→V4 mixed callback slice.
- `test_v4_v4_v4.py`
  - V4→V4→V4 mixed callback slice.

## Keep-stream variants

- `test_v4_v4_v4_keep_stream.py`
  - Keep-stream variant for V4→V4→V4 dispatch tests.

## Metric convention

- All benchmark/optimizing tests print a single machine-readable line:
  - `METRIC gas_used=<value>`
