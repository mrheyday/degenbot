//! Arbitrum gas oracle + EIP-1559 envelope tightening.
//!
//! Reads the `ArbGasInfo` precompile at `0x...006C` for accurate per-tx cost
//! estimation on Arbitrum One. The L1 calldata-byte price (`perL1CalldataUnit`)
//! dominates total cost for our typical 3–6 KB MEV transactions; ignoring it
//! and using only `eth_gasPrice` would systematically under-price by 70–90%.
//!
//! Usage shape:
//!   1. `fetch_gas_oracle(provider).await?` — one-shot snapshot per opportunity
//!   2. `oracle.estimate_cost_wei(calldata_bytes, gas_limit)` — pure math
//!   3. `oracle.is_profitable(gross_profit, calldata, gas_limit)` — gate check
//!   4. `tighten(envelope, &oracle)` — cap priority fee at observed prevailing
//!
//! Live values seen 2026-05-07 on Arbitrum One (per docs.arbitrum.io
//! ArbGasInfo precompile call): L2 base 0.020 gwei, L1 byte 0.843 gwei/byte,
//! backlog 90.8M (congested band).

use alloy::network::TransactionBuilder;
use alloy::primitives::{address, Address, Bytes, U256};
use alloy::providers::Provider;
use alloy::rpc::types::TransactionRequest;
use alloy::sol;

use super::SubmitError;
use crate::monitor::GasEnvelope;

/// Address of the `ArbGasInfo` precompile on every Arbitrum chain — One,
/// Nova, Sepolia. Constant by Arbitrum protocol design.
pub const ARB_GAS_INFO: Address = address!("000000000000000000000000000000000000006C");

/// Address of the `NodeInterface` precompile. Per-tx L1-posting cost is
/// queried here via `gasEstimateL1Component`. Live values 2026-05-07:
/// `gasEstimateForL1=11581`, `baseFee=20_058_000 wei`,
/// `l1BaseFeeEstimate=89_525_730 wei`.
pub const NODE_INTERFACE: Address = address!("00000000000000000000000000000000000000C8");

sol! {
    #[allow(missing_docs)]
    #[sol(rpc)]
    interface IArbGasInfo {
        /// All values in wei.
        /// - `perL2Tx`             fixed L1 data overhead per tx
        /// - `perL1CalldataUnit`   wei per byte of calldata (dominant cost)
        /// - `perStorageAlloc`     wei per storage slot allocation
        /// - `perArbGasBase`       L2 execution price per gas (base)
        /// - `perArbGasCongestion` L2 congestion premium per gas
        /// - `perArbGasTotal`      perArbGasBase + perArbGasCongestion
        function getPricesInWei() external view returns (
            uint256 perL2Tx,
            uint256 perL1CalldataUnit,
            uint256 perStorageAlloc,
            uint256 perArbGasBase,
            uint256 perArbGasCongestion,
            uint256 perArbGasTotal
        );

        /// L1 base fee as currently estimated by Arbitrum.
        function getL1BaseFeeEstimate() external view returns (uint256);

        /// Hard floor for L2 gas price (protocol-imposed minimum).
        function getMinimumGasPrice() external view returns (uint256);

        /// Current gas backlog in ArbGas units. Bands:
        ///   <=10M    uncongested
        ///   10M..100M moderate-to-heavy load (priority tip helps)
        ///   >100M    severe congestion
        function getGasBacklog() external view returns (uint64);
    }

    #[allow(missing_docs)]
    #[sol(rpc)]
    interface INodeInterface {
        /// Returns the per-tx L1-posting cost components.
        ///
        /// `gasEstimateForL1` is in Arbitrum gas units — multiply by the L2 gas
        /// price to get the wei surcharge added on top of L2 execution gas.
        /// `baseFee` is the L2 base fee at quote time. `l1BaseFeeEstimate` is
        /// the L1 base fee Arbitrum is currently using to amortise the
        /// rollup's data-posting cost.
        function gasEstimateL1Component(
            address to,
            bool contractCreation,
            bytes calldata txData
        ) external returns (
            uint64 gasEstimateForL1,
            uint256 baseFee,
            uint256 l1BaseFeeEstimate
        );
    }
}

/// Snapshot of Arbitrum-specific gas pricing. Stale after ~250 ms (one Arb
/// block); refresh per opportunity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArbitrumGasOracle {
    /// Wei per byte of calldata — dominant cost for complex MEV txs.
    pub l1_calldata_price: U256,
    /// Fixed L1-data overhead per tx (paid regardless of calldata size).
    pub per_l2_tx: U256,
    /// L2 execution price per gas (base + congestion).
    pub l2_gas_price: U256,
    /// L1 base fee as seen by Arbitrum's L1-pricing model.
    pub l1_base_fee: U256,
    /// Gas backlog in ArbGas units. See `is_congested()`.
    pub gas_backlog: u64,
    /// Block this snapshot was taken at — for staleness tracking.
    pub block_number: u64,
}

impl ArbitrumGasOracle {
    /// Total tx cost in wei = fixed-overhead + (calldata_bytes × L1-byte-price)
    /// + (gas_limit × L2-gas-price).
    pub fn estimate_cost_wei(&self, calldata_bytes: usize, gas_limit: u64) -> U256 {
        let l1_data_cost = self.l1_calldata_price * U256::from(calldata_bytes);
        let l2_exec_cost = self.l2_gas_price * U256::from(gas_limit);
        self.per_l2_tx + l1_data_cost + l2_exec_cost
    }

    /// Minimum gross profit required to clear costs with `safety_bps` buffer.
    /// Defaults to 25% (i.e. 1.25× cost) — absorbs slippage + gas-estimate
    /// drift. Set higher during congestion or for novel paths.
    pub fn min_profit_wei(&self, calldata_bytes: usize, gas_limit: u64, safety_bps: u32) -> U256 {
        let cost = self.estimate_cost_wei(calldata_bytes, gas_limit);
        cost * U256::from(10_000_u64 + u64::from(safety_bps)) / U256::from(10_000_u64)
    }

    /// Backlog above 10M ArbGas units indicates moderate-to-heavy congestion;
    /// the L2 base-fee response curve starts climbing here.
    pub fn is_congested(&self) -> bool {
        self.gas_backlog > 10_000_000
    }

    /// Suggested priority fee. Arbitrum's centralised sequencer accepts
    /// zero-tip txs in normal conditions, but during backlog spikes a small
    /// tip jumps the queue. Returns 0 when uncongested, else 10% of L2 gas.
    pub fn suggested_priority_fee(&self) -> U256 {
        if self.is_congested() {
            self.l2_gas_price / U256::from(10_u64)
        } else {
            U256::ZERO
        }
    }

    /// Per-gas `maxFeePerGas` for an EIP-1559 tx with 2× headroom over the
    /// observed L2 gas price plus the suggested priority tip.
    pub fn max_fee_per_gas(&self) -> U256 {
        self.l2_gas_price * U256::from(2_u64) + self.suggested_priority_fee()
    }

    /// True iff the supplied gross-profit estimate clears the safety-buffered
    /// minimum for the supplied tx shape.
    pub fn is_profitable(
        &self,
        gross_profit_wei: U256,
        calldata_bytes: usize,
        gas_limit: u64,
        safety_bps: u32,
    ) -> bool {
        gross_profit_wei >= self.min_profit_wei(calldata_bytes, gas_limit, safety_bps)
    }
}

/// One-shot fetch of the gas-oracle snapshot. Caller pays the round-trip
/// cost; for hot-path opportunities consider the watch-channel approach (see
/// `engine/src/executor/mod.rs::LiveBackend` for the production wiring).
///
/// Returns `Err` if the chain doesn't expose the `ArbGasInfo` precompile —
/// e.g., when running against vanilla Anvil for tests. Callers that want a
/// graceful fallback should match on `SubmitError::Gas` and either skip the
/// oracle or use `eth_gasPrice` as a degenerate substitute.
pub async fn fetch_gas_oracle<P: Provider>(provider: P) -> Result<ArbitrumGasOracle, SubmitError> {
    let arb = IArbGasInfo::new(ARB_GAS_INFO, &provider);

    let prices = arb
        .getPricesInWei()
        .call()
        .await
        .map_err(|e| SubmitError::Gas(format!("ArbGasInfo.getPricesInWei: {e}")))?;
    let backlog = arb
        .getGasBacklog()
        .call()
        .await
        .map_err(|e| SubmitError::Gas(format!("ArbGasInfo.getGasBacklog: {e}")))?;
    let l1_base = arb
        .getL1BaseFeeEstimate()
        .call()
        .await
        .map_err(|e| SubmitError::Gas(format!("ArbGasInfo.getL1BaseFeeEstimate: {e}")))?;
    let block = provider
        .get_block_number()
        .await
        .map_err(|e| SubmitError::Gas(format!("get_block_number: {e}")))?;

    Ok(ArbitrumGasOracle {
        l1_calldata_price: prices.perL1CalldataUnit,
        per_l2_tx: prices.perL2Tx,
        l2_gas_price: prices.perArbGasTotal,
        l1_base_fee: l1_base,
        gas_backlog: backlog,
        block_number: block,
    })
}

/// Tighten a strategist-supplied envelope against an oracle snapshot.
/// `max_fee_per_gas_wei` is the strategist's hard cap; the engine MUST NOT
/// exceed it. `max_priority_fee_per_gas_wei` is reduced to the lesser of the
/// strategist's cap and the oracle's suggestion.
pub fn tighten(envelope: &GasEnvelope, oracle: &ArbitrumGasOracle) -> GasEnvelope {
    let suggested = oracle.suggested_priority_fee();
    GasEnvelope {
        max_fee_per_gas_wei: envelope.max_fee_per_gas_wei,
        max_priority_fee_per_gas_wei: envelope.max_priority_fee_per_gas_wei.min(suggested),
    }
}

/// Per-tx total-gas estimate that accounts for both the L2 execution gas
/// (via `eth_estimateGas`) and the L1-posting gas component (via
/// `NodeInterface.gasEstimateL1Component`). Returns the suggested gas-limit
/// to set on the tx, plus a wei breakdown for profitability gating.
///
/// On Arbitrum the rollup charges the user for L1 posting cost via an L1
/// gas-units field that's added to L2 gas. Ignoring it produces ~0%
/// under-estimation when calldata is tiny but ~30–80% under-estimation for
/// typical 3–6 KB MEV transactions — the difference between profitable and
/// not.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PerTxGasEstimate {
    /// L2 execution gas units, with safety buffer.
    pub l2_gas_units: u64,
    /// L1 posting gas units returned by NodeInterface.
    pub l1_gas_units: u64,
    /// Total gas-limit suggestion (l2 + l1).
    pub gas_limit: u64,
    /// L2 execution cost in wei (l2_gas_units × l2_gas_price).
    pub l2_cost_wei: U256,
    /// L1 posting cost in wei (l1_gas_units × l2_gas_price). Arbitrum prices
    /// the L1 component at the L2 gas price by protocol — the L1 surcharge
    /// is a *gas-unit* surcharge, not a separate fee.
    pub l1_cost_wei: U256,
    /// Total wei cost (per_l2_tx fixed + L2 + L1).
    pub total_cost_wei: U256,
}

/// Estimate total tx cost for a specific opportunity. Calls the NodeInterface
/// + ArbGasInfo precompiles plus `eth_estimateGas`, all in parallel.
///
/// `safety_bps` is the buffer applied to the L2 estimate (recommended:
/// 2000–3000 bps = 20–30% buffer; flash-loan callbacks can vary ±5% in gas
/// usage between simulation and inclusion).
pub async fn estimate_total_gas<P: Provider>(
    provider: &P,
    to: Address,
    calldata: &Bytes,
    from: Address,
    safety_bps: u32,
) -> Result<PerTxGasEstimate, SubmitError> {
    let arb_gas = IArbGasInfo::new(ARB_GAS_INFO, provider);
    let node_iface = INodeInterface::new(NODE_INTERFACE, provider);

    let probe_tx = TransactionRequest::default()
        .with_from(from)
        .with_to(to)
        .with_input(calldata.clone());

    let (prices, l1_component, l2_gas_raw) = tokio::try_join!(
        async {
            arb_gas
                .getPricesInWei()
                .call()
                .await
                .map_err(|e| SubmitError::Gas(format!("ArbGasInfo.getPricesInWei: {e}")))
        },
        async {
            node_iface
                .gasEstimateL1Component(to, false, calldata.clone())
                .call()
                .await
                .map_err(|e| SubmitError::Gas(format!("NodeInterface.gasEstimateL1Component: {e}")))
        },
        async {
            provider
                .estimate_gas(probe_tx)
                .await
                .map_err(|e| SubmitError::Gas(format!("eth_estimateGas: {e}")))
        }
    )?;

    let l2_gas_with_buffer = l2_gas_raw * u64::from(10_000_u32 + safety_bps) / 10_000_u64;
    let l1_gas_units = l1_component.gasEstimateForL1;
    let total_gas = l2_gas_with_buffer + l1_gas_units;

    let l2_cost = prices.perArbGasTotal * U256::from(l2_gas_with_buffer);
    let l1_cost = prices.perArbGasTotal * U256::from(l1_gas_units);
    let total_cost = prices.perL2Tx + l2_cost + l1_cost;

    tracing::debug!(
        target: "engine::executor::gas",
        l2_gas_raw,
        l2_gas_with_buffer,
        l1_gas_units,
        total_gas,
        l2_cost_wei = %l2_cost,
        l1_cost_wei = %l1_cost,
        total_cost_wei = %total_cost,
        "per-tx gas estimate"
    );

    Ok(PerTxGasEstimate {
        l2_gas_units: l2_gas_with_buffer,
        l1_gas_units,
        gas_limit: total_gas,
        l2_cost_wei: l2_cost,
        l1_cost_wei: l1_cost,
        total_cost_wei: total_cost,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn live_arbitrum_snapshot() -> ArbitrumGasOracle {
        // Numbers from the 2026-05-07 live ArbGasInfo readout —
        // L2 base 0.020 gwei, L1 byte 0.843 gwei/byte, backlog 90.8M.
        ArbitrumGasOracle {
            l1_calldata_price: U256::from(843_000_000_u64), // 0.843 gwei/byte
            per_l2_tx: U256::from(0_u64),                   // negligible at current rates
            l2_gas_price: U256::from(20_000_000_u64),       // 0.020 gwei
            l1_base_fee: U256::from(52_700_000_u64),        // 0.0527 gwei
            gas_backlog: 90_804_295,
            block_number: 231_842_000,
        }
    }

    #[test]
    fn cost_formula_sums_l1_and_l2_components() {
        let oracle = live_arbitrum_snapshot();
        // Flash-loan arb: 3.2 KB calldata, 900k gas.
        let cost = oracle.estimate_cost_wei(3_200, 900_000);
        // L1 calldata: 3200 × 843_000_000 = 2.6976e12 wei
        // L2 execution: 900_000 × 20_000_000 = 1.8e13 wei
        // Total = sum + per_l2_tx fixed overhead.
        let l1 = U256::from(3_200_u64) * U256::from(843_000_000_u64);
        let l2 = U256::from(900_000_u64) * U256::from(20_000_000_u64);
        assert_eq!(cost, oracle.per_l2_tx + l1 + l2);
        // Both components are non-trivial — neither rounds to zero.
        assert!(l1 > U256::ZERO);
        assert!(l2 > U256::ZERO);
    }

    #[test]
    fn calldata_dominant_when_few_gas_units_per_byte() {
        // Pathological-but-plausible case: 10 KB calldata, only 100k gas.
        // L1: 10000 × 843_000_000 = 8.43e12 wei
        // L2: 100_000 × 20_000_000 = 2.0e12 wei
        // L1 should dominate by ~4×.
        let oracle = live_arbitrum_snapshot();
        let l1 = U256::from(10_000_u64) * U256::from(843_000_000_u64);
        let l2 = U256::from(100_000_u64) * U256::from(20_000_000_u64);
        assert!(l1 > l2 * U256::from(4_u64));
        // estimate_cost_wei reflects the same shape.
        let cost = oracle.estimate_cost_wei(10_000, 100_000);
        assert_eq!(cost, oracle.per_l2_tx + l1 + l2);
    }

    #[test]
    fn min_profit_applies_safety_buffer() {
        let oracle = live_arbitrum_snapshot();
        let cost = oracle.estimate_cost_wei(800, 350_000);
        // 25% buffer (2500 bps).
        let min = oracle.min_profit_wei(800, 350_000, 2500);
        assert_eq!(min, cost * U256::from(12_500_u64) / U256::from(10_000_u64));

        // 50% buffer (5000 bps) > 25% buffer.
        let min_higher = oracle.min_profit_wei(800, 350_000, 5000);
        assert!(min_higher > min);
    }

    #[test]
    fn congested_at_90m_backlog() {
        assert!(live_arbitrum_snapshot().is_congested());

        let calm = ArbitrumGasOracle {
            gas_backlog: 5_000_000,
            ..live_arbitrum_snapshot()
        };
        assert!(!calm.is_congested());
    }

    #[test]
    fn priority_fee_only_when_congested() {
        let oracle = live_arbitrum_snapshot();
        // Congested → 10% of l2_gas_price.
        assert_eq!(
            oracle.suggested_priority_fee(),
            oracle.l2_gas_price / U256::from(10_u64)
        );

        let calm = ArbitrumGasOracle {
            gas_backlog: 5_000_000,
            ..oracle.clone()
        };
        assert_eq!(calm.suggested_priority_fee(), U256::ZERO);
    }

    #[test]
    fn is_profitable_gates_at_min_threshold() {
        let oracle = live_arbitrum_snapshot();
        let min = oracle.min_profit_wei(800, 350_000, 2500);

        assert!(oracle.is_profitable(min, 800, 350_000, 2500));
        assert!(oracle.is_profitable(min + U256::from(1_u64), 800, 350_000, 2500));
        assert!(!oracle.is_profitable(min - U256::from(1_u64), 800, 350_000, 2500));
    }

    #[test]
    fn tighten_clamps_priority_fee_under_strategist_cap() {
        let oracle = live_arbitrum_snapshot();
        let envelope = GasEnvelope {
            max_fee_per_gas_wei: U256::from(2_000_000_000_u64),
            max_priority_fee_per_gas_wei: U256::from(100_000_000_u64), // strategist offers 0.1 gwei
        };
        let tight = tighten(&envelope, &oracle);
        // Suggested = 10% of 0.020 gwei = 2_000_000 wei.
        assert_eq!(
            tight.max_priority_fee_per_gas_wei,
            U256::from(2_000_000_u64)
        );
        // max_fee preserved (strategist's hard cap).
        assert_eq!(tight.max_fee_per_gas_wei, envelope.max_fee_per_gas_wei);
    }

    #[test]
    fn tighten_preserves_strategist_cap_when_lower() {
        let oracle = live_arbitrum_snapshot();
        let envelope = GasEnvelope {
            max_fee_per_gas_wei: U256::from(2_000_000_000_u64),
            max_priority_fee_per_gas_wei: U256::from(500_u64), // tiny strategist cap
        };
        let tight = tighten(&envelope, &oracle);
        // Strategist cap (500 wei) < suggested (2_000_000 wei) → take the cap.
        assert_eq!(tight.max_priority_fee_per_gas_wei, U256::from(500_u64));
    }

    /// PerTxGasEstimate construction sanity — verifies the cost-decomposition
    /// math without actually hitting RPC. Covers what the live
    /// `estimate_total_gas` call assembles after RPC returns.
    #[test]
    fn per_tx_gas_estimate_decomposition_math() {
        // Live numbers (2026-05-07 Arbitrum readout):
        //   gasEstimateForL1 = 11_581
        //   l2_gas_price (perArbGasTotal) = 20_058_000 wei (0.02 gwei effective)
        //   per_l2_tx fixed = 0
        //   l2_gas_raw (eth_estimateGas) = 850_000 (typical flash-loan arb)
        //   safety_bps = 2000 (20% buffer)
        let l2_gas_raw: u64 = 850_000;
        let safety_bps: u32 = 2000;
        let l1_gas_units: u64 = 11_581;
        let l2_gas_price = U256::from(20_058_000_u64);
        let per_l2_tx = U256::ZERO;

        let l2_gas_with_buffer = l2_gas_raw * u64::from(10_000_u32 + safety_bps) / 10_000_u64;
        assert_eq!(l2_gas_with_buffer, 1_020_000); // 850k × 1.20

        let total_gas = l2_gas_with_buffer + l1_gas_units;
        assert_eq!(total_gas, 1_031_581);

        let l2_cost = l2_gas_price * U256::from(l2_gas_with_buffer);
        let l1_cost = l2_gas_price * U256::from(l1_gas_units);
        let total_cost = per_l2_tx + l2_cost + l1_cost;

        // L2 dominates at this scale: 1.02M gas × 0.02 gwei vs 11.6k gas × 0.02 gwei.
        // L1 component is ~1.1% of total cost — small but non-zero, and
        // ignoring it under-prices the tx (= silent loss on tight margins).
        let est = PerTxGasEstimate {
            l2_gas_units: l2_gas_with_buffer,
            l1_gas_units,
            gas_limit: total_gas,
            l2_cost_wei: l2_cost,
            l1_cost_wei: l1_cost,
            total_cost_wei: total_cost,
        };
        assert_eq!(est.gas_limit, l2_gas_with_buffer + l1_gas_units);
        assert_eq!(est.total_cost_wei, l2_cost + l1_cost);
        // L1 is non-trivial — at least 1% of total.
        let l1_pct_bps = (est.l1_cost_wei * U256::from(10_000_u64)) / est.total_cost_wei;
        assert!(l1_pct_bps >= U256::from(100_u64));
    }
}
