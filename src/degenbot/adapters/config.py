"""Runtime settings loaded from environment variables.

Source of truth for all driver configuration. Loaded once at process start;
do not mutate after construction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["debug", "info", "warning", "error", "critical"]


class EnvSettings(BaseSettings):
    """Base settings loaded from the project environment files."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class DegenbotSettings(EnvSettings):
    """Degenbot adapter settings that do not require solver signing secrets."""

    degenbot_source_path: Path = Field(
        default=Path("vendor/degenbot"),
        description="Pinned degenbot source checkout used by the IPC adapter.",
    )
    degenbot_ipc_socket_path: str = Field(
        # Unix socket only; the adapter refuses to replace non-socket paths.
        default="/tmp/degenbot.sock",  # noqa: S108
        description="Unix socket served by the degenbot IPC adapter and consumed by the TS coordinator.",
    )
    degenbot_heartbeat_interval_sec: int = Field(
        default=5,
        ge=1,
        description="Heartbeat interval for the degenbot IPC adapter.",
    )
    log_level: LogLevel = Field(default="info", description="structlog log level.")


class Settings(DegenbotSettings):
    """Driver settings.

    Loaded from environment variables (case-insensitive) with optional
    `.env` file support. Sensitive fields use `SecretStr` so they never
    leak via repr / structured logs.
    """

    # --- CoW protocol ---------------------------------------------------
    cow_api_base: HttpUrl = Field(
        default=HttpUrl("https://api.cow.fi/arbitrum_one"),
        description="Base URL for the CoW Protocol orderbook + competition API.",
    )
    cow_api_key: SecretStr | None = Field(
        default=None,
        description="Optional CoW API key for higher rate limits / private endpoints.",
    )
    cow_solver_address: str | None = Field(
        default=None,
        description="Legacy CoW solver address. Optional because the active CoW posture is quote-only.",
    )
    cow_solver_private_key: SecretStr | None = Field(
        default=None,
        description="Legacy solver EOA key. Unset in quote-only deployments; never required for CoW quoting.",
    )
    chain_id: int = Field(
        default=42161,
        ge=1,
        description="Execution chain id. Defaults to Arbitrum One.",
    )

    # --- Coordinator (TypeScript) ---------------------------------------
    coordinator_quote_url: HttpUrl = Field(
        default=HttpUrl("http://127.0.0.1:8080/quote"),
        description="TS coordinator's quote engine HTTP endpoint.",
    )

    # --- Solver Engine HTTP server --------------------------------------
    # The CoW driver POSTs auctions to /solve on this host:port; the same
    # port serves /health and /metrics. Per CoW deployment guidance, the
    # solver runs on a private network reachable only by the CoW driver
    # — operators must enforce ACLs.
    solver_engine_host: str = Field(
        default="0.0.0.0",  # noqa: S104 — bind-all is intentional inside the private mesh
        description="Bind host for the Solver Engine HTTP server.",
    )
    solver_engine_port: int = Field(
        default=8080,
        description="Bind port for the Solver Engine HTTP server (/solve, /health, /metrics).",
    )
    build_id: str = Field(
        default="dev",
        description="Build identifier surfaced on /health (git sha or container tag).",
    )

    # --- Observability (legacy, retained for back-compat) ---------------
    # Prometheus is now served via the Solver Engine HTTP app at /metrics
    # on `solver_engine_port`. `metrics_port` remains in the schema only
    # to avoid breaking deployments that still set it.
    metrics_port: int = Field(default=9091, description="Deprecated; use solver_engine_port.")

    # --- Infrastructure / REVM simulation -------------------------------
    arb_rpc_http: str | None = Field(
        default=None,
        description="Optional Arbitrum HTTP RPC endpoint; used by REVM when no dedicated simulation URL is set.",
    )
    revm_simulation_rpc_url: str | None = Field(
        default=None,
        description="Dedicated HTTP RPC endpoint backing exact REVM preflight simulation.",
    )
    revm_simulation_required: bool = Field(
        default=False,
        description="Reject executable strategy routes when exact REVM simulation is unavailable or fails.",
    )
    revm_simulation_from_address: str | None = Field(
        default=None,
        description="Delegatee/signer address used as msg.sender for REVM strategy calls.",
    )
    revm_simulation_seed_pools: str = Field(
        default="",
        description="Comma-separated pool addresses to warm into the REVM cache at startup.",
    )
    delegatees_initial: str | None = Field(
        default=None,
        description="Deployment-time delegatee CSV; first address is used as a simulation caller fallback.",
    )

    # --- Strategy flags -------------------------------------------------
    strategies_enabled: bool = Field(
        default=True,
        description="Global kill switch for all strategies.",
    )
    strategy_c_enabled: bool = Field(
        default=True,
        description="Legacy Pick C switch. In the current posture it controls CoW quote-only analysis.",
    )
    strategy_d3_enabled: bool = Field(
        default=True,
        description="Pick D3 pre-batch filter on top of Pick C bidding.",
    )
    strategy_internal_match_enabled: bool = Field(
        default=True,
        description="Enable Pick A internal matching.",
    )
    strategy_four_leg_enabled: bool = Field(
        default=True,
        description="Enable Pick B four-leg composition.",
    )
    strategy_native_arb_enabled: bool = Field(
        default=True,
        description="Enable Pick A native arbitrage.",
    )
    strategy_sandoo_ideas_enabled: bool = Field(
        default=True,
        description="Enable Sandoo idea scoring for native arb.",
    )
    strategy_oracle_sandwich_enabled: bool = Field(
        default=False,
        description="Enable S-5 oracle-update sandwich strategy.",
    )
    strategy_sandwich_enabled: bool = Field(
        default=False,
        description="Enable Pick S traditional sandwich strategy.",
    )
    strategy_timeboost_enabled: bool = Field(
        default=False,
        description="Enable Timeboost express-lane bid economics.",
    )

    # --- Timeboost state ------------------------------------------------
    timeboost_current_bid_wei: int = Field(default=0)
    timeboost_round_duration_sec: int = Field(default=60)
    timeboost_expected_ops_per_round: int = Field(default=10)
    timeboost_non_express_win_bps: int = Field(default=500)  # 5%
    estimated_gas_cost_wei: int = Field(default=500_000 * 10**8)  # 0.0005 ETH avg
    max_gas_price_gwei: float = Field(default=10.0, description="Max gas price in Gwei.")
    flash_loan_fee_wei: int = Field(default=0, description="Estimated flash loan fee in wei.")

    # --- On-chain components --------------------------------------------
    executor_address: str = Field(
        default="0x" + "0" * 40,
        description="Address of the on-chain Executor.sol.",
    )
    aave_v3_pool: str | None = Field(default=None)
    morpho_blue: str | None = Field(default=None)

    # --- Bidding policy -------------------------------------------------
    min_profit_usd: float = Field(
        default=2.0,
        ge=0.0,
        description=(
            "Minimum estimated profit (USD) for quote/provenance reporting. "
            "Quote-only mode never submits CoW solver solutions."
        ),
    )


def load_settings() -> Settings:
    """Construct Settings from the environment.

    Raises on missing required fields. Call once at process start.
    """
    return Settings()


def load_degenbot_settings() -> DegenbotSettings:
    """Construct degenbot adapter settings without requiring solver secrets."""
    return DegenbotSettings()
