use stylus_sdk::alloy_primitives::{U256, U512};

use crate::bit_math;

pub const WAD_UINT: U256 = U256::from_limbs([1_000_000_000_000_000_000, 0, 0, 0]);
pub const Q96: U256 = U256::from_limbs([0, 0x0000_0001_0000_0000, 0, 0]);
pub const Q128: U256 = U256::from_limbs([0, 0, 1, 0]);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MathError {
    DivisionByZero,
    Overflow,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PowerOfTwoError {
    Overflow,
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
