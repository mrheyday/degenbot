use stylus_sdk::alloy_primitives::{U256, U512};

use crate::bit_math;

pub const WAD_UINT: U256 = U256::from_limbs([1_000_000_000_000_000_000, 0, 0, 0]);
pub const Q96: U256 = U256::from_limbs([0, 0x0000_0001_0000_0000, 0, 0]);
pub const Q128: U256 = U256::from_limbs([0, 0, 1, 0]);
pub const V2_FEE_DENOMINATOR_BPS: U256 = U256::from_limbs([10_000, 0, 0, 0]);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MathError {
    DivisionByZero,
    Overflow,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PowerOfTwoError {
    Overflow,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum V2OptimizationError {
    EmptyPath,
    InvalidReserves,
    InvalidFeeBps(U256),
    Overflow,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct V2PoolHop {
    pub reserve_in: U256,
    pub reserve_out: U256,
    pub fee_bps: U256,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct V2CycleQuote {
    pub amount_in: U256,
    pub amount_out: U256,
    pub profit: U256,
}

pub fn clz256(x: U256) -> U256 {
    U256::from(bit_math::leading_zeros(x))
}

pub fn ctz256(x: U256) -> U256 {
    let limbs = x.into_limbs();
    for (index, limb) in limbs.iter().enumerate() {
        if *limb != 0 {
            return U256::from(index as u16 * 64 + limb.trailing_zeros() as u16);
        }
    }
    U256::from(256)
}

pub fn msb_index(x: U256) -> Option<U256> {
    bit_math::most_significant_bit(x).ok().map(U256::from)
}

pub fn lsb_index(x: U256) -> Option<U256> {
    if x == U256::ZERO {
        None
    } else {
        Some(ctz256(x))
    }
}

pub fn bit_length(x: U256) -> U256 {
    if x == U256::ZERO {
        U256::ZERO
    } else {
        U256::from(256) - clz256(x)
    }
}

pub fn log2_floor(x: U256) -> Option<U256> {
    msb_index(x)
}

pub fn log2_ceil(x: U256) -> Option<U256> {
    if x == U256::ZERO {
        return None;
    }
    let floor = msb_index(x)?;
    if is_power_of_two(x) {
        Some(floor)
    } else {
        Some(floor + U256::from(1))
    }
}

pub fn is_power_of_two(x: U256) -> bool {
    x != U256::ZERO && (x & (x - U256::from(1))) == U256::ZERO
}

pub fn floor_power_of_two(x: U256) -> U256 {
    match msb_index(x) {
        Some(index) => U256::from(1) << index.to::<usize>(),
        None => U256::ZERO,
    }
}

pub fn lowest_bit(x: U256) -> U256 {
    if x == U256::ZERO {
        U256::ZERO
    } else {
        U256::from(1) << ctz256(x).to::<usize>()
    }
}

pub fn next_power_of_two(x: U256) -> Result<U256, PowerOfTwoError> {
    if x <= U256::from(1) {
        return Ok(U256::from(1));
    }

    let previous = x - U256::from(1);
    let n = bit_length(previous);
    if n >= U256::from(256) {
        return Err(PowerOfTwoError::Overflow);
    }
    Ok(U256::from(1) << n.to::<usize>())
}

pub fn previous_power_of_two(x: U256) -> U256 {
    floor_power_of_two(x)
}

pub fn average(a: U256, b: U256) -> U256 {
    (a & b) + ((a ^ b) >> 1)
}

pub fn ceil_div(a: U256, b: U256) -> Result<U256, MathError> {
    if b == U256::ZERO {
        return Err(MathError::DivisionByZero);
    }
    if a == U256::ZERO {
        Ok(U256::ZERO)
    } else {
        Ok((a - U256::from(1)) / b + U256::from(1))
    }
}

pub fn clamp(x: U256, lo: U256, hi: U256) -> Option<U256> {
    if lo > hi {
        return None;
    }
    Some(x.max(lo).min(hi))
}

fn narrow_u512(value: U512) -> Result<U256, MathError> {
    if value > U512::from(U256::MAX) {
        Err(MathError::Overflow)
    } else {
        Ok(U256::from(value))
    }
}

pub fn mul_div(x: U256, y: U256, denominator: U256) -> Result<U256, MathError> {
    if denominator == U256::ZERO {
        return Err(MathError::DivisionByZero);
    }

    let product = U512::from(x)
        .checked_mul(U512::from(y))
        .ok_or(MathError::Overflow)?;
    narrow_u512(product / U512::from(denominator))
}

pub fn mul_div_up(x: U256, y: U256, denominator: U256) -> Result<U256, MathError> {
    if denominator == U256::ZERO {
        return Err(MathError::DivisionByZero);
    }

    let product = U512::from(x)
        .checked_mul(U512::from(y))
        .ok_or(MathError::Overflow)?;
    let denominator = U512::from(denominator);
    let quotient = product / denominator;
    if product % denominator == U512::ZERO {
        narrow_u512(quotient)
    } else {
        let rounded = quotient
            .checked_add(U512::from(1))
            .ok_or(MathError::Overflow)?;
        narrow_u512(rounded)
    }
}

pub fn mul_shr(x: U256, y: U256, shift: u8) -> Result<U256, MathError> {
    mul_div(x, y, U256::from(1) << shift as usize)
}

pub fn mul_shr_up(x: U256, y: U256, shift: u8) -> Result<U256, MathError> {
    mul_div_up(x, y, U256::from(1) << shift as usize)
}

pub fn mul_wad_down(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div(x, y, WAD_UINT)
}

pub fn mul_wad_up(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div_up(x, y, WAD_UINT)
}

pub fn div_wad_down(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div(x, WAD_UINT, y)
}

pub fn div_wad_up(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div_up(x, WAD_UINT, y)
}

pub fn mul_q96_down(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div(x, y, Q96)
}

pub fn mul_q96_up(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div_up(x, y, Q96)
}

pub fn div_q96_down(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div(x, Q96, y)
}

pub fn div_q96_up(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div_up(x, Q96, y)
}

pub fn mul_q128_down(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div(x, y, Q128)
}

pub fn mul_q128_up(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div_up(x, y, Q128)
}

pub fn div_q128_down(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div(x, Q128, y)
}

pub fn div_q128_up(x: U256, y: U256) -> Result<U256, MathError> {
    mul_div_up(x, Q128, y)
}

pub fn q96_to_wad(x: U256) -> Result<U256, MathError> {
    mul_div(x, WAD_UINT, Q96)
}

pub fn wad_to_q96(x: U256) -> Result<U256, MathError> {
    mul_div(x, Q96, WAD_UINT)
}

pub fn q128_to_wad(x: U256) -> Result<U256, MathError> {
    mul_div(x, WAD_UINT, Q128)
}

pub fn wad_to_q128(x: U256) -> Result<U256, MathError> {
    mul_div(x, Q128, WAD_UINT)
}

pub fn sqrt(x: U256) -> U256 {
    if x <= U256::from(1) {
        return x;
    }

    let shift = bit_length(x).to::<usize>().div_ceil(2);
    let mut z = U256::from(1) << shift;
    loop {
        let y = (z + x / z) >> 1;
        if y >= z {
            return z;
        }
        z = y;
    }
}

pub fn sqrt_up(x: U256) -> U256 {
    let z = sqrt(x);
    if z != U256::ZERO && z < x / z {
        z + U256::from(1)
    } else {
        z
    }
}

pub fn magnitude_bucket(x: U256) -> U256 {
    log2_floor(x).unwrap_or(U256::ZERO)
}

pub fn reserve_imbalance_bucket(reserve_a: U256, reserve_b: U256) -> U256 {
    if reserve_a == U256::ZERO || reserve_b == U256::ZERO {
        return U256::MAX;
    }
    let a = magnitude_bucket(reserve_a);
    let b = magnitude_bucket(reserve_b);
    if a > b { a - b } else { b - a }
}

pub fn reject_by_reserve_shape(
    reserve_a: U256,
    reserve_b: U256,
    min_bit_length: U256,
    max_imbalance_bucket: U256,
) -> bool {
    if bit_length(reserve_a) < min_bit_length {
        return true;
    }
    if bit_length(reserve_b) < min_bit_length {
        return true;
    }
    reserve_imbalance_bucket(reserve_a, reserve_b) > max_imbalance_bucket
}

pub fn liquidity_class(reserve_a: U256, reserve_b: U256) -> U256 {
    bit_length(reserve_a.min(reserve_b))
}

pub fn first_non_zero_byte_offset(x: U256) -> U256 {
    clz256(x) >> 3
}

pub fn leading_zero_bytes(x: U256) -> U256 {
    clz256(x) >> 3
}

pub fn v2_amount_out(hop: V2PoolHop, amount_in: U256) -> Result<U256, V2OptimizationError> {
    validate_v2_hop(hop)?;
    if amount_in == U256::ZERO {
        return Ok(U256::ZERO);
    }

    let fee_multiplier = V2_FEE_DENOMINATOR_BPS - hop.fee_bps;
    let amount_in_after_fee = checked_mul_u512(U512::from(amount_in), U512::from(fee_multiplier))?;
    let numerator = checked_mul_u512(amount_in_after_fee, U512::from(hop.reserve_out))?;
    let denominator = checked_add_u512(
        checked_mul_u512(
            U512::from(hop.reserve_in),
            U512::from(V2_FEE_DENOMINATOR_BPS),
        )?,
        amount_in_after_fee,
    )?;
    narrow_u512_to_v2(numerator / denominator)
}

pub fn v2_route_output(hops: &[V2PoolHop], amount_in: U256) -> Result<U256, V2OptimizationError> {
    if hops.is_empty() {
        return Err(V2OptimizationError::EmptyPath);
    }

    let mut amount = amount_in;
    for hop in hops {
        amount = v2_amount_out(*hop, amount)?;
    }
    Ok(amount)
}

pub fn optimal_v2_cycle_input(hops: &[V2PoolHop]) -> Result<U256, V2OptimizationError> {
    let (k, m, n) = v2_route_mobius_coefficients(hops)?;
    if k <= n || m == U512::ZERO {
        return Ok(U256::ZERO);
    }

    let target = checked_mul_u512(k, n)?;
    let root = sqrt_u512(target);
    if root <= n {
        return Ok(U256::ZERO);
    }

    narrow_u512_to_v2((root - n) / m)
}

pub fn optimal_v2_cycle_quote(hops: &[V2PoolHop]) -> Result<V2CycleQuote, V2OptimizationError> {
    let amount_in = optimal_v2_cycle_input(hops)?;
    if amount_in == U256::ZERO {
        return Ok(V2CycleQuote {
            amount_in,
            amount_out: U256::ZERO,
            profit: U256::ZERO,
        });
    }

    let amount_out = v2_route_output(hops, amount_in)?;
    Ok(V2CycleQuote {
        amount_in,
        amount_out,
        profit: amount_out.saturating_sub(amount_in),
    })
}

fn v2_route_mobius_coefficients(
    hops: &[V2PoolHop],
) -> Result<(U512, U512, U512), V2OptimizationError> {
    let Some(first) = hops.first().copied() else {
        return Err(V2OptimizationError::EmptyPath);
    };
    validate_v2_hop(first)?;

    let denominator = U512::from(V2_FEE_DENOMINATOR_BPS);
    let mut fee_multiplier = U512::from(V2_FEE_DENOMINATOR_BPS - first.fee_bps);
    let mut k = checked_mul_u512(fee_multiplier, U512::from(first.reserve_out))?;
    let mut m = fee_multiplier;
    let mut n = checked_mul_u512(denominator, U512::from(first.reserve_in))?;

    for hop in &hops[1..] {
        validate_v2_hop(*hop)?;
        fee_multiplier = U512::from(V2_FEE_DENOMINATOR_BPS - hop.fee_bps);
        let reserve_in_term = checked_mul_u512(denominator, U512::from(hop.reserve_in))?;
        let next_k = checked_mul_u512(
            checked_mul_u512(fee_multiplier, U512::from(hop.reserve_out))?,
            k,
        )?;
        let next_m = checked_add_u512(
            checked_mul_u512(fee_multiplier, k)?,
            checked_mul_u512(reserve_in_term, m)?,
        )?;
        let next_n = checked_mul_u512(reserve_in_term, n)?;
        k = next_k;
        m = next_m;
        n = next_n;
    }

    Ok((k, m, n))
}

fn validate_v2_hop(hop: V2PoolHop) -> Result<(), V2OptimizationError> {
    if hop.reserve_in == U256::ZERO || hop.reserve_out == U256::ZERO {
        return Err(V2OptimizationError::InvalidReserves);
    }
    if hop.fee_bps >= V2_FEE_DENOMINATOR_BPS {
        return Err(V2OptimizationError::InvalidFeeBps(hop.fee_bps));
    }
    Ok(())
}

fn sqrt_u512(x: U512) -> U512 {
    if x <= U512::from(1) {
        return x;
    }

    let mut z = x;
    loop {
        let y = (z + x / z) >> 1;
        if y >= z {
            return z;
        }
        z = y;
    }
}

fn narrow_u512_to_v2(value: U512) -> Result<U256, V2OptimizationError> {
    if value > U512::from(U256::MAX) {
        Err(V2OptimizationError::Overflow)
    } else {
        Ok(U256::from(value))
    }
}

fn checked_add_u512(a: U512, b: U512) -> Result<U512, V2OptimizationError> {
    a.checked_add(b).ok_or(V2OptimizationError::Overflow)
}

fn checked_mul_u512(a: U512, b: U512) -> Result<U512, V2OptimizationError> {
    a.checked_mul(b).ok_or(V2OptimizationError::Overflow)
}
