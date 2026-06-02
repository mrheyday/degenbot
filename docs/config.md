---
title: Configuration
category: cli
tags:
  - configuration
  - environment-variables
related_files:
  - src/degenbot/logging.py
  - src/degenbot/config.py
  - src/degenbot/cli/__init__.py
complexity: simple
---

# Configuration

## Environment Variables

### Debug Logging

| Variable | Values | Description |
|----------|--------|-------------|
| `DEGENBOT_DEBUG` | `1`, `true`, `yes` | Enable debug-level logging output globally |
| `DEGENBOT_DEBUG_FUNCTION_CALLS` | `1`, `true`, `yes` | Enable function call trace logging |
| `ALCHEMY_API_KEY` | Alchemy key | Default key for generated HTTP RPC, WSS, Bundler, and Gas Manager endpoints |
| `WEB3_ALCHEMY_API_KEY` | Alchemy key | Ape-compatible fallback when `ALCHEMY_API_KEY` is unset |
| `ALCHEMY_CHAIN_<chain_id>_NETWORK` | Alchemy network identifier | Override/add the Alchemy network slug for a chain, e.g. `ALCHEMY_CHAIN_42161_NETWORK=arb-mainnet` |
| `ALCHEMY_CHAIN_<chain_id>_ACCOUNT_ABSTRACTION` | `1`, `true`, `yes`, `on` | Enable Bundler/Gas Manager endpoint construction for a newly supported chain after confirming Alchemy AA support |

Set `DEGENBOT_DEBUG` before importing degenbot to see all `logger.debug()` messages throughout the codebase. This is useful for troubleshooting and development.

Set `DEGENBOT_DEBUG_FUNCTION_CALLS` to trace all function calls decorated with `@log_function_call`.

```bash
DEGENBOT_DEBUG=1 python my_script.py
```

### Alchemy Endpoint Fallback

If a chain is missing from the `[rpc]` table, degenbot builds an Alchemy HTTP RPC endpoint from
`ALCHEMY_API_KEY` or `WEB3_ALCHEMY_API_KEY`. The shared helper
`degenbot.provider.alchemy.alchemy_endpoint_bundle(chain_id)` returns the deterministic endpoint set
for the same key:

- `rpc_http`: `https://<network>.g.alchemy.com/v2/<key>`
- `rpc_ws`: `wss://<network>.g.alchemy.com/v2/<key>`
- `bundler`: same HTTP endpoint on supported AA chains, otherwise `None`
- `gas_manager`: same HTTP endpoint on supported AA chains, otherwise `None`
- `account_abstraction_supported`: whether Alchemy's SDK registry lists Bundler/Gas Manager support

Use `degenbot.provider.alchemy.alchemy_account_abstraction_supported(chain_id)` before routing
Bundler or Gas Manager calls. The RPC/WSS registry follows Alchemy's Node endpoint slugs, while
Account Abstraction support follows Alchemy's SDK chain registry. Direct Bundler or Gas Manager
endpoint construction raises `DegenbotValueError` on node-only chains.
CLI utilities can request a specific Alchemy service through
`degenbot.cli.utils.get_rpc_endpoint_from_config(chain_id=..., service=...)`; HTTP RPC keeps using
the `[rpc]` table first, WebSocket uses a configured WSS endpoint when present, and AA services use
the Alchemy fallback with the same fail-closed AA checks.

For a newly supported chain that is not in the built-in registry, set
`ALCHEMY_CHAIN_<chain_id>_NETWORK` or `ALCHEMY_NETWORK_<chain_id>` to Alchemy's network identifier.
For a chain newly added to Alchemy's Bundler/Gas Manager support, also set
`ALCHEMY_CHAIN_<chain_id>_ACCOUNT_ABSTRACTION=true`.

## Configuration File

Degenbot uses a TOML configuration file located at `~/.config/degenbot/config.toml`. It is created automatically on first use with default settings.

```toml
[rpc]
# Chain ID to RPC endpoint mapping
1 = "https://eth-mainnet.example.com"
8453 = "https://base-mainnet.example.com"

[database]
# SQLite database path (defaults to ~/.config/degenbot/degenbot.db)
path = "/path/to/degenbot.db"
```
