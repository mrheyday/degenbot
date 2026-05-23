use stylus_sdk::alloy_primitives::U256;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BitMathError {
    ZeroInput,
}

pub fn leading_zeros(x: U256) -> u16 {
    let limbs = x.into_limbs();
    let mut index = limbs.len();
    while index > 0 {
        index -= 1;
        let limb = limbs[index];
        if limb != 0 {
            return ((limbs.len() - 1 - index) as u16) * 64 + limb.leading_zeros() as u16;
        }
    }
    256
}

pub fn most_significant_bit(x: U256) -> Result<u8, BitMathError> {
    if x == U256::ZERO {
        return Err(BitMathError::ZeroInput);
    }
    Ok((255 - leading_zeros(x)) as u8)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn leading_zeroes_matches_solidity_clz_boundaries() {
        assert_eq!(256, leading_zeros(U256::ZERO));
        assert_eq!(255, leading_zeros(U256::from(1)));
        assert_eq!(254, leading_zeros(U256::from(2)));
        assert_eq!(0, leading_zeros(U256::MAX));
        assert_eq!(0, leading_zeros(U256::from(1) << 255));
    }

    #[test]
    fn most_significant_bit_matches_solidity_indices() {
        assert_eq!(
            Err(BitMathError::ZeroInput),
            most_significant_bit(U256::ZERO)
        );
        assert_eq!(Ok(0), most_significant_bit(U256::from(1)));
        assert_eq!(Ok(1), most_significant_bit(U256::from(2)));
        assert_eq!(Ok(255), most_significant_bit(U256::MAX));
    }
}
