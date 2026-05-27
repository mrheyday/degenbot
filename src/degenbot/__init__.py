from .abi_adapter import (
    AbiAdapter,
    AbiBackend,
    AbiDecodeError,
    AbiEncodeError,
    AbiUnsupportedOperation,
    get_default_adapter,
    get_default_backend,
)
from .abi_adapter import decode as abi_decode
from .abi_adapter import decode_single as abi_decode_single
from .abi_adapter import encode as abi_encode
from .checksum_cache import get_checksum_address
from .config import settings
from .connection import (
    async_connection_manager,
    connection_manager,
    get_async_web3,
    get_web3,
    set_async_web3,
    set_web3,
)
from .degenbot_rs import (
    apply_gap_to_price_x96,
    decode_return_data,
    encode_function_call,
    get_function_selector,
    get_sqrt_ratio_at_tick,
    get_tick_at_sqrt_ratio,
    optimal_input_2pool,
    optimal_input_2pool_curve,
    optimal_input_2pool_v3,
    optimal_v2_frontrun_amount,
    synthetic_victim_amount_in,
    to_checksum_address,
    v2_mid_price_x96,
    v2_optimal_sandwich_size,
    v2_sandwich_max_size,
    v3_mid_price_x96,
)
from .dispatch import (
    DispatchAdapter,
    DispatchReceiptDict,
    compose_dispatch_envelope,
    submit_dispatch_envelope,
)
from .execution import (
    encode_compose_four_leg_calldata,
    encode_match_internal_calldata,
    encode_native_arb_calldata,
)
from .execution_engine import compose_engine_job
from .pipeline import (
    DeterministicPipeline,
    PipelineAction,
    PipelineCollector,
    PipelineConfig,
    PipelineConfigurationError,
    PipelineError,
    PipelineExecutor,
    PipelineFault,
    PipelineMetrics,
    PipelineStrategy,
)
from .version import __version__

# isort: split

from .adapters.config import DegenbotSettings, load_degenbot_settings
from .adapters.ipc import is_recognized_dex_kind
from .aerodrome import (
    AerodromeV2Pool,
    AerodromeV2PoolManager,
    AerodromeV2PoolState,
    AerodromeV3Pool,
    AerodromeV3PoolManager,
    AerodromeV3PoolState,
)
from .anvil_fork import AnvilFork
from .arbitrage import ArbitrageCalculationResult, UniswapCurveCycle, UniswapLpCycle
from .arbitrage.types import (
    CurveStableSwapPoolSwapAmounts,
    UniswapV2PoolSwapAmounts,
    UniswapV3PoolSwapAmounts,
    UniswapV4PoolSwapAmounts,
)
from .bot import BotOpportunity, BotScanConfig, DegenbotBot
from .camelot import CamelotLiquidityPool
from .chainlink import ChainlinkPriceContract
from .connection.ipc import DegenbotIpcServer
from .cow.models import Auction as CowAuction
from .cow.submitter import CompetitionSubmitter
from .curve import (
    CurveStableswapPool,
    CurveStableswapPoolSimulationResult,
    CurveStableswapPoolState,
    CurveStableSwapPoolStateUpdated,
)
from .decision.engine import DecisionEngine, RoutedDecision
from .decision.precedence import DecisionKind, compare_priority
from .decision.sandoo_ideas import SandooIdeaSignal
from .decision.types import (
    AggregatorQuote,
    DecisionContext,
    DecisionRoute,
    MatchCandidate,
    MatchPair,
)
from .erc20 import Erc20Token, Erc20TokenManager, EtherPlaceholder
from .flash.source_router import ExecutorFlashRoute, resolve_executor_flash_route
from .logging import logger
from .matching.encoder import MatchedTrade, encode_match_pair
from .matching.internal_matcher import find_best_match, find_matches
from .matching.unified_queue import UnifiedQueue
from .pancakeswap import (
    PancakeswapV2Pool,
    PancakeswapV2PoolManager,
    PancakeswapV3Pool,
    PancakeswapV3PoolManager,
)
from .registry import pool_registry, token_registry
from .simulation import SimulationResult, Simulator
from .strategies_coordinator.four_leg import FourLegPlan, FourLegStrategy
from .strategies_coordinator.internal_match import (
    InternalMatchPlan,
    InternalMatchStrategy,
)
from .strategies_coordinator.native_arb import NativeArbStrategy
from .strategies_coordinator.oracle_sandwich import (
    OracleSandwichPlan,
    OracleSandwichStrategy,
)
from .strategies_coordinator.sandwich import SandwichPlan, SandwichStrategy
from .strategies_coordinator.types import (
    DEX_KIND,
    FLASH_PROTOCOL,
    ComposeParams,
    MatchParams,
    NativeArbParams,
)
from .strategies_coordinator.types import (
    SwapStep as ContractSwapStep,
)
from .strategy_signals.bus import SignalBus
from .strategy_signals.correlation import CorrelationWindow
from .strategy_signals.ostium_oracle_gap import (
    OstiumOracleGapPayload,
    OstiumOracleGapSource,
)
from .sushiswap import (
    SushiswapV2Pool,
    SushiswapV2PoolManager,
    SushiswapV3Pool,
    SushiswapV3PoolManager,
)
from .swapbased import SwapbasedV2Pool, SwapbasedV2PoolManager
from .uniswap import (
    UniswapV2Pool,
    UniswapV2PoolExternalUpdate,
    UniswapV2PoolManager,
    UniswapV2PoolSimulationResult,
    UniswapV2PoolState,
    UniswapV3LiquiditySnapshot,
    UniswapV3Pool,
    UniswapV3PoolExternalUpdate,
    UniswapV3PoolManager,
    UniswapV3PoolSimulationResult,
    UniswapV3PoolState,
    UniswapV4LiquiditySnapshot,
    UniswapV4Pool,
    UniswapV4PoolExternalUpdate,
    UniswapV4PoolState,
)

__all__ = (
    "DEX_KIND",
    "FLASH_PROTOCOL",
    "AbiAdapter",
    "AbiBackend",
    "AbiDecodeError",
    "AbiEncodeError",
    "AbiUnsupportedOperation",
    "AerodromeV2Pool",
    "AerodromeV2PoolManager",
    "AerodromeV2PoolState",
    "AerodromeV3Pool",
    "AerodromeV3PoolManager",
    "AerodromeV3PoolState",
    "AggregatorQuote",
    "AnvilFork",
    "ArbitrageCalculationResult",
    "BotOpportunity",
    "BotScanConfig",
    "CamelotLiquidityPool",
    "ChainlinkPriceContract",
    "CompetitionSubmitter",
    "ComposeParams",
    "ContractSwapStep",
    "CorrelationWindow",
    "CowAuction",
    "CurveStableSwapPoolStateUpdated",
    "CurveStableSwapPoolSwapAmounts",
    "CurveStableswapPool",
    "CurveStableswapPoolSimulationResult",
    "CurveStableswapPoolState",
    "DecisionContext",
    "DecisionEngine",
    "DecisionKind",
    "DecisionRoute",
    "DegenbotBot",
    "DegenbotIpcServer",
    "DegenbotSettings",
    "DeterministicPipeline",
    "DispatchAdapter",
    "DispatchReceiptDict",
    "Erc20Token",
    "Erc20TokenManager",
    "EtherPlaceholder",
    "ExecutorFlashRoute",
    "FourLegPlan",
    "FourLegStrategy",
    "InternalMatchPlan",
    "InternalMatchStrategy",
    "MatchCandidate",
    "MatchPair",
    "MatchParams",
    "MatchedTrade",
    "NativeArbParams",
    "NativeArbStrategy",
    "OracleSandwichPlan",
    "OracleSandwichStrategy",
    "OstiumOracleGapPayload",
    "OstiumOracleGapSource",
    "PancakeswapV2Pool",
    "PancakeswapV2PoolManager",
    "PancakeswapV3Pool",
    "PancakeswapV3PoolManager",
    "PipelineAction",
    "PipelineCollector",
    "PipelineConfig",
    "PipelineConfigurationError",
    "PipelineError",
    "PipelineExecutor",
    "PipelineFault",
    "PipelineMetrics",
    "PipelineStrategy",
    "RoutedDecision",
    "SandooIdeaSignal",
    "SandwichPlan",
    "SandwichStrategy",
    "SignalBus",
    "SimulationResult",
    "Simulator",
    "SushiswapV2Pool",
    "SushiswapV2PoolManager",
    "SushiswapV3Pool",
    "SushiswapV3PoolManager",
    "SwapbasedV2Pool",
    "SwapbasedV2PoolManager",
    "UnifiedQueue",
    "UniswapCurveCycle",
    "UniswapLpCycle",
    "UniswapV2Pool",
    "UniswapV2PoolExternalUpdate",
    "UniswapV2PoolManager",
    "UniswapV2PoolSimulationResult",
    "UniswapV2PoolState",
    "UniswapV2PoolSwapAmounts",
    "UniswapV3LiquiditySnapshot",
    "UniswapV3Pool",
    "UniswapV3PoolExternalUpdate",
    "UniswapV3PoolManager",
    "UniswapV3PoolSimulationResult",
    "UniswapV3PoolState",
    "UniswapV3PoolSwapAmounts",
    "UniswapV4LiquiditySnapshot",
    "UniswapV4Pool",
    "UniswapV4PoolExternalUpdate",
    "UniswapV4PoolState",
    "UniswapV4PoolSwapAmounts",
    "__version__",
    "abi_decode",
    "abi_decode_single",
    "abi_encode",
    "apply_gap_to_price_x96",
    "async_connection_manager",
    "compare_priority",
    "compose_dispatch_envelope",
    "compose_engine_job",
    "connection_manager",
    "decode_return_data",
    "encode_compose_four_leg_calldata",
    "encode_function_call",
    "encode_match_internal_calldata",
    "encode_match_pair",
    "encode_native_arb_calldata",
    "find_best_match",
    "find_matches",
    "get_async_web3",
    "get_checksum_address",
    "get_default_adapter",
    "get_default_backend",
    "get_function_selector",
    "get_sqrt_ratio_at_tick",
    "get_tick_at_sqrt_ratio",
    "get_web3",
    "is_recognized_dex_kind",
    "load_degenbot_settings",
    "logger",
    "optimal_input_2pool",
    "optimal_input_2pool_curve",
    "optimal_input_2pool_v3",
    "optimal_v2_frontrun_amount",
    "pool_registry",
    "resolve_executor_flash_route",
    "set_async_web3",
    "set_web3",
    "settings",
    "submit_dispatch_envelope",
    "synthetic_victim_amount_in",
    "to_checksum_address",
    "token_registry",
    "v2_mid_price_x96",
    "v2_optimal_sandwich_size",
    "v2_sandwich_max_size",
    "v3_mid_price_x96",
)
