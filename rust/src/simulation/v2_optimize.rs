//! Analytical optimization for Uniswap V2 / Constant Product cycles.
//!
//! Implements the closed-form solution for optimal trade sizing in 2-pool
//! constant-product cycles, as described in Degen Code Part V.

use alloy::primitives::{U256, U512};
use eyre::{eyre, Result};

use crate::utils::u256::{isqrt_u512, narrow_u512};

/// Calculate the optimal input amount for a 2-pool Uniswap V2 arbitrage cycle.
///
/// Cycle: Token A -> (Pool 1) -> Token B -> (Pool 2) -> Token A
///
/// Parameters:
/// - `r_a1`: Token A reserves in Pool 1
/// - `r_b1`: Token B reserves in Pool 1
/// - `fee_bps1`: Fee in basis points for Pool 1 (e.g. 30)
/// - `r_b2`: Token B reserves in Pool 2
/// - `r_a2`: Token A reserves in Pool 2
/// - `fee_bps2`: Fee in basis points for Pool 2 (e.g. 30)
///
/// Formula:
/// x* = (sqrt(r_a1 * r_b1 * r_b2 * r_a2 * gamma1 * gamma2) - r_a1 * r_b2) / (r_b2 + r_b1 * gamma1)
/// where gamma = (10000 - fee_bps) / 10000
pub fn optimal_input_2pool(
    r_a1: U256,
    r_b1: U256,
    fee_bps1: u32,
    r_b2: U256,
    r_a2: U256,
    fee_bps2: u32,
) -> Result<U256> {
    if r_a1.is_zero() || r_b1.is_zero() || r_b2.is_zero() || r_a2.is_zero() {
        return Err(eyre!("v2_optimize: reserves must be non-zero"));
    }

    let g1_num = U512::from(10_000u64 - u64::from(fee_bps1));
    let g2_num = U512::from(10_000u64 - u64::from(fee_bps2));
    let d = U512::from(10_000u64);

    // Numerator parts
    // sqrt(r_a1 * r_b1 * r_b2 * r_a2 * g1_num * g2_num / (d * d))
    let k = U512::from(r_a1) * U512::from(r_b1) * U512::from(r_b2) * U512::from(r_a2) * g1_num * g2_num;
    let sqrt_k = isqrt_u512(k);
    
    // sqrt_k is in units of (token_a * token_b * d)
    // We need to divide by d to get back to token units for the subtraction
    let term1 = sqrt_k / d;
    let term2 = U512::from(r_a1) * U512::from(r_b2);

    if term1 <= term2 {
        // No profitable arbitrage exists
        return Ok(U256::ZERO);
    }

    let numerator = term1 - term2;

    // Denominator: r_b2 + r_b1 * gamma1 = r_b2 + (r_b1 * g1_num / d)
    // Multiply by d to clear denominator: (r_b2 * d + r_b1 * g1_num) / d
    let denom_scaled = U512::from(r_b2) * d + U512::from(r_b1) * g1_num;
    
    // Final x* = (numerator * d) / denom_scaled
    let result = (numerator * d) / denom_scaled;

    narrow_u512(result, "v2_optimize: optimal input overflows U256")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_optimal_input_profitable() {
        // Profitable case:
        // Pool 1: 100 A / 500 B (1 A buys ~5 B)
        // Pool 2: 500 B / 200 A (1 B buys ~0.4 A)
        // 1 A -> 5 B -> 2 A
        let r_a1 = U256::from(100u64);
        let r_b1 = U256::from(500u64);
        let r_b2 = U256::from(500u64);
        let r_a2 = U256::from(200u64);
        
        let x_star = optimal_input_2pool(r_a1, r_b1, 30, r_b2, r_a2, 30).unwrap();
        assert!(!x_star.is_zero());
        println!("x_star: {}", x_star);
        // Expected result should be positive
    }

    #[test]
    fn test_optimal_input_unprofitable() {
        // Pool 1: 100 A / 100 B, Pool 2: 100 B / 100 A
        // Fees will make this unprofitable
        let r_a1 = U256::from(100u64);
        let r_b1 = U256::from(100u64);
        let r_b2 = U256::from(100u64);
        let r_a2 = U256::from(100u64);
        
        let x_star = optimal_input_2pool(r_a1, r_b1, 30, r_b2, r_a2, 30).unwrap();
        assert!(x_star.is_zero());
    }
}
