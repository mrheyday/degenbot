///Module containing a contract's types and functions.
/**

```solidity
library StepMerging {
    struct Hop { bytes32 dex; bytes32 fromToken; bytes32 toToken; uint256 amountIn; uint256 amountOut; uint256 gas; uint256 poolLiquidity; }
    struct MergedGroup { bytes32 signatureHash; uint256 mergedCount; uint256 mergedAmountAtIntermediate; uint256 mergedOutput; uint256 originalBestOutput; uint256 mergedGas; uint256 originalTotalGas; }
    struct Route { Hop[] hops; uint256 totalOutput; uint256 totalGas; }
}
```*/
#[allow(
    non_camel_case_types,
    non_snake_case,
    clippy::pub_underscore_fields,
    clippy::style,
    clippy::empty_structs_with_brackets
)]
pub mod StepMerging {
    use super::*;
    use alloy::sol_types as alloy_sol_types;
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**```solidity
struct Hop { bytes32 dex; bytes32 fromToken; bytes32 toToken; uint256 amountIn; uint256 amountOut; uint256 gas; uint256 poolLiquidity; }
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct Hop {
        #[allow(missing_docs)]
        pub dex: alloy::sol_types::private::FixedBytes<32>,
        #[allow(missing_docs)]
        pub fromToken: alloy::sol_types::private::FixedBytes<32>,
        #[allow(missing_docs)]
        pub toToken: alloy::sol_types::private::FixedBytes<32>,
        #[allow(missing_docs)]
        pub amountIn: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub amountOut: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub gas: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub poolLiquidity: alloy::sol_types::private::primitives::aliases::U256,
    }
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        #[doc(hidden)]
        #[allow(dead_code)]
        type UnderlyingSolTuple<'a> = (
            alloy::sol_types::sol_data::FixedBytes<32>,
            alloy::sol_types::sol_data::FixedBytes<32>,
            alloy::sol_types::sol_data::FixedBytes<32>,
            alloy::sol_types::sol_data::Uint<256>,
            alloy::sol_types::sol_data::Uint<256>,
            alloy::sol_types::sol_data::Uint<256>,
            alloy::sol_types::sol_data::Uint<256>,
        );
        #[doc(hidden)]
        type UnderlyingRustTuple<'a> = (
            alloy::sol_types::private::FixedBytes<32>,
            alloy::sol_types::private::FixedBytes<32>,
            alloy::sol_types::private::FixedBytes<32>,
            alloy::sol_types::private::primitives::aliases::U256,
            alloy::sol_types::private::primitives::aliases::U256,
            alloy::sol_types::private::primitives::aliases::U256,
            alloy::sol_types::private::primitives::aliases::U256,
        );
        #[cfg(test)]
        #[allow(dead_code, unreachable_patterns)]
        fn _type_assertion(
            _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
        ) {
            match _t {
                alloy_sol_types::private::AssertTypeEq::<
                    <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                >(_) => {}
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<Hop> for UnderlyingRustTuple<'_> {
            fn from(value: Hop) -> Self {
                (
                    value.dex,
                    value.fromToken,
                    value.toToken,
                    value.amountIn,
                    value.amountOut,
                    value.gas,
                    value.poolLiquidity,
                )
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<UnderlyingRustTuple<'_>> for Hop {
            fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                Self {
                    dex: tuple.0,
                    fromToken: tuple.1,
                    toToken: tuple.2,
                    amountIn: tuple.3,
                    amountOut: tuple.4,
                    gas: tuple.5,
                    poolLiquidity: tuple.6,
                }
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolValue for Hop {
            type SolType = Self;
        }
        #[automatically_derived]
        impl alloy_sol_types::private::SolTypeValue<Self> for Hop {
            #[inline]
            fn stv_to_tokens(&self) -> <Self as alloy_sol_types::SolType>::Token<'_> {
                (
                    <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::SolType>::tokenize(&self.dex),
                    <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::SolType>::tokenize(&self.fromToken),
                    <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::SolType>::tokenize(&self.toToken),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.amountIn),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.amountOut),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.gas),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.poolLiquidity),
                )
            }
            #[inline]
            fn stv_abi_encoded_size(&self) -> usize {
                if let Some(size) = <Self as alloy_sol_types::SolType>::ENCODED_SIZE {
                    return size;
                }
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_encoded_size(&tuple)
            }
            #[inline]
            fn stv_eip712_data_word(&self) -> alloy_sol_types::Word {
                <Self as alloy_sol_types::SolStruct>::eip712_hash_struct(self)
            }
            #[inline]
            fn stv_abi_encode_packed_to(
                &self,
                out: &mut alloy_sol_types::private::Vec<u8>,
            ) {
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_encode_packed_to(&tuple, out)
            }
            #[inline]
            fn stv_abi_packed_encoded_size(&self) -> usize {
                if let Some(size) = <Self as alloy_sol_types::SolType>::PACKED_ENCODED_SIZE {
                    return size;
                }
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_packed_encoded_size(&tuple)
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolType for Hop {
            type RustType = Self;
            type Token<'a> = <UnderlyingSolTuple<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SOL_NAME: &'static str = <Self as alloy_sol_types::SolStruct>::NAME;
            const ENCODED_SIZE: Option<usize> = <UnderlyingSolTuple<
                '_,
            > as alloy_sol_types::SolType>::ENCODED_SIZE;
            const PACKED_ENCODED_SIZE: Option<usize> = <UnderlyingSolTuple<
                '_,
            > as alloy_sol_types::SolType>::PACKED_ENCODED_SIZE;
            #[inline]
            fn valid_token(token: &Self::Token<'_>) -> bool {
                <UnderlyingSolTuple<'_> as alloy_sol_types::SolType>::valid_token(token)
            }
            #[inline]
            fn detokenize(token: Self::Token<'_>) -> Self::RustType {
                let tuple = <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::detokenize(token);
                <Self as ::core::convert::From<UnderlyingRustTuple<'_>>>::from(tuple)
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolStruct for Hop {
            const NAME: &'static str = "Hop";
            #[inline]
            fn eip712_root_type() -> alloy_sol_types::private::Cow<'static, str> {
                alloy_sol_types::private::Cow::Borrowed(
                    "Hop(bytes32 dex,bytes32 fromToken,bytes32 toToken,uint256 amountIn,uint256 amountOut,uint256 gas,uint256 poolLiquidity)",
                )
            }
            #[inline]
            fn eip712_components() -> alloy_sol_types::private::Vec<
                alloy_sol_types::private::Cow<'static, str>,
            > {
                alloy_sol_types::private::Vec::new()
            }
            #[inline]
            fn eip712_encode_type() -> alloy_sol_types::private::Cow<'static, str> {
                <Self as alloy_sol_types::SolStruct>::eip712_root_type()
            }
            #[inline]
            fn eip712_encode_data(&self) -> alloy_sol_types::private::Vec<u8> {
                [
                    <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.dex)
                        .0,
                    <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.fromToken)
                        .0,
                    <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.toToken)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.amountIn)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.amountOut)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.gas)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.poolLiquidity)
                        .0,
                ]
                    .concat()
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::EventTopic for Hop {
            #[inline]
            fn topic_preimage_length(rust: &Self::RustType) -> usize {
                0usize
                    + <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(&rust.dex)
                    + <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.fromToken,
                    )
                    + <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.toToken,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.amountIn,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.amountOut,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(&rust.gas)
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.poolLiquidity,
                    )
            }
            #[inline]
            fn encode_topic_preimage(
                rust: &Self::RustType,
                out: &mut alloy_sol_types::private::Vec<u8>,
            ) {
                out.reserve(
                    <Self as alloy_sol_types::EventTopic>::topic_preimage_length(rust),
                );
                <alloy::sol_types::sol_data::FixedBytes<
                    32,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(&rust.dex, out);
                <alloy::sol_types::sol_data::FixedBytes<
                    32,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.fromToken,
                    out,
                );
                <alloy::sol_types::sol_data::FixedBytes<
                    32,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.toToken,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.amountIn,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.amountOut,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(&rust.gas, out);
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.poolLiquidity,
                    out,
                );
            }
            #[inline]
            fn encode_topic(
                rust: &Self::RustType,
            ) -> alloy_sol_types::abi::token::WordToken {
                let mut out = alloy_sol_types::private::Vec::new();
                <Self as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    rust,
                    &mut out,
                );
                alloy_sol_types::abi::token::WordToken(
                    alloy_sol_types::private::keccak256(out),
                )
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**```solidity
struct MergedGroup { bytes32 signatureHash; uint256 mergedCount; uint256 mergedAmountAtIntermediate; uint256 mergedOutput; uint256 originalBestOutput; uint256 mergedGas; uint256 originalTotalGas; }
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct MergedGroup {
        #[allow(missing_docs)]
        pub signatureHash: alloy::sol_types::private::FixedBytes<32>,
        #[allow(missing_docs)]
        pub mergedCount: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub mergedAmountAtIntermediate: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub mergedOutput: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub originalBestOutput: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub mergedGas: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub originalTotalGas: alloy::sol_types::private::primitives::aliases::U256,
    }
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        #[doc(hidden)]
        #[allow(dead_code)]
        type UnderlyingSolTuple<'a> = (
            alloy::sol_types::sol_data::FixedBytes<32>,
            alloy::sol_types::sol_data::Uint<256>,
            alloy::sol_types::sol_data::Uint<256>,
            alloy::sol_types::sol_data::Uint<256>,
            alloy::sol_types::sol_data::Uint<256>,
            alloy::sol_types::sol_data::Uint<256>,
            alloy::sol_types::sol_data::Uint<256>,
        );
        #[doc(hidden)]
        type UnderlyingRustTuple<'a> = (
            alloy::sol_types::private::FixedBytes<32>,
            alloy::sol_types::private::primitives::aliases::U256,
            alloy::sol_types::private::primitives::aliases::U256,
            alloy::sol_types::private::primitives::aliases::U256,
            alloy::sol_types::private::primitives::aliases::U256,
            alloy::sol_types::private::primitives::aliases::U256,
            alloy::sol_types::private::primitives::aliases::U256,
        );
        #[cfg(test)]
        #[allow(dead_code, unreachable_patterns)]
        fn _type_assertion(
            _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
        ) {
            match _t {
                alloy_sol_types::private::AssertTypeEq::<
                    <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                >(_) => {}
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<MergedGroup> for UnderlyingRustTuple<'_> {
            fn from(value: MergedGroup) -> Self {
                (
                    value.signatureHash,
                    value.mergedCount,
                    value.mergedAmountAtIntermediate,
                    value.mergedOutput,
                    value.originalBestOutput,
                    value.mergedGas,
                    value.originalTotalGas,
                )
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<UnderlyingRustTuple<'_>> for MergedGroup {
            fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                Self {
                    signatureHash: tuple.0,
                    mergedCount: tuple.1,
                    mergedAmountAtIntermediate: tuple.2,
                    mergedOutput: tuple.3,
                    originalBestOutput: tuple.4,
                    mergedGas: tuple.5,
                    originalTotalGas: tuple.6,
                }
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolValue for MergedGroup {
            type SolType = Self;
        }
        #[automatically_derived]
        impl alloy_sol_types::private::SolTypeValue<Self> for MergedGroup {
            #[inline]
            fn stv_to_tokens(&self) -> <Self as alloy_sol_types::SolType>::Token<'_> {
                (
                    <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::SolType>::tokenize(&self.signatureHash),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.mergedCount),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(
                        &self.mergedAmountAtIntermediate,
                    ),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.mergedOutput),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.originalBestOutput),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.mergedGas),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.originalTotalGas),
                )
            }
            #[inline]
            fn stv_abi_encoded_size(&self) -> usize {
                if let Some(size) = <Self as alloy_sol_types::SolType>::ENCODED_SIZE {
                    return size;
                }
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_encoded_size(&tuple)
            }
            #[inline]
            fn stv_eip712_data_word(&self) -> alloy_sol_types::Word {
                <Self as alloy_sol_types::SolStruct>::eip712_hash_struct(self)
            }
            #[inline]
            fn stv_abi_encode_packed_to(
                &self,
                out: &mut alloy_sol_types::private::Vec<u8>,
            ) {
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_encode_packed_to(&tuple, out)
            }
            #[inline]
            fn stv_abi_packed_encoded_size(&self) -> usize {
                if let Some(size) = <Self as alloy_sol_types::SolType>::PACKED_ENCODED_SIZE {
                    return size;
                }
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_packed_encoded_size(&tuple)
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolType for MergedGroup {
            type RustType = Self;
            type Token<'a> = <UnderlyingSolTuple<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SOL_NAME: &'static str = <Self as alloy_sol_types::SolStruct>::NAME;
            const ENCODED_SIZE: Option<usize> = <UnderlyingSolTuple<
                '_,
            > as alloy_sol_types::SolType>::ENCODED_SIZE;
            const PACKED_ENCODED_SIZE: Option<usize> = <UnderlyingSolTuple<
                '_,
            > as alloy_sol_types::SolType>::PACKED_ENCODED_SIZE;
            #[inline]
            fn valid_token(token: &Self::Token<'_>) -> bool {
                <UnderlyingSolTuple<'_> as alloy_sol_types::SolType>::valid_token(token)
            }
            #[inline]
            fn detokenize(token: Self::Token<'_>) -> Self::RustType {
                let tuple = <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::detokenize(token);
                <Self as ::core::convert::From<UnderlyingRustTuple<'_>>>::from(tuple)
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolStruct for MergedGroup {
            const NAME: &'static str = "MergedGroup";
            #[inline]
            fn eip712_root_type() -> alloy_sol_types::private::Cow<'static, str> {
                alloy_sol_types::private::Cow::Borrowed(
                    "MergedGroup(bytes32 signatureHash,uint256 mergedCount,uint256 mergedAmountAtIntermediate,uint256 mergedOutput,uint256 originalBestOutput,uint256 mergedGas,uint256 originalTotalGas)",
                )
            }
            #[inline]
            fn eip712_components() -> alloy_sol_types::private::Vec<
                alloy_sol_types::private::Cow<'static, str>,
            > {
                alloy_sol_types::private::Vec::new()
            }
            #[inline]
            fn eip712_encode_type() -> alloy_sol_types::private::Cow<'static, str> {
                <Self as alloy_sol_types::SolStruct>::eip712_root_type()
            }
            #[inline]
            fn eip712_encode_data(&self) -> alloy_sol_types::private::Vec<u8> {
                [
                    <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.signatureHash)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.mergedCount)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(
                            &self.mergedAmountAtIntermediate,
                        )
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.mergedOutput)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(
                            &self.originalBestOutput,
                        )
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.mergedGas)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(
                            &self.originalTotalGas,
                        )
                        .0,
                ]
                    .concat()
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::EventTopic for MergedGroup {
            #[inline]
            fn topic_preimage_length(rust: &Self::RustType) -> usize {
                0usize
                    + <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.signatureHash,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.mergedCount,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.mergedAmountAtIntermediate,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.mergedOutput,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.originalBestOutput,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.mergedGas,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.originalTotalGas,
                    )
            }
            #[inline]
            fn encode_topic_preimage(
                rust: &Self::RustType,
                out: &mut alloy_sol_types::private::Vec<u8>,
            ) {
                out.reserve(
                    <Self as alloy_sol_types::EventTopic>::topic_preimage_length(rust),
                );
                <alloy::sol_types::sol_data::FixedBytes<
                    32,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.signatureHash,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.mergedCount,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.mergedAmountAtIntermediate,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.mergedOutput,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.originalBestOutput,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.mergedGas,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.originalTotalGas,
                    out,
                );
            }
            #[inline]
            fn encode_topic(
                rust: &Self::RustType,
            ) -> alloy_sol_types::abi::token::WordToken {
                let mut out = alloy_sol_types::private::Vec::new();
                <Self as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    rust,
                    &mut out,
                );
                alloy_sol_types::abi::token::WordToken(
                    alloy_sol_types::private::keccak256(out),
                )
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**```solidity
struct Route { Hop[] hops; uint256 totalOutput; uint256 totalGas; }
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct Route {
        #[allow(missing_docs)]
        pub hops: alloy::sol_types::private::Vec<
            <Hop as alloy::sol_types::SolType>::RustType,
        >,
        #[allow(missing_docs)]
        pub totalOutput: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub totalGas: alloy::sol_types::private::primitives::aliases::U256,
    }
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        #[doc(hidden)]
        #[allow(dead_code)]
        type UnderlyingSolTuple<'a> = (
            alloy::sol_types::sol_data::Array<Hop>,
            alloy::sol_types::sol_data::Uint<256>,
            alloy::sol_types::sol_data::Uint<256>,
        );
        #[doc(hidden)]
        type UnderlyingRustTuple<'a> = (
            alloy::sol_types::private::Vec<<Hop as alloy::sol_types::SolType>::RustType>,
            alloy::sol_types::private::primitives::aliases::U256,
            alloy::sol_types::private::primitives::aliases::U256,
        );
        #[cfg(test)]
        #[allow(dead_code, unreachable_patterns)]
        fn _type_assertion(
            _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
        ) {
            match _t {
                alloy_sol_types::private::AssertTypeEq::<
                    <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                >(_) => {}
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<Route> for UnderlyingRustTuple<'_> {
            fn from(value: Route) -> Self {
                (value.hops, value.totalOutput, value.totalGas)
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<UnderlyingRustTuple<'_>> for Route {
            fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                Self {
                    hops: tuple.0,
                    totalOutput: tuple.1,
                    totalGas: tuple.2,
                }
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolValue for Route {
            type SolType = Self;
        }
        #[automatically_derived]
        impl alloy_sol_types::private::SolTypeValue<Self> for Route {
            #[inline]
            fn stv_to_tokens(&self) -> <Self as alloy_sol_types::SolType>::Token<'_> {
                (
                    <alloy::sol_types::sol_data::Array<
                        Hop,
                    > as alloy_sol_types::SolType>::tokenize(&self.hops),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.totalOutput),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.totalGas),
                )
            }
            #[inline]
            fn stv_abi_encoded_size(&self) -> usize {
                if let Some(size) = <Self as alloy_sol_types::SolType>::ENCODED_SIZE {
                    return size;
                }
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_encoded_size(&tuple)
            }
            #[inline]
            fn stv_eip712_data_word(&self) -> alloy_sol_types::Word {
                <Self as alloy_sol_types::SolStruct>::eip712_hash_struct(self)
            }
            #[inline]
            fn stv_abi_encode_packed_to(
                &self,
                out: &mut alloy_sol_types::private::Vec<u8>,
            ) {
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_encode_packed_to(&tuple, out)
            }
            #[inline]
            fn stv_abi_packed_encoded_size(&self) -> usize {
                if let Some(size) = <Self as alloy_sol_types::SolType>::PACKED_ENCODED_SIZE {
                    return size;
                }
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_packed_encoded_size(&tuple)
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolType for Route {
            type RustType = Self;
            type Token<'a> = <UnderlyingSolTuple<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SOL_NAME: &'static str = <Self as alloy_sol_types::SolStruct>::NAME;
            const ENCODED_SIZE: Option<usize> = <UnderlyingSolTuple<
                '_,
            > as alloy_sol_types::SolType>::ENCODED_SIZE;
            const PACKED_ENCODED_SIZE: Option<usize> = <UnderlyingSolTuple<
                '_,
            > as alloy_sol_types::SolType>::PACKED_ENCODED_SIZE;
            #[inline]
            fn valid_token(token: &Self::Token<'_>) -> bool {
                <UnderlyingSolTuple<'_> as alloy_sol_types::SolType>::valid_token(token)
            }
            #[inline]
            fn detokenize(token: Self::Token<'_>) -> Self::RustType {
                let tuple = <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::detokenize(token);
                <Self as ::core::convert::From<UnderlyingRustTuple<'_>>>::from(tuple)
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolStruct for Route {
            const NAME: &'static str = "Route";
            #[inline]
            fn eip712_root_type() -> alloy_sol_types::private::Cow<'static, str> {
                alloy_sol_types::private::Cow::Borrowed(
                    "Route(Hop[] hops,uint256 totalOutput,uint256 totalGas)",
                )
            }
            #[inline]
            fn eip712_components() -> alloy_sol_types::private::Vec<
                alloy_sol_types::private::Cow<'static, str>,
            > {
                let mut components = alloy_sol_types::private::Vec::with_capacity(1);
                components.push(<Hop as alloy_sol_types::SolStruct>::eip712_root_type());
                components
                    .extend(<Hop as alloy_sol_types::SolStruct>::eip712_components());
                components
            }
            #[inline]
            fn eip712_encode_data(&self) -> alloy_sol_types::private::Vec<u8> {
                [
                    <alloy::sol_types::sol_data::Array<
                        Hop,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.hops)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.totalOutput)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.totalGas)
                        .0,
                ]
                    .concat()
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::EventTopic for Route {
            #[inline]
            fn topic_preimage_length(rust: &Self::RustType) -> usize {
                0usize
                    + <alloy::sol_types::sol_data::Array<
                        Hop,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(&rust.hops)
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.totalOutput,
                    )
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.totalGas,
                    )
            }
            #[inline]
            fn encode_topic_preimage(
                rust: &Self::RustType,
                out: &mut alloy_sol_types::private::Vec<u8>,
            ) {
                out.reserve(
                    <Self as alloy_sol_types::EventTopic>::topic_preimage_length(rust),
                );
                <alloy::sol_types::sol_data::Array<
                    Hop,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.hops,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.totalOutput,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.totalGas,
                    out,
                );
            }
            #[inline]
            fn encode_topic(
                rust: &Self::RustType,
            ) -> alloy_sol_types::abi::token::WordToken {
                let mut out = alloy_sol_types::private::Vec::new();
                <Self as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    rust,
                    &mut out,
                );
                alloy_sol_types::abi::token::WordToken(
                    alloy_sol_types::private::keccak256(out),
                )
            }
        }
    };
    use alloy::contract as alloy_contract;
    /**Creates a new wrapper around an on-chain [`StepMerging`](self) contract instance.

See the [wrapper's documentation](`StepMergingInstance`) for more details.*/
    #[inline]
    pub const fn new<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    >(
        address: alloy_sol_types::private::Address,
        __provider: P,
    ) -> StepMergingInstance<P, N> {
        StepMergingInstance::<P, N>::new(address, __provider)
    }
    /**A [`StepMerging`](self) instance.

Contains type-safe methods for interacting with an on-chain instance of the
[`StepMerging`](self) contract located at a given `address`, using a given
provider `P`.

If the contract bytecode is available (see the [`sol!`](alloy_sol_types::sol!)
documentation on how to provide it), the `deploy` and `deploy_builder` methods can
be used to deploy a new instance of the contract.

See the [module-level documentation](self) for all the available methods.*/
    #[derive(Clone)]
    pub struct StepMergingInstance<P, N = alloy_contract::private::Ethereum> {
        address: alloy_sol_types::private::Address,
        provider: P,
        _network: ::core::marker::PhantomData<N>,
    }
    #[automatically_derived]
    impl<P, N> ::core::fmt::Debug for StepMergingInstance<P, N> {
        #[inline]
        fn fmt(&self, f: &mut ::core::fmt::Formatter<'_>) -> ::core::fmt::Result {
            f.debug_tuple("StepMergingInstance").field(&self.address).finish()
        }
    }
    /// Instantiation and getters/setters.
    impl<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    > StepMergingInstance<P, N> {
        /**Creates a new wrapper around an on-chain [`StepMerging`](self) contract instance.

See the [wrapper's documentation](`StepMergingInstance`) for more details.*/
        #[inline]
        pub const fn new(
            address: alloy_sol_types::private::Address,
            __provider: P,
        ) -> Self {
            Self {
                address,
                provider: __provider,
                _network: ::core::marker::PhantomData,
            }
        }
        /// Returns a reference to the address.
        #[inline]
        pub const fn address(&self) -> &alloy_sol_types::private::Address {
            &self.address
        }
        /// Sets the address.
        #[inline]
        pub fn set_address(&mut self, address: alloy_sol_types::private::Address) {
            self.address = address;
        }
        /// Sets the address and returns `self`.
        pub fn at(mut self, address: alloy_sol_types::private::Address) -> Self {
            self.set_address(address);
            self
        }
        /// Returns a reference to the provider.
        #[inline]
        pub const fn provider(&self) -> &P {
            &self.provider
        }
    }
    impl<P: ::core::clone::Clone, N> StepMergingInstance<&P, N> {
        /// Clones the provider and returns a new instance with the cloned provider.
        #[inline]
        pub fn with_cloned_provider(self) -> StepMergingInstance<P, N> {
            StepMergingInstance {
                address: self.address,
                provider: ::core::clone::Clone::clone(&self.provider),
                _network: ::core::marker::PhantomData,
            }
        }
    }
    /// Function calls.
    impl<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    > StepMergingInstance<P, N> {
        /// Creates a new call builder using this contract instance's provider and address.
        ///
        /// Note that the call can be any function call, not just those defined in this
        /// contract. Prefer using the other methods for building type-safe contract calls.
        pub fn call_builder<C: alloy_sol_types::SolCall>(
            &self,
            call: &C,
        ) -> alloy_contract::SolCallBuilder<&P, C, N> {
            alloy_contract::SolCallBuilder::new_sol(&self.provider, &self.address, call)
        }
    }
    /// Event filters.
    impl<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    > StepMergingInstance<P, N> {
        /// Creates a new event filter using this contract instance's provider and address.
        ///
        /// Note that the type can be any event, not just those defined in this contract.
        /// Prefer using the other methods for building type-safe event filters.
        pub fn event_filter<E: alloy_sol_types::SolEvent>(
            &self,
        ) -> alloy_contract::Event<&P, E, N> {
            alloy_contract::Event::new_sol(&self.provider, &self.address)
        }
    }
}
/**

Generated by the following Solidity interface...
```solidity
library StepMerging {
    struct Hop {
        bytes32 dex;
        bytes32 fromToken;
        bytes32 toToken;
        uint256 amountIn;
        uint256 amountOut;
        uint256 gas;
        uint256 poolLiquidity;
    }
    struct MergedGroup {
        bytes32 signatureHash;
        uint256 mergedCount;
        uint256 mergedAmountAtIntermediate;
        uint256 mergedOutput;
        uint256 originalBestOutput;
        uint256 mergedGas;
        uint256 originalTotalGas;
    }
    struct Route {
        Hop[] hops;
        uint256 totalOutput;
        uint256 totalGas;
    }
}

interface PathFinder {
    struct Route {
        address[] path;
        uint8[] venues;
        uint24[] fees;
        uint256 amountOut;
    }

    error PathFinder__NoRoute();
    error PathFinder__SameToken();
    error PathFinder__SlippageOutOfRange();
    error PathFinder__VenueNotImplemented(uint8 venue);
    error PathFinder__ZeroAmount();

    function findRoute(address tokenIn, address tokenOut, uint256 amountIn, uint256 slippageBps) external returns (Route memory route);
    function findRouteWithHints(address tokenIn, address tokenOut, uint256 amountIn, uint256 slippageBps, bytes memory extraData) external returns (Route memory route);
    function mergeRoutes(StepMerging.Route[] memory routes, bytes32 finalToken) external pure returns (StepMerging.Route[] memory optimised, StepMerging.MergedGroup[] memory groups);
}
```

...which was generated by the following JSON ABI:
```json
[
  {
    "type": "function",
    "name": "findRoute",
    "inputs": [
      {
        "name": "tokenIn",
        "type": "address",
        "internalType": "address"
      },
      {
        "name": "tokenOut",
        "type": "address",
        "internalType": "address"
      },
      {
        "name": "amountIn",
        "type": "uint256",
        "internalType": "uint256"
      },
      {
        "name": "slippageBps",
        "type": "uint256",
        "internalType": "uint256"
      }
    ],
    "outputs": [
      {
        "name": "route",
        "type": "tuple",
        "internalType": "struct Route",
        "components": [
          {
            "name": "path",
            "type": "address[]",
            "internalType": "address[]"
          },
          {
            "name": "venues",
            "type": "uint8[]",
            "internalType": "uint8[]"
          },
          {
            "name": "fees",
            "type": "uint24[]",
            "internalType": "uint24[]"
          },
          {
            "name": "amountOut",
            "type": "uint256",
            "internalType": "uint256"
          }
        ]
      }
    ],
    "stateMutability": "nonpayable"
  },
  {
    "type": "function",
    "name": "findRouteWithHints",
    "inputs": [
      {
        "name": "tokenIn",
        "type": "address",
        "internalType": "address"
      },
      {
        "name": "tokenOut",
        "type": "address",
        "internalType": "address"
      },
      {
        "name": "amountIn",
        "type": "uint256",
        "internalType": "uint256"
      },
      {
        "name": "slippageBps",
        "type": "uint256",
        "internalType": "uint256"
      },
      {
        "name": "extraData",
        "type": "bytes",
        "internalType": "bytes"
      }
    ],
    "outputs": [
      {
        "name": "route",
        "type": "tuple",
        "internalType": "struct Route",
        "components": [
          {
            "name": "path",
            "type": "address[]",
            "internalType": "address[]"
          },
          {
            "name": "venues",
            "type": "uint8[]",
            "internalType": "uint8[]"
          },
          {
            "name": "fees",
            "type": "uint24[]",
            "internalType": "uint24[]"
          },
          {
            "name": "amountOut",
            "type": "uint256",
            "internalType": "uint256"
          }
        ]
      }
    ],
    "stateMutability": "nonpayable"
  },
  {
    "type": "function",
    "name": "mergeRoutes",
    "inputs": [
      {
        "name": "routes",
        "type": "tuple[]",
        "internalType": "struct StepMerging.Route[]",
        "components": [
          {
            "name": "hops",
            "type": "tuple[]",
            "internalType": "struct StepMerging.Hop[]",
            "components": [
              {
                "name": "dex",
                "type": "bytes32",
                "internalType": "bytes32"
              },
              {
                "name": "fromToken",
                "type": "bytes32",
                "internalType": "bytes32"
              },
              {
                "name": "toToken",
                "type": "bytes32",
                "internalType": "bytes32"
              },
              {
                "name": "amountIn",
                "type": "uint256",
                "internalType": "uint256"
              },
              {
                "name": "amountOut",
                "type": "uint256",
                "internalType": "uint256"
              },
              {
                "name": "gas",
                "type": "uint256",
                "internalType": "uint256"
              },
              {
                "name": "poolLiquidity",
                "type": "uint256",
                "internalType": "uint256"
              }
            ]
          },
          {
            "name": "totalOutput",
            "type": "uint256",
            "internalType": "uint256"
          },
          {
            "name": "totalGas",
            "type": "uint256",
            "internalType": "uint256"
          }
        ]
      },
      {
        "name": "finalToken",
        "type": "bytes32",
        "internalType": "bytes32"
      }
    ],
    "outputs": [
      {
        "name": "optimised",
        "type": "tuple[]",
        "internalType": "struct StepMerging.Route[]",
        "components": [
          {
            "name": "hops",
            "type": "tuple[]",
            "internalType": "struct StepMerging.Hop[]",
            "components": [
              {
                "name": "dex",
                "type": "bytes32",
                "internalType": "bytes32"
              },
              {
                "name": "fromToken",
                "type": "bytes32",
                "internalType": "bytes32"
              },
              {
                "name": "toToken",
                "type": "bytes32",
                "internalType": "bytes32"
              },
              {
                "name": "amountIn",
                "type": "uint256",
                "internalType": "uint256"
              },
              {
                "name": "amountOut",
                "type": "uint256",
                "internalType": "uint256"
              },
              {
                "name": "gas",
                "type": "uint256",
                "internalType": "uint256"
              },
              {
                "name": "poolLiquidity",
                "type": "uint256",
                "internalType": "uint256"
              }
            ]
          },
          {
            "name": "totalOutput",
            "type": "uint256",
            "internalType": "uint256"
          },
          {
            "name": "totalGas",
            "type": "uint256",
            "internalType": "uint256"
          }
        ]
      },
      {
        "name": "groups",
        "type": "tuple[]",
        "internalType": "struct StepMerging.MergedGroup[]",
        "components": [
          {
            "name": "signatureHash",
            "type": "bytes32",
            "internalType": "bytes32"
          },
          {
            "name": "mergedCount",
            "type": "uint256",
            "internalType": "uint256"
          },
          {
            "name": "mergedAmountAtIntermediate",
            "type": "uint256",
            "internalType": "uint256"
          },
          {
            "name": "mergedOutput",
            "type": "uint256",
            "internalType": "uint256"
          },
          {
            "name": "originalBestOutput",
            "type": "uint256",
            "internalType": "uint256"
          },
          {
            "name": "mergedGas",
            "type": "uint256",
            "internalType": "uint256"
          },
          {
            "name": "originalTotalGas",
            "type": "uint256",
            "internalType": "uint256"
          }
        ]
      }
    ],
    "stateMutability": "pure"
  },
  {
    "type": "error",
    "name": "PathFinder__NoRoute",
    "inputs": []
  },
  {
    "type": "error",
    "name": "PathFinder__SameToken",
    "inputs": []
  },
  {
    "type": "error",
    "name": "PathFinder__SlippageOutOfRange",
    "inputs": []
  },
  {
    "type": "error",
    "name": "PathFinder__VenueNotImplemented",
    "inputs": [
      {
        "name": "venue",
        "type": "uint8",
        "internalType": "uint8"
      }
    ]
  },
  {
    "type": "error",
    "name": "PathFinder__ZeroAmount",
    "inputs": []
  }
]
```*/
#[allow(
    non_camel_case_types,
    non_snake_case,
    clippy::pub_underscore_fields,
    clippy::style,
    clippy::empty_structs_with_brackets
)]
pub mod PathFinder {
    use super::*;
    use alloy::sol_types as alloy_sol_types;
    /// The creation / init bytecode of the contract.
    ///
    /// ```text
    ///0x608080604052346015576128bb908161001a8239f35b5f80fdfe6103a06040526004361015610012575f80fd5b5f3560e01c806321bf9f26146104ee57806381c6ecd6146101ea5763c036c8ea1461003b575f80fd5b346101e65760a03660031901126101e65761005461069c565b61005c6106b2565b6084359160643591604435906001600160401b0385116101e657366023860112156101e65784600401356001600160401b0381116101e65785019260248401933685116101e6576040906100ae610862565b506100bb878686866108a1565b879003126101e65760248601359560ff87168097036101e6576044810135906001600160401b0382116101e65701846043820112156101e65760248101359061010382610886565b95610111604051978861082a565b828752604482840101116101e657815f9260446020930183890137860101526002860361017957610143949550611806565b60608101511561016a576101669161015a91610bea565b604051918291826106c8565b0390f35b630541871160e01b5f5260045ffd5b600886036101915761018c9495506117a9565b610143565b600386036101a45761018c9495506116f9565b600986036101b75761018c9495506115fb565b85600581036101d457631602da9b60e21b5f52600560045260245ffd5b631602da9b60e21b5f5260045260245ffd5b5f80fd5b346101e65760403660031901126101e6576004356001600160401b0381116101e657366023820112156101e6578060040135906102268261084b565b90610234604051928361082a565b8282526024602083019360051b820101903682116101e65760248101935b8285106103d45761026560243585610d41565b60c05161026051604051918291604083016040845281518091526060840190602060608260051b8701019301915f905b82821061031d57505050508281036020840152602080835192838152019201905f5b8181106102c5575050500390f35b91935091602060e060019260c0875180518352848101518584015260408101516040840152606081015160608401526080810151608084015260a081015160a0840152015160c08201520194019101918493926102b7565b91939092949550605f1987820301825284519060608101918051926060835283518091526020608084019401905f905b80821061038057505050600192602092604080848680960151868501520151910152960192019201869594939192610295565b909194602060e060019260c0895180518352848101518584015260408101516040840152606081015160608401526080810151608084015260a081015160a0840152015160c082015201960192019061034d565b84356001600160401b0381116101e6578201606060231982360301126101e65760405190610401826107aa565b60248101356001600160401b0381116101e65760249082010136601f820112156101e65780356104308161084b565b9161043e604051938461082a565b818352602060e08185019302820101903682116101e657602001915b81831061048a57505050916064602094928594835260448101358584015201356040820152815201940193610252565b60e0833603126101e657602060e0916040516104a5816107d9565b85358152828601358382015260408601356040820152606086013560608201526080860135608082015260a086013560a082015260c086013560c082015281520192019161045a565b346101e65760803660031901126101e65761050761069c565b61050f6106b2565b6064359160443561051e610862565b5061052b848285856108a1565b6105368184846108ef565b9261054282828561093f565b8460608083015191015110610694575b506001600160a01b0383167382af49447d8a07e3bd95bd0d56f35241523fbab18114158061066d575b61060b575b73af88d065e77c8cc2239327c5edb3a432268e58311415806105e4575b6105bc575b50505060608101511561016a576101669161015a91610bea565b6105c592610b27565b60608101516060830151106105dc575b80806105a2565b9050826105d5565b506001600160a01b03811673af88d065e77c8cc2239327c5edb3a432268e5831141561059d565b6106168383866109a4565b610621848487610a8e565b906060810151606088015110610665575b506060810151606087015110610649575b50610580565b945073af88d065e77c8cc2239327c5edb3a432268e5831610643565b955087610632565b506001600160a01b0382167382af49447d8a07e3bd95bd0d56f35241523fbab1141561057b565b935085610552565b600435906001600160a01b03821682036101e657565b602435906001600160a01b03821682036101e657565b6020815260a0810191805192608060208401528351809152602060c084019401905f5b81811061078b57505050602081810151838503601f190160408501528051808652948201949101905f5b81811061077257505050604081015192601f19838203016060840152602080855192838152019401905f5b818110610757575050506060608091015191015290565b825162ffffff16865260209586019590920191600101610740565b825160ff16865260209586019590920191600101610715565b82516001600160a01b03168652602095860195909201916001016106eb565b606081019081106001600160401b038211176107c557604052565b634e487b7160e01b5f52604160045260245ffd5b60e081019081106001600160401b038211176107c557604052565b608081019081106001600160401b038211176107c557604052565b60a081019081106001600160401b038211176107c557604052565b90601f801991011681019081106001600160401b038211176107c557604052565b6001600160401b0381116107c55760051b60200190565b6040519061086f826107f4565b5f6060838181528160208201528160408201520152565b6001600160401b0381116107c557601f01601f191660200190565b6001600160a01b039081169116146108e057156108d1576103e8106108c257565b632a8406b960e01b5f5260045ffd5b63857e4aa960e01b5f5260045ffd5b634181f73f60e11b5f5260045ffd5b909291926109066108fe610862565b948284611a12565b91821561093a579061091791611bcf565b8352610921611c1a565b602084015261092e611c1a565b60408401526060830152565b505050565b9092919261095661094e610862565b948284611c6f565b919092831561099e5761092e929161096d91611bcf565b855260405161097d60408261082a565b6001815260203681830137600161099382610cfc565b526020860152611c41565b50505050565b909291926109cf6109b3610862565b947382af49447d8a07e3bd95bd0d56f35241523fbab184611a12565b801561093a576109f490827382af49447d8a07e3bd95bd0d56f35241523fbab1611a12565b91821561093a57907382af49447d8a07e3bd95bd0d56f35241523fbab1610a1a92611cf7565b8352604051610a2a60608261082a565b60028152604090813660208301375f610a4282610cfc565b525f610a4d82610d1d565b52602085015260405190610a6260608361082a565b600282523660208301375f610a7682610cfc565b525f610a8182610d1d565b5260408401526060830152565b90929192610ab9610a9d610862565b947382af49447d8a07e3bd95bd0d56f35241523fbab184611c6f565b90801561099e57610adf90837382af49447d8a07e3bd95bd0d56f35241523fbab1611c6f565b9290938415610b205761092e9392917382af49447d8a07e3bd95bd0d56f35241523fbab1610b0c92611cf7565b8652610b16611d61565b6020870152611d92565b5050505050565b90929192610b52610b36610862565b9473af88d065e77c8cc2239327c5edb3a432268e583184611c6f565b90801561099e57610b78908373af88d065e77c8cc2239327c5edb3a432268e5831611c6f565b9290938415610b205761092e93929173af88d065e77c8cc2239327c5edb3a432268e5831610b0c92611cf7565b81810292918115918404141715610bb857565b634e487b7160e01b5f52601160045260245ffd5b8115610bd6570490565b634e487b7160e01b5f52601260045260245ffd5b90610bf3610862565b5080610bfd575090565b606082019081519061271003906127108211610bb85761271091610c2091610ba5565b04905290565b60405190610c33826107aa565b5f604083606081528260208201520152565b90610c4f8261084b565b610c5c604051918261082a565b8281528092610c6d601f199161084b565b01905f5b828110610c7d57505050565b602090610c88610c26565b82828501015201610c71565b60405190610ca1826107d9565b5f60c0838281528260208201528260408201528260608201528260808201528260a08201520152565b90610cd48261084b565b610ce1604051918261082a565b8281528092610cf2601f199161084b565b0190602036910137565b805115610d095760200190565b634e487b7160e01b5f52603260045260245ffd5b805160011015610d095760400190565b8051821015610d095760209160051b010190565b6102c052610120525f610260525f60c0526102c051511561157557610d696102c05151610cca565b610380525f5b6102c05151811015610dc857806002610d8d6001936102c051610d2d565b5151511015610dac575f5b610da58261038051610d2d565b5201610d6f565b610dc3610dbc826102c051610d2d565b5151611dca565b610d98565b50610dd66102c05151610cca565b906102c0515191610de68361084b565b92610df4604051948561082a565b808452610e03601f199161084b565b013660208501375f6102a0525f5b6102c05151811015610ecd57610e2a8161038051610d2d565b515f81610e71575b906001929115610e44575b5001610e11565b610e516102a05185610d2d565b5281610e606102a05187610d2d565b52816102a051016102a0525f610e3d565b5f5b6102a0518110610e84575b50610e32565b82610e8f8287610d2d565b5114610e9d57600101610e73565b92919050610eab8387610d2d565b51925f198414610bb857610ec460018095019188610d2d565b52909180610e7e565b50919091610edd6102a051610c45565b610260525f5f5b6102a05181106115365750610f09610efb8261084b565b60405160a05260a05161082a565b60a051819052601f1990610f1c9061084b565b015f5b81811061151d5750509060a05160c0525f610240525f610360525f60e0525b6102a05160e05110610f4e575050565b610f5a60e05183610d2d565b51610320526001610f6d60e05183610d2d565b5103610ff5575f5b6102c05151811015610fee5761032051610f928261038051610d2d565b5114610fa057600101610f75565b610fb0906102c093929351610d2d565b51610fc16102405161026051610d2d565b52610fd26102405161026051610d2d565b5060016102405101610240525b600160e0510160e05290610f3e565b5090610fdf565b909161100360e05183610d2d565b516101c052611010610c26565b50611019610c94565b506110266101c051610c45565b610340525f925f5b6102c05151811015611515576103205161104b8261038051610d2d565b511461105a575b60010161102e565b9360019061106b866102c051610d2d565b516110798261034051610d2d565b526110878161034051610d2d565b5001936101c0518503611052575092505b5f610300526110a961034051610cfc565b51516110b761034051610cfc565b5151515f198101908111610bb8576110ce91610d2d565b5192608084015180670de0b6b3a7640000810204670de0b6b3a76400001481151715610bb857606085015161110c91670de0b6b3a764000002610bcc565b6102e0525f5b61034051518110156111f15761112b8161034051610d2d565b51515161113b8261034051610d2d565b51516001198201828111610bb85761115291610d2d565b51906111618361034051610d2d565b5151915f198201918211610bb85761117e60809261118e94610d2d565b5161014052015161030051611a05565b610300526080610140510151670de0b6b3a7640000810290808204670de0b6b3a76400001490151715610bb85761014051606001516111cc91610bcc565b6102e05181116111e0575b50600101611112565b6102e05261014051945060016111d7565b50919092670de0b6b3a764000061121b61121260c0840151610300516126ac565b61030051610ba5565b046102805260a081015180603e810204603e1481151715610bb85761124261034051610cfc565b515161125061034051610cfc565b515151610220819052600119810111610bb857606491604061127c603e93600119610220510190610d2d565b5101516102005260c08451940151936040516101e05261129e6101e0516107d9565b6101e051526102005160206101e05101526101205160406101e05101526103005160606101e05101526102805160806101e0510152020460a06101e051015260c06101e05101526112f161034051610cfc565b51516101a0526101a051516101805261131f61130f6101805161084b565b604051610160526101605161082a565b610180516101605152601f196113376101805161084b565b015f5b8181106114fb5750505f5b600181018111610bb8576101a05151600182011015611391578061136e6001926101a051610d2d565b5161137c8261016051610d2d565b5261138a8161016051610d2d565b5001611345565b50906101a05151805f19810111610bb8576113c7906101e0516113ba5f19830161016051610d2d565b525f190161016051610d2d565b506113d46101605161281e565b915f610100525f5f6080525b610340515160805110156114555761142a9061010051602061140760805161034051610d2d565b51015111611438575b604061142160805161034051610d2d565b51015190611a05565b6080805160010190526113e0565b602061144960805161034051610d2d565b51015161010052611410565b90926040810151916040519261146a846107d9565b6103205184526101c051602085015261030051604085015261028051606085015261010051608085015260a084015260c08301526114ae6102405161026051610d2d565b526114bf6102405161026051610d2d565b506114cf6103605160a051610d2d565b526114df6103605160a051610d2d565b5060016102405101610240526001610360510161036052610fdf565b602090611506610c94565b8282610160510101520161133a565b509250611098565b602090611528610c94565b828260a05101015201610f1f565b60016115428286610d2d565b511180611562575b611557575b600101610ee4565b60019091019061154f565b5061156d8184610d2d565b51151561154a565b60405161158360208261082a565b5f81525f805b8181106115d0575050604051906115a160208361082a565b5f82525f805b8181106115b95750506102605260c052565b6020906115c4610c94565b828287010152016115a7565b6020906115db610c26565b82828601015201611589565b51906001600160a01b03821682036101e657565b919392611606610862565b946060828051810103126101e657611620602083016115e7565b91606060408201519101519260ff84168094036101e6576001600160a01b0316801580156116e3575b6116db5784918691600286036116a9576116639550611f51565b915b821561093a579061167591611bcf565b835260405161168560408261082a565b6001815260203681830137600561169b82610cfc565b52602084015261092e611c1a565b9394909250600314159050610b20576001600160a01b0316908115610b2057846116d593928592611e94565b91611665565b505050505050565b50803b15611649565b519081151582036101e657565b919392611704610862565b946080828051810103126101e65761171e602083016115e7565b9160408101516117356080606084015193016116ec565b936001600160a01b0316801580156117a0575b61179757828214611797579061176094939291612279565b91821561093a579061177191611bcf565b835260405161178160408261082a565b6001815260203681830137600361169b82610cfc565b50505050505050565b50803b15611748565b919392936117b5610862565b946040818051810103126101e6576117db60406117d4602084016115e7565b92016116ec565b506001600160a01b0316801580156117fd575b61099e57908361090692612346565b50803b156117ee565b91939290611812610862565b9482518301908360208301920360e081126101e65760a0136101e6576040519361183b8561080f565b611847602082016115e7565b8552611855604082016115e7565b946020810195865260608201519562ffffff871687036101e6576040820196875260808301518060020b81036101e657606083015261189660a084016115e7565b60808301526118a760c084016116ec565b9260e0810151906001600160401b0382116101e6570185603f820112156101e6576020810151906118d782610886565b966118e5604051988961082a565b828852604082840101116101e657815f92604060209301838a015e8701015282156119975781516001600160a01b038981169116149081611980575b505b15611797579061193493929161238a565b92831561099e579161194d62ffffff9261092e94611bcf565b865260405161195d60408261082a565b6001815260203681830137600261197382610cfc565b5260208701525116611c41565b516001600160a01b0387811691161490505f611921565b516001600160a01b038881169116148015611923575080516001600160a01b03868116911614611923565b3d156119ec573d906119d382610886565b916119e1604051938461082a565b82523d5f602084013e565b606090565b51906001600160701b03821682036101e657565b91908201809211610bb857565b90611a1d908261249a565b6001600160a01b038116158015611bc6575b611bbf575f806040516020810190630240bc6b60e21b825260048152611a5660248261082a565b5190845afa91611a646119c2565b92158015611bb4575b611b7e576060838051810103126101e657611a8a602084016119f1565b916060611a99604086016119f1565b94015163ffffffff8116036101e6575f80916040516020810190630dfe168160e01b825260048152611acc60248261082a565b51915afa611ad86119c2565b90158015611ba9575b611ba0576020818051810103126101e6576001600160a01b0390611b07906020016115e7565b6001600160a01b03909216911603611b8e576001600160701b0391821691165b801591828015611b86575b611b7e576103e58402938085046103e51490151715610bb857611b559084610ba5565b916103e882029182046103e8141715610bb857611b7b92611b7591611a05565b90610bcc565b90565b505050505f90565b508015611b32565b6001600160701b039081169116611b27565b50505050505f90565b506020815110611ae1565b506060835110611a6d565b5050505f90565b50803b15611a2f565b9190611c0b604051611be260608261082a565b6002815260403660208301378094611bf982610cfc565b6001600160a01b039091169052610d1d565b6001600160a01b039091169052565b60405190611c2960408361082a565b60018252602036818401375f611c3e83610cfc565b52565b9060405191611c5160408461082a565b600183526020368185013762ffffff611c6984610cfc565b91169052565b919290925f935f93611c82838383612539565b80611ceb575b50611c948383836125b0565b868111611cde575b50611ca8838383612604565b868111611ccf575b5090611cbc9291612658565b838111611cc65750565b92506127109150565b9550610bb89450611cbc611cb0565b95506101f494505f611c9c565b9550606494505f611c88565b92919060405190611d0960808361082a565b6003825260603660208401378194611d2083610cfc565b6001600160a01b039091169052611d3682610d1d565b6001600160a01b039091169052805160021015610d09576001600160a01b0390911660609190910152565b60405190611d7060608361082a565b6002825260403660208401376001611c3e8382611d8c82610cfc565b52610d1d565b919062ffffff611c69604051611da960608261082a565b600281526040366020830137809583611dc183610cfc565b91169052610d1d565b90815160028110611e6a575f198101908111610bb857611de981610cca565b905f5b818110611e475750509091506040516020810181819360208151939101925f5b818110611e2e575050611e28925003601f19810183528261082a565b51902090565b8451835260209485019486945090920191600101611e0c565b806040611e5660019388610d2d565b510151611e638286610d2d565b5201611dec565b505f9150565b805180835260209291819084018484015e5f828201840152601f01601f1916010190565b905f8094611f128295611f0460209960405190611eb18c8361082a565b8682526040516307d245e960e41b8d82019081526001600160a01b03998a1660248301529489166044820152959097166064860152608485019690965260a060a4850152909483919060c4830190611e70565b03601f19810183528261082a565b51925af190611f1f6119c2565b91158015611f47575b611f4157815181830192018101829003126101e6575190565b50505f90565b5080825110611f28565b9091939293604094855193611f66878661082a565b60018552601f1987015f5b8181106122455750508651602096611f89888361082a565b5f8252885192611f988461080f565b83525f8884015260018984015260608301526080820152611fb885610cfc565b52611fc284610cfc565b50606093865191611fd3868461082a565b6002835286830193601f198701368637611fec84610cfc565b6001600160a01b03909116905261200283610d1d565b6001600160a01b039091169052865161201a816107f4565b308152868101905f82528881019230845288888301955f87528b80519a637c26833760e11b848d01528b6101048101915f602483015260e060448301528651809352610124820190866101248560051b8501019801945f935b8585106121e35750505050508b85036023190160648d0152505051808352910195905f5b8a8282106121c657505091516001600160a01b0390811660848a01529251151560a4890152505090511660c485015251151560e4840152829003601f19810183525f92839290916120e8908361082a565b828583519301915af16120f96119c2565b901580156121bc575b611bbf57805181019082818184019303126101e65782810151906001600160401b0382116101e657019281603f850112156101e65782840151906121458261084b565b946121528251968761082a565b82865284808088019460051b830101019384116101e65701905b8282106121ad575050505060028151106121a85761218990610d1d565b515f8112156121a857600160ff1b8114610bb857611b7b905f03612887565b505f90565b8151815290830190830161216c565b5082815110612102565b83516001600160a01b031689529788019790920191600101612097565b889294969960a06080600196989a9b946122309461012319908503018a528d5190815185528682015187860152808201519085015288810151898501520151918160808201520190611e70565b98019301930190928f938f969593948f612073565b60209089516122538161080f565b5f81525f838201525f8b8201525f60608201526060608082015282828a01015201611f71565b5f9485949193929015612310576122926122989161289c565b9261289c565b60405192635e0d443f60e01b6020850152600f0b6024840152600f0b60448301526064820152606481526122cd60848261082a565b905b602082519201905afa6122e06119c2565b90158015612305575b6121a857602081519181808201938492010103126101e6575190565b5060208151106122e9565b916040519263556d6e9f60e01b60208501526024840152604483015260648201526064815261234060848261082a565b906122cf565b5f9283926040519060208201926378a051ad60e11b8452602483015260018060a01b031660448201526044815261237e60648261082a565b51915afa6122e06119c2565b9091600160801b81101561248d5761246b5f9493611f048695604051956123b0876107f4565b86526020860192151583526001600160801b036040870195168552606086019081526001600160801b03604051958694602086019863aa9d21cb60e01b8a52602060248801525160018060a01b03815116604488015260018060a01b03602082015116606488015262ffffff6040820151166084880152606081015160020b60a4880152608060018060a01b039101511660c487015251151560e4860152511661010484015251610100610124840152610144830190611e70565b519082733972c00f7ed4885e145823eb7c655375d275a1c55af16122e06119c2565b6335278d125f526004601cfd5b60405163e6a4390560e01b602082019081526001600160a01b0392831660248301529290911660448083019190915281525f9182916124da60648261082a565b519073f1d7cc64fb4452f05c498126312ebe29f30fbcf95afa6124fb6119c2565b9015801561252e575b6121a8576020818051810103126101e6576001600160a01b039061252a906020016115e7565b1690565b506020815110612504565b604051636352813560e11b602082019081526001600160a01b03928316602483015291909216604483015260648083019390935260848201929092525f60a4808301829052825291829161258e60c48261082a565b5190827361ffe014ba17989e743c5f6cb21bf9697530b21e5af16122e06119c2565b604051636352813560e11b602082019081526001600160a01b03928316602483015291909216604483015260648201929092526101f460848201525f60a4808301829052825291829161258e60c48261082a565b604051636352813560e11b602082019081526001600160a01b0392831660248301529190921660448301526064820192909252610bb860848201525f60a4808301829052825291829161258e60c48261082a565b604051636352813560e11b602082019081526001600160a01b039283166024830152919092166044830152606482019290925261271060848201525f60a4808301829052825291829161258e60c48261082a565b908015611f4157816126bd91611a05565b670de0b6b3a7640000820291818115670de0b6b3a7640000838604141702156127a9575090045b60038102906064811560038385041417021561274b5750606490045b660aa87bee5380008101670de0b6b3a7640000111561274457670dd60e37b9108000035b67016345785d8a00008111156127375790565b5067016345785d8a000090565b505f612724565b606460035f1981840984811085019003920990806064111561279c57828211900360fe1b910360021c177f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c2902612700565b63ae47f7025f526004601cfd5b81670de0b6b3a76400005f1981840985811086019003920990825f038316928181111561279c5783900480600302600218808202600203028082026002030280820260020302808202600203028082026002030280910260020302936001848483030494805f030401921190030217026126e4565b90612827610c26565b82815282518015612882575f198101908111610bb85761284960809185610d2d565b51015160208201525f90815b84518310156128785761287060019160a06114218689610d2d565b920191612855565b6040820152925050565b509150565b5f811215611b7b576335278d125f526004601cfd5b6001607f1b81101561248d57600f0b9056fea164736f6c6343000822000a
    /// ```
    #[rustfmt::skip]
    #[allow(clippy::all)]
    pub static BYTECODE: alloy_sol_types::private::Bytes = alloy_sol_types::private::Bytes::from_static(
        b"`\x80\x80`@R4`\x15Wa(\xBB\x90\x81a\0\x1A\x829\xF3[_\x80\xFD\xFEa\x03\xA0`@R`\x046\x10\x15a\0\x12W_\x80\xFD[_5`\xE0\x1C\x80c!\xBF\x9F&\x14a\x04\xEEW\x80c\x81\xC6\xEC\xD6\x14a\x01\xEAWc\xC06\xC8\xEA\x14a\0;W_\x80\xFD[4a\x01\xE6W`\xA06`\x03\x19\x01\x12a\x01\xE6Wa\0Ta\x06\x9CV[a\0\\a\x06\xB2V[`\x845\x91`d5\x91`D5\x90`\x01`\x01`@\x1B\x03\x85\x11a\x01\xE6W6`#\x86\x01\x12\x15a\x01\xE6W\x84`\x04\x015`\x01`\x01`@\x1B\x03\x81\x11a\x01\xE6W\x85\x01\x92`$\x84\x01\x936\x85\x11a\x01\xE6W`@\x90a\0\xAEa\x08bV[Pa\0\xBB\x87\x86\x86\x86a\x08\xA1V[\x87\x90\x03\x12a\x01\xE6W`$\x86\x015\x95`\xFF\x87\x16\x80\x97\x03a\x01\xE6W`D\x81\x015\x90`\x01`\x01`@\x1B\x03\x82\x11a\x01\xE6W\x01\x84`C\x82\x01\x12\x15a\x01\xE6W`$\x81\x015\x90a\x01\x03\x82a\x08\x86V[\x95a\x01\x11`@Q\x97\x88a\x08*V[\x82\x87R`D\x82\x84\x01\x01\x11a\x01\xE6W\x81_\x92`D` \x93\x01\x83\x89\x017\x86\x01\x01R`\x02\x86\x03a\x01yWa\x01C\x94\x95Pa\x18\x06V[``\x81\x01Q\x15a\x01jWa\x01f\x91a\x01Z\x91a\x0B\xEAV[`@Q\x91\x82\x91\x82a\x06\xC8V[\x03\x90\xF3[c\x05A\x87\x11`\xE0\x1B_R`\x04_\xFD[`\x08\x86\x03a\x01\x91Wa\x01\x8C\x94\x95Pa\x17\xA9V[a\x01CV[`\x03\x86\x03a\x01\xA4Wa\x01\x8C\x94\x95Pa\x16\xF9V[`\t\x86\x03a\x01\xB7Wa\x01\x8C\x94\x95Pa\x15\xFBV[\x85`\x05\x81\x03a\x01\xD4Wc\x16\x02\xDA\x9B`\xE2\x1B_R`\x05`\x04R`$_\xFD[c\x16\x02\xDA\x9B`\xE2\x1B_R`\x04R`$_\xFD[_\x80\xFD[4a\x01\xE6W`@6`\x03\x19\x01\x12a\x01\xE6W`\x045`\x01`\x01`@\x1B\x03\x81\x11a\x01\xE6W6`#\x82\x01\x12\x15a\x01\xE6W\x80`\x04\x015\x90a\x02&\x82a\x08KV[\x90a\x024`@Q\x92\x83a\x08*V[\x82\x82R`$` \x83\x01\x93`\x05\x1B\x82\x01\x01\x906\x82\x11a\x01\xE6W`$\x81\x01\x93[\x82\x85\x10a\x03\xD4Wa\x02e`$5\x85a\rAV[`\xC0Qa\x02`Q`@Q\x91\x82\x91`@\x83\x01`@\x84R\x81Q\x80\x91R``\x84\x01\x90` ``\x82`\x05\x1B\x87\x01\x01\x93\x01\x91_\x90[\x82\x82\x10a\x03\x1DWPPPP\x82\x81\x03` \x84\x01R` \x80\x83Q\x92\x83\x81R\x01\x92\x01\x90_[\x81\x81\x10a\x02\xC5WPPP\x03\x90\xF3[\x91\x93P\x91` `\xE0`\x01\x92`\xC0\x87Q\x80Q\x83R\x84\x81\x01Q\x85\x84\x01R`@\x81\x01Q`@\x84\x01R``\x81\x01Q``\x84\x01R`\x80\x81\x01Q`\x80\x84\x01R`\xA0\x81\x01Q`\xA0\x84\x01R\x01Q`\xC0\x82\x01R\x01\x94\x01\x91\x01\x91\x84\x93\x92a\x02\xB7V[\x91\x93\x90\x92\x94\x95P`_\x19\x87\x82\x03\x01\x82R\x84Q\x90``\x81\x01\x91\x80Q\x92``\x83R\x83Q\x80\x91R` `\x80\x84\x01\x94\x01\x90_\x90[\x80\x82\x10a\x03\x80WPPP`\x01\x92` \x92`@\x80\x84\x86\x80\x96\x01Q\x86\x85\x01R\x01Q\x91\x01R\x96\x01\x92\x01\x92\x01\x86\x95\x94\x93\x91\x92a\x02\x95V[\x90\x91\x94` `\xE0`\x01\x92`\xC0\x89Q\x80Q\x83R\x84\x81\x01Q\x85\x84\x01R`@\x81\x01Q`@\x84\x01R``\x81\x01Q``\x84\x01R`\x80\x81\x01Q`\x80\x84\x01R`\xA0\x81\x01Q`\xA0\x84\x01R\x01Q`\xC0\x82\x01R\x01\x96\x01\x92\x01\x90a\x03MV[\x845`\x01`\x01`@\x1B\x03\x81\x11a\x01\xE6W\x82\x01```#\x19\x826\x03\x01\x12a\x01\xE6W`@Q\x90a\x04\x01\x82a\x07\xAAV[`$\x81\x015`\x01`\x01`@\x1B\x03\x81\x11a\x01\xE6W`$\x90\x82\x01\x016`\x1F\x82\x01\x12\x15a\x01\xE6W\x805a\x040\x81a\x08KV[\x91a\x04>`@Q\x93\x84a\x08*V[\x81\x83R` `\xE0\x81\x85\x01\x93\x02\x82\x01\x01\x906\x82\x11a\x01\xE6W` \x01\x91[\x81\x83\x10a\x04\x8AWPPP\x91`d` \x94\x92\x85\x94\x83R`D\x81\x015\x85\x84\x01R\x015`@\x82\x01R\x81R\x01\x94\x01\x93a\x02RV[`\xE0\x836\x03\x12a\x01\xE6W` `\xE0\x91`@Qa\x04\xA5\x81a\x07\xD9V[\x855\x81R\x82\x86\x015\x83\x82\x01R`@\x86\x015`@\x82\x01R``\x86\x015``\x82\x01R`\x80\x86\x015`\x80\x82\x01R`\xA0\x86\x015`\xA0\x82\x01R`\xC0\x86\x015`\xC0\x82\x01R\x81R\x01\x92\x01\x91a\x04ZV[4a\x01\xE6W`\x806`\x03\x19\x01\x12a\x01\xE6Wa\x05\x07a\x06\x9CV[a\x05\x0Fa\x06\xB2V[`d5\x91`D5a\x05\x1Ea\x08bV[Pa\x05+\x84\x82\x85\x85a\x08\xA1V[a\x056\x81\x84\x84a\x08\xEFV[\x92a\x05B\x82\x82\x85a\t?V[\x84``\x80\x83\x01Q\x91\x01Q\x10a\x06\x94W[P`\x01`\x01`\xA0\x1B\x03\x83\x16s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1\x81\x14\x15\x80a\x06mW[a\x06\x0BW[s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1\x14\x15\x80a\x05\xE4W[a\x05\xBCW[PPP``\x81\x01Q\x15a\x01jWa\x01f\x91a\x01Z\x91a\x0B\xEAV[a\x05\xC5\x92a\x0B'V[``\x81\x01Q``\x83\x01Q\x10a\x05\xDCW[\x80\x80a\x05\xA2V[\x90P\x82a\x05\xD5V[P`\x01`\x01`\xA0\x1B\x03\x81\x16s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1\x14\x15a\x05\x9DV[a\x06\x16\x83\x83\x86a\t\xA4V[a\x06!\x84\x84\x87a\n\x8EV[\x90``\x81\x01Q``\x88\x01Q\x10a\x06eW[P``\x81\x01Q``\x87\x01Q\x10a\x06IW[Pa\x05\x80V[\x94Ps\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1a\x06CV[\x95P\x87a\x062V[P`\x01`\x01`\xA0\x1B\x03\x82\x16s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1\x14\x15a\x05{V[\x93P\x85a\x05RV[`\x045\x90`\x01`\x01`\xA0\x1B\x03\x82\x16\x82\x03a\x01\xE6WV[`$5\x90`\x01`\x01`\xA0\x1B\x03\x82\x16\x82\x03a\x01\xE6WV[` \x81R`\xA0\x81\x01\x91\x80Q\x92`\x80` \x84\x01R\x83Q\x80\x91R` `\xC0\x84\x01\x94\x01\x90_[\x81\x81\x10a\x07\x8BWPPP` \x81\x81\x01Q\x83\x85\x03`\x1F\x19\x01`@\x85\x01R\x80Q\x80\x86R\x94\x82\x01\x94\x91\x01\x90_[\x81\x81\x10a\x07rWPPP`@\x81\x01Q\x92`\x1F\x19\x83\x82\x03\x01``\x84\x01R` \x80\x85Q\x92\x83\x81R\x01\x94\x01\x90_[\x81\x81\x10a\x07WWPPP```\x80\x91\x01Q\x91\x01R\x90V[\x82Qb\xFF\xFF\xFF\x16\x86R` \x95\x86\x01\x95\x90\x92\x01\x91`\x01\x01a\x07@V[\x82Q`\xFF\x16\x86R` \x95\x86\x01\x95\x90\x92\x01\x91`\x01\x01a\x07\x15V[\x82Q`\x01`\x01`\xA0\x1B\x03\x16\x86R` \x95\x86\x01\x95\x90\x92\x01\x91`\x01\x01a\x06\xEBV[``\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[cNH{q`\xE0\x1B_R`A`\x04R`$_\xFD[`\xE0\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[`\x80\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[`\xA0\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[\x90`\x1F\x80\x19\x91\x01\x16\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[`\x01`\x01`@\x1B\x03\x81\x11a\x07\xC5W`\x05\x1B` \x01\x90V[`@Q\x90a\x08o\x82a\x07\xF4V[_``\x83\x81\x81R\x81` \x82\x01R\x81`@\x82\x01R\x01RV[`\x01`\x01`@\x1B\x03\x81\x11a\x07\xC5W`\x1F\x01`\x1F\x19\x16` \x01\x90V[`\x01`\x01`\xA0\x1B\x03\x90\x81\x16\x91\x16\x14a\x08\xE0W\x15a\x08\xD1Wa\x03\xE8\x10a\x08\xC2WV[c*\x84\x06\xB9`\xE0\x1B_R`\x04_\xFD[c\x85~J\xA9`\xE0\x1B_R`\x04_\xFD[cA\x81\xF7?`\xE1\x1B_R`\x04_\xFD[\x90\x92\x91\x92a\t\x06a\x08\xFEa\x08bV[\x94\x82\x84a\x1A\x12V[\x91\x82\x15a\t:W\x90a\t\x17\x91a\x1B\xCFV[\x83Ra\t!a\x1C\x1AV[` \x84\x01Ra\t.a\x1C\x1AV[`@\x84\x01R``\x83\x01RV[PPPV[\x90\x92\x91\x92a\tVa\tNa\x08bV[\x94\x82\x84a\x1CoV[\x91\x90\x92\x83\x15a\t\x9EWa\t.\x92\x91a\tm\x91a\x1B\xCFV[\x85R`@Qa\t}`@\x82a\x08*V[`\x01\x81R` 6\x81\x83\x017`\x01a\t\x93\x82a\x0C\xFCV[R` \x86\x01Ra\x1CAV[PPPPV[\x90\x92\x91\x92a\t\xCFa\t\xB3a\x08bV[\x94s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1\x84a\x1A\x12V[\x80\x15a\t:Wa\t\xF4\x90\x82s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1a\x1A\x12V[\x91\x82\x15a\t:W\x90s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1a\n\x1A\x92a\x1C\xF7V[\x83R`@Qa\n*``\x82a\x08*V[`\x02\x81R`@\x90\x816` \x83\x017_a\nB\x82a\x0C\xFCV[R_a\nM\x82a\r\x1DV[R` \x85\x01R`@Q\x90a\nb``\x83a\x08*V[`\x02\x82R6` \x83\x017_a\nv\x82a\x0C\xFCV[R_a\n\x81\x82a\r\x1DV[R`@\x84\x01R``\x83\x01RV[\x90\x92\x91\x92a\n\xB9a\n\x9Da\x08bV[\x94s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1\x84a\x1CoV[\x90\x80\x15a\t\x9EWa\n\xDF\x90\x83s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1a\x1CoV[\x92\x90\x93\x84\x15a\x0B Wa\t.\x93\x92\x91s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1a\x0B\x0C\x92a\x1C\xF7V[\x86Ra\x0B\x16a\x1DaV[` \x87\x01Ra\x1D\x92V[PPPPPV[\x90\x92\x91\x92a\x0BRa\x0B6a\x08bV[\x94s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1\x84a\x1CoV[\x90\x80\x15a\t\x9EWa\x0Bx\x90\x83s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1a\x1CoV[\x92\x90\x93\x84\x15a\x0B Wa\t.\x93\x92\x91s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1a\x0B\x0C\x92a\x1C\xF7V[\x81\x81\x02\x92\x91\x81\x15\x91\x84\x04\x14\x17\x15a\x0B\xB8WV[cNH{q`\xE0\x1B_R`\x11`\x04R`$_\xFD[\x81\x15a\x0B\xD6W\x04\x90V[cNH{q`\xE0\x1B_R`\x12`\x04R`$_\xFD[\x90a\x0B\xF3a\x08bV[P\x80a\x0B\xFDWP\x90V[``\x82\x01\x90\x81Q\x90a'\x10\x03\x90a'\x10\x82\x11a\x0B\xB8Wa'\x10\x91a\x0C \x91a\x0B\xA5V[\x04\x90R\x90V[`@Q\x90a\x0C3\x82a\x07\xAAV[_`@\x83``\x81R\x82` \x82\x01R\x01RV[\x90a\x0CO\x82a\x08KV[a\x0C\\`@Q\x91\x82a\x08*V[\x82\x81R\x80\x92a\x0Cm`\x1F\x19\x91a\x08KV[\x01\x90_[\x82\x81\x10a\x0C}WPPPV[` \x90a\x0C\x88a\x0C&V[\x82\x82\x85\x01\x01R\x01a\x0CqV[`@Q\x90a\x0C\xA1\x82a\x07\xD9V[_`\xC0\x83\x82\x81R\x82` \x82\x01R\x82`@\x82\x01R\x82``\x82\x01R\x82`\x80\x82\x01R\x82`\xA0\x82\x01R\x01RV[\x90a\x0C\xD4\x82a\x08KV[a\x0C\xE1`@Q\x91\x82a\x08*V[\x82\x81R\x80\x92a\x0C\xF2`\x1F\x19\x91a\x08KV[\x01\x90` 6\x91\x017V[\x80Q\x15a\r\tW` \x01\x90V[cNH{q`\xE0\x1B_R`2`\x04R`$_\xFD[\x80Q`\x01\x10\x15a\r\tW`@\x01\x90V[\x80Q\x82\x10\x15a\r\tW` \x91`\x05\x1B\x01\x01\x90V[a\x02\xC0Ra\x01 R_a\x02`R_`\xC0Ra\x02\xC0QQ\x15a\x15uWa\ria\x02\xC0QQa\x0C\xCAV[a\x03\x80R_[a\x02\xC0QQ\x81\x10\x15a\r\xC8W\x80`\x02a\r\x8D`\x01\x93a\x02\xC0Qa\r-V[QQQ\x10\x15a\r\xACW_[a\r\xA5\x82a\x03\x80Qa\r-V[R\x01a\roV[a\r\xC3a\r\xBC\x82a\x02\xC0Qa\r-V[QQa\x1D\xCAV[a\r\x98V[Pa\r\xD6a\x02\xC0QQa\x0C\xCAV[\x90a\x02\xC0QQ\x91a\r\xE6\x83a\x08KV[\x92a\r\xF4`@Q\x94\x85a\x08*V[\x80\x84Ra\x0E\x03`\x1F\x19\x91a\x08KV[\x016` \x85\x017_a\x02\xA0R_[a\x02\xC0QQ\x81\x10\x15a\x0E\xCDWa\x0E*\x81a\x03\x80Qa\r-V[Q_\x81a\x0EqW[\x90`\x01\x92\x91\x15a\x0EDW[P\x01a\x0E\x11V[a\x0EQa\x02\xA0Q\x85a\r-V[R\x81a\x0E`a\x02\xA0Q\x87a\r-V[R\x81a\x02\xA0Q\x01a\x02\xA0R_a\x0E=V[_[a\x02\xA0Q\x81\x10a\x0E\x84W[Pa\x0E2V[\x82a\x0E\x8F\x82\x87a\r-V[Q\x14a\x0E\x9DW`\x01\x01a\x0EsV[\x92\x91\x90Pa\x0E\xAB\x83\x87a\r-V[Q\x92_\x19\x84\x14a\x0B\xB8Wa\x0E\xC4`\x01\x80\x95\x01\x91\x88a\r-V[R\x90\x91\x80a\x0E~V[P\x91\x90\x91a\x0E\xDDa\x02\xA0Qa\x0CEV[a\x02`R__[a\x02\xA0Q\x81\x10a\x156WPa\x0F\ta\x0E\xFB\x82a\x08KV[`@Q`\xA0R`\xA0Qa\x08*V[`\xA0Q\x81\x90R`\x1F\x19\x90a\x0F\x1C\x90a\x08KV[\x01_[\x81\x81\x10a\x15\x1DWPP\x90`\xA0Q`\xC0R_a\x02@R_a\x03`R_`\xE0R[a\x02\xA0Q`\xE0Q\x10a\x0FNWPPV[a\x0FZ`\xE0Q\x83a\r-V[Qa\x03 R`\x01a\x0Fm`\xE0Q\x83a\r-V[Q\x03a\x0F\xF5W_[a\x02\xC0QQ\x81\x10\x15a\x0F\xEEWa\x03 Qa\x0F\x92\x82a\x03\x80Qa\r-V[Q\x14a\x0F\xA0W`\x01\x01a\x0FuV[a\x0F\xB0\x90a\x02\xC0\x93\x92\x93Qa\r-V[Qa\x0F\xC1a\x02@Qa\x02`Qa\r-V[Ra\x0F\xD2a\x02@Qa\x02`Qa\r-V[P`\x01a\x02@Q\x01a\x02@R[`\x01`\xE0Q\x01`\xE0R\x90a\x0F>V[P\x90a\x0F\xDFV[\x90\x91a\x10\x03`\xE0Q\x83a\r-V[Qa\x01\xC0Ra\x10\x10a\x0C&V[Pa\x10\x19a\x0C\x94V[Pa\x10&a\x01\xC0Qa\x0CEV[a\x03@R_\x92_[a\x02\xC0QQ\x81\x10\x15a\x15\x15Wa\x03 Qa\x10K\x82a\x03\x80Qa\r-V[Q\x14a\x10ZW[`\x01\x01a\x10.V[\x93`\x01\x90a\x10k\x86a\x02\xC0Qa\r-V[Qa\x10y\x82a\x03@Qa\r-V[Ra\x10\x87\x81a\x03@Qa\r-V[P\x01\x93a\x01\xC0Q\x85\x03a\x10RWP\x92P[_a\x03\0Ra\x10\xA9a\x03@Qa\x0C\xFCV[QQa\x10\xB7a\x03@Qa\x0C\xFCV[QQQ_\x19\x81\x01\x90\x81\x11a\x0B\xB8Wa\x10\xCE\x91a\r-V[Q\x92`\x80\x84\x01Q\x80g\r\xE0\xB6\xB3\xA7d\0\0\x81\x02\x04g\r\xE0\xB6\xB3\xA7d\0\0\x14\x81\x15\x17\x15a\x0B\xB8W``\x85\x01Qa\x11\x0C\x91g\r\xE0\xB6\xB3\xA7d\0\0\x02a\x0B\xCCV[a\x02\xE0R_[a\x03@QQ\x81\x10\x15a\x11\xF1Wa\x11+\x81a\x03@Qa\r-V[QQQa\x11;\x82a\x03@Qa\r-V[QQ`\x01\x19\x82\x01\x82\x81\x11a\x0B\xB8Wa\x11R\x91a\r-V[Q\x90a\x11a\x83a\x03@Qa\r-V[QQ\x91_\x19\x82\x01\x91\x82\x11a\x0B\xB8Wa\x11~`\x80\x92a\x11\x8E\x94a\r-V[Qa\x01@R\x01Qa\x03\0Qa\x1A\x05V[a\x03\0R`\x80a\x01@Q\x01Qg\r\xE0\xB6\xB3\xA7d\0\0\x81\x02\x90\x80\x82\x04g\r\xE0\xB6\xB3\xA7d\0\0\x14\x90\x15\x17\x15a\x0B\xB8Wa\x01@Q``\x01Qa\x11\xCC\x91a\x0B\xCCV[a\x02\xE0Q\x81\x11a\x11\xE0W[P`\x01\x01a\x11\x12V[a\x02\xE0Ra\x01@Q\x94P`\x01a\x11\xD7V[P\x91\x90\x92g\r\xE0\xB6\xB3\xA7d\0\0a\x12\x1Ba\x12\x12`\xC0\x84\x01Qa\x03\0Qa&\xACV[a\x03\0Qa\x0B\xA5V[\x04a\x02\x80R`\xA0\x81\x01Q\x80`>\x81\x02\x04`>\x14\x81\x15\x17\x15a\x0B\xB8Wa\x12Ba\x03@Qa\x0C\xFCV[QQa\x12Pa\x03@Qa\x0C\xFCV[QQQa\x02 \x81\x90R`\x01\x19\x81\x01\x11a\x0B\xB8W`d\x91`@a\x12|`>\x93`\x01\x19a\x02 Q\x01\x90a\r-V[Q\x01Qa\x02\0R`\xC0\x84Q\x94\x01Q\x93`@Qa\x01\xE0Ra\x12\x9Ea\x01\xE0Qa\x07\xD9V[a\x01\xE0QRa\x02\0Q` a\x01\xE0Q\x01Ra\x01 Q`@a\x01\xE0Q\x01Ra\x03\0Q``a\x01\xE0Q\x01Ra\x02\x80Q`\x80a\x01\xE0Q\x01R\x02\x04`\xA0a\x01\xE0Q\x01R`\xC0a\x01\xE0Q\x01Ra\x12\xF1a\x03@Qa\x0C\xFCV[QQa\x01\xA0Ra\x01\xA0QQa\x01\x80Ra\x13\x1Fa\x13\x0Fa\x01\x80Qa\x08KV[`@Qa\x01`Ra\x01`Qa\x08*V[a\x01\x80Qa\x01`QR`\x1F\x19a\x137a\x01\x80Qa\x08KV[\x01_[\x81\x81\x10a\x14\xFBWPP_[`\x01\x81\x01\x81\x11a\x0B\xB8Wa\x01\xA0QQ`\x01\x82\x01\x10\x15a\x13\x91W\x80a\x13n`\x01\x92a\x01\xA0Qa\r-V[Qa\x13|\x82a\x01`Qa\r-V[Ra\x13\x8A\x81a\x01`Qa\r-V[P\x01a\x13EV[P\x90a\x01\xA0QQ\x80_\x19\x81\x01\x11a\x0B\xB8Wa\x13\xC7\x90a\x01\xE0Qa\x13\xBA_\x19\x83\x01a\x01`Qa\r-V[R_\x19\x01a\x01`Qa\r-V[Pa\x13\xD4a\x01`Qa(\x1EV[\x91_a\x01\0R__`\x80R[a\x03@QQ`\x80Q\x10\x15a\x14UWa\x14*\x90a\x01\0Q` a\x14\x07`\x80Qa\x03@Qa\r-V[Q\x01Q\x11a\x148W[`@a\x14!`\x80Qa\x03@Qa\r-V[Q\x01Q\x90a\x1A\x05V[`\x80\x80Q`\x01\x01\x90Ra\x13\xE0V[` a\x14I`\x80Qa\x03@Qa\r-V[Q\x01Qa\x01\0Ra\x14\x10V[\x90\x92`@\x81\x01Q\x91`@Q\x92a\x14j\x84a\x07\xD9V[a\x03 Q\x84Ra\x01\xC0Q` \x85\x01Ra\x03\0Q`@\x85\x01Ra\x02\x80Q``\x85\x01Ra\x01\0Q`\x80\x85\x01R`\xA0\x84\x01R`\xC0\x83\x01Ra\x14\xAEa\x02@Qa\x02`Qa\r-V[Ra\x14\xBFa\x02@Qa\x02`Qa\r-V[Pa\x14\xCFa\x03`Q`\xA0Qa\r-V[Ra\x14\xDFa\x03`Q`\xA0Qa\r-V[P`\x01a\x02@Q\x01a\x02@R`\x01a\x03`Q\x01a\x03`Ra\x0F\xDFV[` \x90a\x15\x06a\x0C\x94V[\x82\x82a\x01`Q\x01\x01R\x01a\x13:V[P\x92Pa\x10\x98V[` \x90a\x15(a\x0C\x94V[\x82\x82`\xA0Q\x01\x01R\x01a\x0F\x1FV[`\x01a\x15B\x82\x86a\r-V[Q\x11\x80a\x15bW[a\x15WW[`\x01\x01a\x0E\xE4V[`\x01\x90\x91\x01\x90a\x15OV[Pa\x15m\x81\x84a\r-V[Q\x15\x15a\x15JV[`@Qa\x15\x83` \x82a\x08*V[_\x81R_\x80[\x81\x81\x10a\x15\xD0WPP`@Q\x90a\x15\xA1` \x83a\x08*V[_\x82R_\x80[\x81\x81\x10a\x15\xB9WPPa\x02`R`\xC0RV[` \x90a\x15\xC4a\x0C\x94V[\x82\x82\x87\x01\x01R\x01a\x15\xA7V[` \x90a\x15\xDBa\x0C&V[\x82\x82\x86\x01\x01R\x01a\x15\x89V[Q\x90`\x01`\x01`\xA0\x1B\x03\x82\x16\x82\x03a\x01\xE6WV[\x91\x93\x92a\x16\x06a\x08bV[\x94``\x82\x80Q\x81\x01\x03\x12a\x01\xE6Wa\x16 ` \x83\x01a\x15\xE7V[\x91```@\x82\x01Q\x91\x01Q\x92`\xFF\x84\x16\x80\x94\x03a\x01\xE6W`\x01`\x01`\xA0\x1B\x03\x16\x80\x15\x80\x15a\x16\xE3W[a\x16\xDBW\x84\x91\x86\x91`\x02\x86\x03a\x16\xA9Wa\x16c\x95Pa\x1FQV[\x91[\x82\x15a\t:W\x90a\x16u\x91a\x1B\xCFV[\x83R`@Qa\x16\x85`@\x82a\x08*V[`\x01\x81R` 6\x81\x83\x017`\x05a\x16\x9B\x82a\x0C\xFCV[R` \x84\x01Ra\t.a\x1C\x1AV[\x93\x94\x90\x92P`\x03\x14\x15\x90Pa\x0B W`\x01`\x01`\xA0\x1B\x03\x16\x90\x81\x15a\x0B W\x84a\x16\xD5\x93\x92\x85\x92a\x1E\x94V[\x91a\x16eV[PPPPPPV[P\x80;\x15a\x16IV[Q\x90\x81\x15\x15\x82\x03a\x01\xE6WV[\x91\x93\x92a\x17\x04a\x08bV[\x94`\x80\x82\x80Q\x81\x01\x03\x12a\x01\xE6Wa\x17\x1E` \x83\x01a\x15\xE7V[\x91`@\x81\x01Qa\x175`\x80``\x84\x01Q\x93\x01a\x16\xECV[\x93`\x01`\x01`\xA0\x1B\x03\x16\x80\x15\x80\x15a\x17\xA0W[a\x17\x97W\x82\x82\x14a\x17\x97W\x90a\x17`\x94\x93\x92\x91a\"yV[\x91\x82\x15a\t:W\x90a\x17q\x91a\x1B\xCFV[\x83R`@Qa\x17\x81`@\x82a\x08*V[`\x01\x81R` 6\x81\x83\x017`\x03a\x16\x9B\x82a\x0C\xFCV[PPPPPPPV[P\x80;\x15a\x17HV[\x91\x93\x92\x93a\x17\xB5a\x08bV[\x94`@\x81\x80Q\x81\x01\x03\x12a\x01\xE6Wa\x17\xDB`@a\x17\xD4` \x84\x01a\x15\xE7V[\x92\x01a\x16\xECV[P`\x01`\x01`\xA0\x1B\x03\x16\x80\x15\x80\x15a\x17\xFDW[a\t\x9EW\x90\x83a\t\x06\x92a#FV[P\x80;\x15a\x17\xEEV[\x91\x93\x92\x90a\x18\x12a\x08bV[\x94\x82Q\x83\x01\x90\x83` \x83\x01\x92\x03`\xE0\x81\x12a\x01\xE6W`\xA0\x13a\x01\xE6W`@Q\x93a\x18;\x85a\x08\x0FV[a\x18G` \x82\x01a\x15\xE7V[\x85Ra\x18U`@\x82\x01a\x15\xE7V[\x94` \x81\x01\x95\x86R``\x82\x01Q\x95b\xFF\xFF\xFF\x87\x16\x87\x03a\x01\xE6W`@\x82\x01\x96\x87R`\x80\x83\x01Q\x80`\x02\x0B\x81\x03a\x01\xE6W``\x83\x01Ra\x18\x96`\xA0\x84\x01a\x15\xE7V[`\x80\x83\x01Ra\x18\xA7`\xC0\x84\x01a\x16\xECV[\x92`\xE0\x81\x01Q\x90`\x01`\x01`@\x1B\x03\x82\x11a\x01\xE6W\x01\x85`?\x82\x01\x12\x15a\x01\xE6W` \x81\x01Q\x90a\x18\xD7\x82a\x08\x86V[\x96a\x18\xE5`@Q\x98\x89a\x08*V[\x82\x88R`@\x82\x84\x01\x01\x11a\x01\xE6W\x81_\x92`@` \x93\x01\x83\x8A\x01^\x87\x01\x01R\x82\x15a\x19\x97W\x81Q`\x01`\x01`\xA0\x1B\x03\x89\x81\x16\x91\x16\x14\x90\x81a\x19\x80W[P[\x15a\x17\x97W\x90a\x194\x93\x92\x91a#\x8AV[\x92\x83\x15a\t\x9EW\x91a\x19Mb\xFF\xFF\xFF\x92a\t.\x94a\x1B\xCFV[\x86R`@Qa\x19]`@\x82a\x08*V[`\x01\x81R` 6\x81\x83\x017`\x02a\x19s\x82a\x0C\xFCV[R` \x87\x01RQ\x16a\x1CAV[Q`\x01`\x01`\xA0\x1B\x03\x87\x81\x16\x91\x16\x14\x90P_a\x19!V[Q`\x01`\x01`\xA0\x1B\x03\x88\x81\x16\x91\x16\x14\x80\x15a\x19#WP\x80Q`\x01`\x01`\xA0\x1B\x03\x86\x81\x16\x91\x16\x14a\x19#V[=\x15a\x19\xECW=\x90a\x19\xD3\x82a\x08\x86V[\x91a\x19\xE1`@Q\x93\x84a\x08*V[\x82R=_` \x84\x01>V[``\x90V[Q\x90`\x01`\x01`p\x1B\x03\x82\x16\x82\x03a\x01\xE6WV[\x91\x90\x82\x01\x80\x92\x11a\x0B\xB8WV[\x90a\x1A\x1D\x90\x82a$\x9AV[`\x01`\x01`\xA0\x1B\x03\x81\x16\x15\x80\x15a\x1B\xC6W[a\x1B\xBFW_\x80`@Q` \x81\x01\x90c\x02@\xBCk`\xE2\x1B\x82R`\x04\x81Ra\x1AV`$\x82a\x08*V[Q\x90\x84Z\xFA\x91a\x1Ada\x19\xC2V[\x92\x15\x80\x15a\x1B\xB4W[a\x1B~W``\x83\x80Q\x81\x01\x03\x12a\x01\xE6Wa\x1A\x8A` \x84\x01a\x19\xF1V[\x91``a\x1A\x99`@\x86\x01a\x19\xF1V[\x94\x01Qc\xFF\xFF\xFF\xFF\x81\x16\x03a\x01\xE6W_\x80\x91`@Q` \x81\x01\x90c\r\xFE\x16\x81`\xE0\x1B\x82R`\x04\x81Ra\x1A\xCC`$\x82a\x08*V[Q\x91Z\xFAa\x1A\xD8a\x19\xC2V[\x90\x15\x80\x15a\x1B\xA9W[a\x1B\xA0W` \x81\x80Q\x81\x01\x03\x12a\x01\xE6W`\x01`\x01`\xA0\x1B\x03\x90a\x1B\x07\x90` \x01a\x15\xE7V[`\x01`\x01`\xA0\x1B\x03\x90\x92\x16\x91\x16\x03a\x1B\x8EW`\x01`\x01`p\x1B\x03\x91\x82\x16\x91\x16[\x80\x15\x91\x82\x80\x15a\x1B\x86W[a\x1B~Wa\x03\xE5\x84\x02\x93\x80\x85\x04a\x03\xE5\x14\x90\x15\x17\x15a\x0B\xB8Wa\x1BU\x90\x84a\x0B\xA5V[\x91a\x03\xE8\x82\x02\x91\x82\x04a\x03\xE8\x14\x17\x15a\x0B\xB8Wa\x1B{\x92a\x1Bu\x91a\x1A\x05V[\x90a\x0B\xCCV[\x90V[PPPP_\x90V[P\x80\x15a\x1B2V[`\x01`\x01`p\x1B\x03\x90\x81\x16\x91\x16a\x1B'V[PPPPP_\x90V[P` \x81Q\x10a\x1A\xE1V[P``\x83Q\x10a\x1AmV[PPP_\x90V[P\x80;\x15a\x1A/V[\x91\x90a\x1C\x0B`@Qa\x1B\xE2``\x82a\x08*V[`\x02\x81R`@6` \x83\x017\x80\x94a\x1B\xF9\x82a\x0C\xFCV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90Ra\r\x1DV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90RV[`@Q\x90a\x1C)`@\x83a\x08*V[`\x01\x82R` 6\x81\x84\x017_a\x1C>\x83a\x0C\xFCV[RV[\x90`@Q\x91a\x1CQ`@\x84a\x08*V[`\x01\x83R` 6\x81\x85\x017b\xFF\xFF\xFFa\x1Ci\x84a\x0C\xFCV[\x91\x16\x90RV[\x91\x92\x90\x92_\x93_\x93a\x1C\x82\x83\x83\x83a%9V[\x80a\x1C\xEBW[Pa\x1C\x94\x83\x83\x83a%\xB0V[\x86\x81\x11a\x1C\xDEW[Pa\x1C\xA8\x83\x83\x83a&\x04V[\x86\x81\x11a\x1C\xCFW[P\x90a\x1C\xBC\x92\x91a&XV[\x83\x81\x11a\x1C\xC6WPV[\x92Pa'\x10\x91PV[\x95Pa\x0B\xB8\x94Pa\x1C\xBCa\x1C\xB0V[\x95Pa\x01\xF4\x94P_a\x1C\x9CV[\x95P`d\x94P_a\x1C\x88V[\x92\x91\x90`@Q\x90a\x1D\t`\x80\x83a\x08*V[`\x03\x82R``6` \x84\x017\x81\x94a\x1D \x83a\x0C\xFCV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90Ra\x1D6\x82a\r\x1DV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90R\x80Q`\x02\x10\x15a\r\tW`\x01`\x01`\xA0\x1B\x03\x90\x91\x16``\x91\x90\x91\x01RV[`@Q\x90a\x1Dp``\x83a\x08*V[`\x02\x82R`@6` \x84\x017`\x01a\x1C>\x83\x82a\x1D\x8C\x82a\x0C\xFCV[Ra\r\x1DV[\x91\x90b\xFF\xFF\xFFa\x1Ci`@Qa\x1D\xA9``\x82a\x08*V[`\x02\x81R`@6` \x83\x017\x80\x95\x83a\x1D\xC1\x83a\x0C\xFCV[\x91\x16\x90Ra\r\x1DV[\x90\x81Q`\x02\x81\x10a\x1EjW_\x19\x81\x01\x90\x81\x11a\x0B\xB8Wa\x1D\xE9\x81a\x0C\xCAV[\x90_[\x81\x81\x10a\x1EGWPP\x90\x91P`@Q` \x81\x01\x81\x81\x93` \x81Q\x93\x91\x01\x92_[\x81\x81\x10a\x1E.WPPa\x1E(\x92P\x03`\x1F\x19\x81\x01\x83R\x82a\x08*V[Q\x90 \x90V[\x84Q\x83R` \x94\x85\x01\x94\x86\x94P\x90\x92\x01\x91`\x01\x01a\x1E\x0CV[\x80`@a\x1EV`\x01\x93\x88a\r-V[Q\x01Qa\x1Ec\x82\x86a\r-V[R\x01a\x1D\xECV[P_\x91PV[\x80Q\x80\x83R` \x92\x91\x81\x90\x84\x01\x84\x84\x01^_\x82\x82\x01\x84\x01R`\x1F\x01`\x1F\x19\x16\x01\x01\x90V[\x90_\x80\x94a\x1F\x12\x82\x95a\x1F\x04` \x99`@Q\x90a\x1E\xB1\x8C\x83a\x08*V[\x86\x82R`@Qc\x07\xD2E\xE9`\xE4\x1B\x8D\x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x99\x8A\x16`$\x83\x01R\x94\x89\x16`D\x82\x01R\x95\x90\x97\x16`d\x86\x01R`\x84\x85\x01\x96\x90\x96R`\xA0`\xA4\x85\x01R\x90\x94\x83\x91\x90`\xC4\x83\x01\x90a\x1EpV[\x03`\x1F\x19\x81\x01\x83R\x82a\x08*V[Q\x92Z\xF1\x90a\x1F\x1Fa\x19\xC2V[\x91\x15\x80\x15a\x1FGW[a\x1FAW\x81Q\x81\x83\x01\x92\x01\x81\x01\x82\x90\x03\x12a\x01\xE6WQ\x90V[PP_\x90V[P\x80\x82Q\x10a\x1F(V[\x90\x91\x93\x92\x93`@\x94\x85Q\x93a\x1Ff\x87\x86a\x08*V[`\x01\x85R`\x1F\x19\x87\x01_[\x81\x81\x10a\"EWPP\x86Q` \x96a\x1F\x89\x88\x83a\x08*V[_\x82R\x88Q\x92a\x1F\x98\x84a\x08\x0FV[\x83R_\x88\x84\x01R`\x01\x89\x84\x01R``\x83\x01R`\x80\x82\x01Ra\x1F\xB8\x85a\x0C\xFCV[Ra\x1F\xC2\x84a\x0C\xFCV[P``\x93\x86Q\x91a\x1F\xD3\x86\x84a\x08*V[`\x02\x83R\x86\x83\x01\x93`\x1F\x19\x87\x016\x867a\x1F\xEC\x84a\x0C\xFCV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90Ra \x02\x83a\r\x1DV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90R\x86Qa \x1A\x81a\x07\xF4V[0\x81R\x86\x81\x01\x90_\x82R\x88\x81\x01\x920\x84R\x88\x88\x83\x01\x95_\x87R\x8B\x80Q\x9Ac|&\x837`\xE1\x1B\x84\x8D\x01R\x8Ba\x01\x04\x81\x01\x91_`$\x83\x01R`\xE0`D\x83\x01R\x86Q\x80\x93Ra\x01$\x82\x01\x90\x86a\x01$\x85`\x05\x1B\x85\x01\x01\x98\x01\x94_\x93[\x85\x85\x10a!\xE3WPPPPP\x8B\x85\x03`#\x19\x01`d\x8D\x01RPPQ\x80\x83R\x91\x01\x95\x90_[\x8A\x82\x82\x10a!\xC6WPP\x91Q`\x01`\x01`\xA0\x1B\x03\x90\x81\x16`\x84\x8A\x01R\x92Q\x15\x15`\xA4\x89\x01RPP\x90Q\x16`\xC4\x85\x01RQ\x15\x15`\xE4\x84\x01R\x82\x90\x03`\x1F\x19\x81\x01\x83R_\x92\x83\x92\x90\x91a \xE8\x90\x83a\x08*V[\x82\x85\x83Q\x93\x01\x91Z\xF1a \xF9a\x19\xC2V[\x90\x15\x80\x15a!\xBCW[a\x1B\xBFW\x80Q\x81\x01\x90\x82\x81\x81\x84\x01\x93\x03\x12a\x01\xE6W\x82\x81\x01Q\x90`\x01`\x01`@\x1B\x03\x82\x11a\x01\xE6W\x01\x92\x81`?\x85\x01\x12\x15a\x01\xE6W\x82\x84\x01Q\x90a!E\x82a\x08KV[\x94a!R\x82Q\x96\x87a\x08*V[\x82\x86R\x84\x80\x80\x88\x01\x94`\x05\x1B\x83\x01\x01\x01\x93\x84\x11a\x01\xE6W\x01\x90[\x82\x82\x10a!\xADWPPPP`\x02\x81Q\x10a!\xA8Wa!\x89\x90a\r\x1DV[Q_\x81\x12\x15a!\xA8W`\x01`\xFF\x1B\x81\x14a\x0B\xB8Wa\x1B{\x90_\x03a(\x87V[P_\x90V[\x81Q\x81R\x90\x83\x01\x90\x83\x01a!lV[P\x82\x81Q\x10a!\x02V[\x83Q`\x01`\x01`\xA0\x1B\x03\x16\x89R\x97\x88\x01\x97\x90\x92\x01\x91`\x01\x01a \x97V[\x88\x92\x94\x96\x99`\xA0`\x80`\x01\x96\x98\x9A\x9B\x94a\"0\x94a\x01#\x19\x90\x85\x03\x01\x8AR\x8DQ\x90\x81Q\x85R\x86\x82\x01Q\x87\x86\x01R\x80\x82\x01Q\x90\x85\x01R\x88\x81\x01Q\x89\x85\x01R\x01Q\x91\x81`\x80\x82\x01R\x01\x90a\x1EpV[\x98\x01\x93\x01\x93\x01\x90\x92\x8F\x93\x8F\x96\x95\x93\x94\x8Fa sV[` \x90\x89Qa\"S\x81a\x08\x0FV[_\x81R_\x83\x82\x01R_\x8B\x82\x01R_``\x82\x01R```\x80\x82\x01R\x82\x82\x8A\x01\x01R\x01a\x1FqV[_\x94\x85\x94\x91\x93\x92\x90\x15a#\x10Wa\"\x92a\"\x98\x91a(\x9CV[\x92a(\x9CV[`@Q\x92c^\rD?`\xE0\x1B` \x85\x01R`\x0F\x0B`$\x84\x01R`\x0F\x0B`D\x83\x01R`d\x82\x01R`d\x81Ra\"\xCD`\x84\x82a\x08*V[\x90[` \x82Q\x92\x01\x90Z\xFAa\"\xE0a\x19\xC2V[\x90\x15\x80\x15a#\x05W[a!\xA8W` \x81Q\x91\x81\x80\x82\x01\x93\x84\x92\x01\x01\x03\x12a\x01\xE6WQ\x90V[P` \x81Q\x10a\"\xE9V[\x91`@Q\x92cUmn\x9F`\xE0\x1B` \x85\x01R`$\x84\x01R`D\x83\x01R`d\x82\x01R`d\x81Ra#@`\x84\x82a\x08*V[\x90a\"\xCFV[_\x92\x83\x92`@Q\x90` \x82\x01\x92cx\xA0Q\xAD`\xE1\x1B\x84R`$\x83\x01R`\x01\x80`\xA0\x1B\x03\x16`D\x82\x01R`D\x81Ra#~`d\x82a\x08*V[Q\x91Z\xFAa\"\xE0a\x19\xC2V[\x90\x91`\x01`\x80\x1B\x81\x10\x15a$\x8DWa$k_\x94\x93a\x1F\x04\x86\x95`@Q\x95a#\xB0\x87a\x07\xF4V[\x86R` \x86\x01\x92\x15\x15\x83R`\x01`\x01`\x80\x1B\x03`@\x87\x01\x95\x16\x85R``\x86\x01\x90\x81R`\x01`\x01`\x80\x1B\x03`@Q\x95\x86\x94` \x86\x01\x98c\xAA\x9D!\xCB`\xE0\x1B\x8AR` `$\x88\x01RQ`\x01\x80`\xA0\x1B\x03\x81Q\x16`D\x88\x01R`\x01\x80`\xA0\x1B\x03` \x82\x01Q\x16`d\x88\x01Rb\xFF\xFF\xFF`@\x82\x01Q\x16`\x84\x88\x01R``\x81\x01Q`\x02\x0B`\xA4\x88\x01R`\x80`\x01\x80`\xA0\x1B\x03\x91\x01Q\x16`\xC4\x87\x01RQ\x15\x15`\xE4\x86\x01RQ\x16a\x01\x04\x84\x01RQa\x01\0a\x01$\x84\x01Ra\x01D\x83\x01\x90a\x1EpV[Q\x90\x82s9r\xC0\x0F~\xD4\x88^\x14X#\xEB|eSu\xD2u\xA1\xC5Z\xF1a\"\xE0a\x19\xC2V[c5'\x8D\x12_R`\x04`\x1C\xFD[`@Qc\xE6\xA49\x05`\xE0\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x92\x90\x91\x16`D\x80\x83\x01\x91\x90\x91R\x81R_\x91\x82\x91a$\xDA`d\x82a\x08*V[Q\x90s\xF1\xD7\xCCd\xFBDR\xF0\\I\x81&1.\xBE)\xF3\x0F\xBC\xF9Z\xFAa$\xFBa\x19\xC2V[\x90\x15\x80\x15a%.W[a!\xA8W` \x81\x80Q\x81\x01\x03\x12a\x01\xE6W`\x01`\x01`\xA0\x1B\x03\x90a%*\x90` \x01a\x15\xE7V[\x16\x90V[P` \x81Q\x10a%\x04V[`@QccR\x815`\xE1\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x91\x90\x92\x16`D\x83\x01R`d\x80\x83\x01\x93\x90\x93R`\x84\x82\x01\x92\x90\x92R_`\xA4\x80\x83\x01\x82\x90R\x82R\x91\x82\x91a%\x8E`\xC4\x82a\x08*V[Q\x90\x82sa\xFF\xE0\x14\xBA\x17\x98\x9Et<_l\xB2\x1B\xF9iu0\xB2\x1EZ\xF1a\"\xE0a\x19\xC2V[`@QccR\x815`\xE1\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x91\x90\x92\x16`D\x83\x01R`d\x82\x01\x92\x90\x92Ra\x01\xF4`\x84\x82\x01R_`\xA4\x80\x83\x01\x82\x90R\x82R\x91\x82\x91a%\x8E`\xC4\x82a\x08*V[`@QccR\x815`\xE1\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x91\x90\x92\x16`D\x83\x01R`d\x82\x01\x92\x90\x92Ra\x0B\xB8`\x84\x82\x01R_`\xA4\x80\x83\x01\x82\x90R\x82R\x91\x82\x91a%\x8E`\xC4\x82a\x08*V[`@QccR\x815`\xE1\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x91\x90\x92\x16`D\x83\x01R`d\x82\x01\x92\x90\x92Ra'\x10`\x84\x82\x01R_`\xA4\x80\x83\x01\x82\x90R\x82R\x91\x82\x91a%\x8E`\xC4\x82a\x08*V[\x90\x80\x15a\x1FAW\x81a&\xBD\x91a\x1A\x05V[g\r\xE0\xB6\xB3\xA7d\0\0\x82\x02\x91\x81\x81\x15g\r\xE0\xB6\xB3\xA7d\0\0\x83\x86\x04\x14\x17\x02\x15a'\xA9WP\x90\x04[`\x03\x81\x02\x90`d\x81\x15`\x03\x83\x85\x04\x14\x17\x02\x15a'KWP`d\x90\x04[f\n\xA8{\xEES\x80\0\x81\x01g\r\xE0\xB6\xB3\xA7d\0\0\x11\x15a'DWg\r\xD6\x0E7\xB9\x10\x80\0\x03[g\x01cEx]\x8A\0\0\x81\x11\x15a'7W\x90V[Pg\x01cEx]\x8A\0\0\x90V[P_a'$V[`d`\x03_\x19\x81\x84\t\x84\x81\x10\x85\x01\x90\x03\x92\t\x90\x80`d\x11\x15a'\x9CW\x82\x82\x11\x90\x03`\xFE\x1B\x91\x03`\x02\x1C\x17\x7F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\)\x02a'\0V[c\xAEG\xF7\x02_R`\x04`\x1C\xFD[\x81g\r\xE0\xB6\xB3\xA7d\0\0_\x19\x81\x84\t\x85\x81\x10\x86\x01\x90\x03\x92\t\x90\x82_\x03\x83\x16\x92\x81\x81\x11\x15a'\x9CW\x83\x90\x04\x80`\x03\x02`\x02\x18\x80\x82\x02`\x02\x03\x02\x80\x82\x02`\x02\x03\x02\x80\x82\x02`\x02\x03\x02\x80\x82\x02`\x02\x03\x02\x80\x82\x02`\x02\x03\x02\x80\x91\x02`\x02\x03\x02\x93`\x01\x84\x84\x83\x03\x04\x94\x80_\x03\x04\x01\x92\x11\x90\x03\x02\x17\x02a&\xE4V[\x90a('a\x0C&V[\x82\x81R\x82Q\x80\x15a(\x82W_\x19\x81\x01\x90\x81\x11a\x0B\xB8Wa(I`\x80\x91\x85a\r-V[Q\x01Q` \x82\x01R_\x90\x81[\x84Q\x83\x10\x15a(xWa(p`\x01\x91`\xA0a\x14!\x86\x89a\r-V[\x92\x01\x91a(UV[`@\x82\x01R\x92PPV[P\x91PV[_\x81\x12\x15a\x1B{Wc5'\x8D\x12_R`\x04`\x1C\xFD[`\x01`\x7F\x1B\x81\x10\x15a$\x8DW`\x0F\x0B\x90V\xFE\xA1dsolcC\0\x08\"\0\n",
    );
    /// The runtime bytecode of the contract, as deployed on the network.
    ///
    /// ```text
    ///0x6103a06040526004361015610012575f80fd5b5f3560e01c806321bf9f26146104ee57806381c6ecd6146101ea5763c036c8ea1461003b575f80fd5b346101e65760a03660031901126101e65761005461069c565b61005c6106b2565b6084359160643591604435906001600160401b0385116101e657366023860112156101e65784600401356001600160401b0381116101e65785019260248401933685116101e6576040906100ae610862565b506100bb878686866108a1565b879003126101e65760248601359560ff87168097036101e6576044810135906001600160401b0382116101e65701846043820112156101e65760248101359061010382610886565b95610111604051978861082a565b828752604482840101116101e657815f9260446020930183890137860101526002860361017957610143949550611806565b60608101511561016a576101669161015a91610bea565b604051918291826106c8565b0390f35b630541871160e01b5f5260045ffd5b600886036101915761018c9495506117a9565b610143565b600386036101a45761018c9495506116f9565b600986036101b75761018c9495506115fb565b85600581036101d457631602da9b60e21b5f52600560045260245ffd5b631602da9b60e21b5f5260045260245ffd5b5f80fd5b346101e65760403660031901126101e6576004356001600160401b0381116101e657366023820112156101e6578060040135906102268261084b565b90610234604051928361082a565b8282526024602083019360051b820101903682116101e65760248101935b8285106103d45761026560243585610d41565b60c05161026051604051918291604083016040845281518091526060840190602060608260051b8701019301915f905b82821061031d57505050508281036020840152602080835192838152019201905f5b8181106102c5575050500390f35b91935091602060e060019260c0875180518352848101518584015260408101516040840152606081015160608401526080810151608084015260a081015160a0840152015160c08201520194019101918493926102b7565b91939092949550605f1987820301825284519060608101918051926060835283518091526020608084019401905f905b80821061038057505050600192602092604080848680960151868501520151910152960192019201869594939192610295565b909194602060e060019260c0895180518352848101518584015260408101516040840152606081015160608401526080810151608084015260a081015160a0840152015160c082015201960192019061034d565b84356001600160401b0381116101e6578201606060231982360301126101e65760405190610401826107aa565b60248101356001600160401b0381116101e65760249082010136601f820112156101e65780356104308161084b565b9161043e604051938461082a565b818352602060e08185019302820101903682116101e657602001915b81831061048a57505050916064602094928594835260448101358584015201356040820152815201940193610252565b60e0833603126101e657602060e0916040516104a5816107d9565b85358152828601358382015260408601356040820152606086013560608201526080860135608082015260a086013560a082015260c086013560c082015281520192019161045a565b346101e65760803660031901126101e65761050761069c565b61050f6106b2565b6064359160443561051e610862565b5061052b848285856108a1565b6105368184846108ef565b9261054282828561093f565b8460608083015191015110610694575b506001600160a01b0383167382af49447d8a07e3bd95bd0d56f35241523fbab18114158061066d575b61060b575b73af88d065e77c8cc2239327c5edb3a432268e58311415806105e4575b6105bc575b50505060608101511561016a576101669161015a91610bea565b6105c592610b27565b60608101516060830151106105dc575b80806105a2565b9050826105d5565b506001600160a01b03811673af88d065e77c8cc2239327c5edb3a432268e5831141561059d565b6106168383866109a4565b610621848487610a8e565b906060810151606088015110610665575b506060810151606087015110610649575b50610580565b945073af88d065e77c8cc2239327c5edb3a432268e5831610643565b955087610632565b506001600160a01b0382167382af49447d8a07e3bd95bd0d56f35241523fbab1141561057b565b935085610552565b600435906001600160a01b03821682036101e657565b602435906001600160a01b03821682036101e657565b6020815260a0810191805192608060208401528351809152602060c084019401905f5b81811061078b57505050602081810151838503601f190160408501528051808652948201949101905f5b81811061077257505050604081015192601f19838203016060840152602080855192838152019401905f5b818110610757575050506060608091015191015290565b825162ffffff16865260209586019590920191600101610740565b825160ff16865260209586019590920191600101610715565b82516001600160a01b03168652602095860195909201916001016106eb565b606081019081106001600160401b038211176107c557604052565b634e487b7160e01b5f52604160045260245ffd5b60e081019081106001600160401b038211176107c557604052565b608081019081106001600160401b038211176107c557604052565b60a081019081106001600160401b038211176107c557604052565b90601f801991011681019081106001600160401b038211176107c557604052565b6001600160401b0381116107c55760051b60200190565b6040519061086f826107f4565b5f6060838181528160208201528160408201520152565b6001600160401b0381116107c557601f01601f191660200190565b6001600160a01b039081169116146108e057156108d1576103e8106108c257565b632a8406b960e01b5f5260045ffd5b63857e4aa960e01b5f5260045ffd5b634181f73f60e11b5f5260045ffd5b909291926109066108fe610862565b948284611a12565b91821561093a579061091791611bcf565b8352610921611c1a565b602084015261092e611c1a565b60408401526060830152565b505050565b9092919261095661094e610862565b948284611c6f565b919092831561099e5761092e929161096d91611bcf565b855260405161097d60408261082a565b6001815260203681830137600161099382610cfc565b526020860152611c41565b50505050565b909291926109cf6109b3610862565b947382af49447d8a07e3bd95bd0d56f35241523fbab184611a12565b801561093a576109f490827382af49447d8a07e3bd95bd0d56f35241523fbab1611a12565b91821561093a57907382af49447d8a07e3bd95bd0d56f35241523fbab1610a1a92611cf7565b8352604051610a2a60608261082a565b60028152604090813660208301375f610a4282610cfc565b525f610a4d82610d1d565b52602085015260405190610a6260608361082a565b600282523660208301375f610a7682610cfc565b525f610a8182610d1d565b5260408401526060830152565b90929192610ab9610a9d610862565b947382af49447d8a07e3bd95bd0d56f35241523fbab184611c6f565b90801561099e57610adf90837382af49447d8a07e3bd95bd0d56f35241523fbab1611c6f565b9290938415610b205761092e9392917382af49447d8a07e3bd95bd0d56f35241523fbab1610b0c92611cf7565b8652610b16611d61565b6020870152611d92565b5050505050565b90929192610b52610b36610862565b9473af88d065e77c8cc2239327c5edb3a432268e583184611c6f565b90801561099e57610b78908373af88d065e77c8cc2239327c5edb3a432268e5831611c6f565b9290938415610b205761092e93929173af88d065e77c8cc2239327c5edb3a432268e5831610b0c92611cf7565b81810292918115918404141715610bb857565b634e487b7160e01b5f52601160045260245ffd5b8115610bd6570490565b634e487b7160e01b5f52601260045260245ffd5b90610bf3610862565b5080610bfd575090565b606082019081519061271003906127108211610bb85761271091610c2091610ba5565b04905290565b60405190610c33826107aa565b5f604083606081528260208201520152565b90610c4f8261084b565b610c5c604051918261082a565b8281528092610c6d601f199161084b565b01905f5b828110610c7d57505050565b602090610c88610c26565b82828501015201610c71565b60405190610ca1826107d9565b5f60c0838281528260208201528260408201528260608201528260808201528260a08201520152565b90610cd48261084b565b610ce1604051918261082a565b8281528092610cf2601f199161084b565b0190602036910137565b805115610d095760200190565b634e487b7160e01b5f52603260045260245ffd5b805160011015610d095760400190565b8051821015610d095760209160051b010190565b6102c052610120525f610260525f60c0526102c051511561157557610d696102c05151610cca565b610380525f5b6102c05151811015610dc857806002610d8d6001936102c051610d2d565b5151511015610dac575f5b610da58261038051610d2d565b5201610d6f565b610dc3610dbc826102c051610d2d565b5151611dca565b610d98565b50610dd66102c05151610cca565b906102c0515191610de68361084b565b92610df4604051948561082a565b808452610e03601f199161084b565b013660208501375f6102a0525f5b6102c05151811015610ecd57610e2a8161038051610d2d565b515f81610e71575b906001929115610e44575b5001610e11565b610e516102a05185610d2d565b5281610e606102a05187610d2d565b52816102a051016102a0525f610e3d565b5f5b6102a0518110610e84575b50610e32565b82610e8f8287610d2d565b5114610e9d57600101610e73565b92919050610eab8387610d2d565b51925f198414610bb857610ec460018095019188610d2d565b52909180610e7e565b50919091610edd6102a051610c45565b610260525f5f5b6102a05181106115365750610f09610efb8261084b565b60405160a05260a05161082a565b60a051819052601f1990610f1c9061084b565b015f5b81811061151d5750509060a05160c0525f610240525f610360525f60e0525b6102a05160e05110610f4e575050565b610f5a60e05183610d2d565b51610320526001610f6d60e05183610d2d565b5103610ff5575f5b6102c05151811015610fee5761032051610f928261038051610d2d565b5114610fa057600101610f75565b610fb0906102c093929351610d2d565b51610fc16102405161026051610d2d565b52610fd26102405161026051610d2d565b5060016102405101610240525b600160e0510160e05290610f3e565b5090610fdf565b909161100360e05183610d2d565b516101c052611010610c26565b50611019610c94565b506110266101c051610c45565b610340525f925f5b6102c05151811015611515576103205161104b8261038051610d2d565b511461105a575b60010161102e565b9360019061106b866102c051610d2d565b516110798261034051610d2d565b526110878161034051610d2d565b5001936101c0518503611052575092505b5f610300526110a961034051610cfc565b51516110b761034051610cfc565b5151515f198101908111610bb8576110ce91610d2d565b5192608084015180670de0b6b3a7640000810204670de0b6b3a76400001481151715610bb857606085015161110c91670de0b6b3a764000002610bcc565b6102e0525f5b61034051518110156111f15761112b8161034051610d2d565b51515161113b8261034051610d2d565b51516001198201828111610bb85761115291610d2d565b51906111618361034051610d2d565b5151915f198201918211610bb85761117e60809261118e94610d2d565b5161014052015161030051611a05565b610300526080610140510151670de0b6b3a7640000810290808204670de0b6b3a76400001490151715610bb85761014051606001516111cc91610bcc565b6102e05181116111e0575b50600101611112565b6102e05261014051945060016111d7565b50919092670de0b6b3a764000061121b61121260c0840151610300516126ac565b61030051610ba5565b046102805260a081015180603e810204603e1481151715610bb85761124261034051610cfc565b515161125061034051610cfc565b515151610220819052600119810111610bb857606491604061127c603e93600119610220510190610d2d565b5101516102005260c08451940151936040516101e05261129e6101e0516107d9565b6101e051526102005160206101e05101526101205160406101e05101526103005160606101e05101526102805160806101e0510152020460a06101e051015260c06101e05101526112f161034051610cfc565b51516101a0526101a051516101805261131f61130f6101805161084b565b604051610160526101605161082a565b610180516101605152601f196113376101805161084b565b015f5b8181106114fb5750505f5b600181018111610bb8576101a05151600182011015611391578061136e6001926101a051610d2d565b5161137c8261016051610d2d565b5261138a8161016051610d2d565b5001611345565b50906101a05151805f19810111610bb8576113c7906101e0516113ba5f19830161016051610d2d565b525f190161016051610d2d565b506113d46101605161281e565b915f610100525f5f6080525b610340515160805110156114555761142a9061010051602061140760805161034051610d2d565b51015111611438575b604061142160805161034051610d2d565b51015190611a05565b6080805160010190526113e0565b602061144960805161034051610d2d565b51015161010052611410565b90926040810151916040519261146a846107d9565b6103205184526101c051602085015261030051604085015261028051606085015261010051608085015260a084015260c08301526114ae6102405161026051610d2d565b526114bf6102405161026051610d2d565b506114cf6103605160a051610d2d565b526114df6103605160a051610d2d565b5060016102405101610240526001610360510161036052610fdf565b602090611506610c94565b8282610160510101520161133a565b509250611098565b602090611528610c94565b828260a05101015201610f1f565b60016115428286610d2d565b511180611562575b611557575b600101610ee4565b60019091019061154f565b5061156d8184610d2d565b51151561154a565b60405161158360208261082a565b5f81525f805b8181106115d0575050604051906115a160208361082a565b5f82525f805b8181106115b95750506102605260c052565b6020906115c4610c94565b828287010152016115a7565b6020906115db610c26565b82828601015201611589565b51906001600160a01b03821682036101e657565b919392611606610862565b946060828051810103126101e657611620602083016115e7565b91606060408201519101519260ff84168094036101e6576001600160a01b0316801580156116e3575b6116db5784918691600286036116a9576116639550611f51565b915b821561093a579061167591611bcf565b835260405161168560408261082a565b6001815260203681830137600561169b82610cfc565b52602084015261092e611c1a565b9394909250600314159050610b20576001600160a01b0316908115610b2057846116d593928592611e94565b91611665565b505050505050565b50803b15611649565b519081151582036101e657565b919392611704610862565b946080828051810103126101e65761171e602083016115e7565b9160408101516117356080606084015193016116ec565b936001600160a01b0316801580156117a0575b61179757828214611797579061176094939291612279565b91821561093a579061177191611bcf565b835260405161178160408261082a565b6001815260203681830137600361169b82610cfc565b50505050505050565b50803b15611748565b919392936117b5610862565b946040818051810103126101e6576117db60406117d4602084016115e7565b92016116ec565b506001600160a01b0316801580156117fd575b61099e57908361090692612346565b50803b156117ee565b91939290611812610862565b9482518301908360208301920360e081126101e65760a0136101e6576040519361183b8561080f565b611847602082016115e7565b8552611855604082016115e7565b946020810195865260608201519562ffffff871687036101e6576040820196875260808301518060020b81036101e657606083015261189660a084016115e7565b60808301526118a760c084016116ec565b9260e0810151906001600160401b0382116101e6570185603f820112156101e6576020810151906118d782610886565b966118e5604051988961082a565b828852604082840101116101e657815f92604060209301838a015e8701015282156119975781516001600160a01b038981169116149081611980575b505b15611797579061193493929161238a565b92831561099e579161194d62ffffff9261092e94611bcf565b865260405161195d60408261082a565b6001815260203681830137600261197382610cfc565b5260208701525116611c41565b516001600160a01b0387811691161490505f611921565b516001600160a01b038881169116148015611923575080516001600160a01b03868116911614611923565b3d156119ec573d906119d382610886565b916119e1604051938461082a565b82523d5f602084013e565b606090565b51906001600160701b03821682036101e657565b91908201809211610bb857565b90611a1d908261249a565b6001600160a01b038116158015611bc6575b611bbf575f806040516020810190630240bc6b60e21b825260048152611a5660248261082a565b5190845afa91611a646119c2565b92158015611bb4575b611b7e576060838051810103126101e657611a8a602084016119f1565b916060611a99604086016119f1565b94015163ffffffff8116036101e6575f80916040516020810190630dfe168160e01b825260048152611acc60248261082a565b51915afa611ad86119c2565b90158015611ba9575b611ba0576020818051810103126101e6576001600160a01b0390611b07906020016115e7565b6001600160a01b03909216911603611b8e576001600160701b0391821691165b801591828015611b86575b611b7e576103e58402938085046103e51490151715610bb857611b559084610ba5565b916103e882029182046103e8141715610bb857611b7b92611b7591611a05565b90610bcc565b90565b505050505f90565b508015611b32565b6001600160701b039081169116611b27565b50505050505f90565b506020815110611ae1565b506060835110611a6d565b5050505f90565b50803b15611a2f565b9190611c0b604051611be260608261082a565b6002815260403660208301378094611bf982610cfc565b6001600160a01b039091169052610d1d565b6001600160a01b039091169052565b60405190611c2960408361082a565b60018252602036818401375f611c3e83610cfc565b52565b9060405191611c5160408461082a565b600183526020368185013762ffffff611c6984610cfc565b91169052565b919290925f935f93611c82838383612539565b80611ceb575b50611c948383836125b0565b868111611cde575b50611ca8838383612604565b868111611ccf575b5090611cbc9291612658565b838111611cc65750565b92506127109150565b9550610bb89450611cbc611cb0565b95506101f494505f611c9c565b9550606494505f611c88565b92919060405190611d0960808361082a565b6003825260603660208401378194611d2083610cfc565b6001600160a01b039091169052611d3682610d1d565b6001600160a01b039091169052805160021015610d09576001600160a01b0390911660609190910152565b60405190611d7060608361082a565b6002825260403660208401376001611c3e8382611d8c82610cfc565b52610d1d565b919062ffffff611c69604051611da960608261082a565b600281526040366020830137809583611dc183610cfc565b91169052610d1d565b90815160028110611e6a575f198101908111610bb857611de981610cca565b905f5b818110611e475750509091506040516020810181819360208151939101925f5b818110611e2e575050611e28925003601f19810183528261082a565b51902090565b8451835260209485019486945090920191600101611e0c565b806040611e5660019388610d2d565b510151611e638286610d2d565b5201611dec565b505f9150565b805180835260209291819084018484015e5f828201840152601f01601f1916010190565b905f8094611f128295611f0460209960405190611eb18c8361082a565b8682526040516307d245e960e41b8d82019081526001600160a01b03998a1660248301529489166044820152959097166064860152608485019690965260a060a4850152909483919060c4830190611e70565b03601f19810183528261082a565b51925af190611f1f6119c2565b91158015611f47575b611f4157815181830192018101829003126101e6575190565b50505f90565b5080825110611f28565b9091939293604094855193611f66878661082a565b60018552601f1987015f5b8181106122455750508651602096611f89888361082a565b5f8252885192611f988461080f565b83525f8884015260018984015260608301526080820152611fb885610cfc565b52611fc284610cfc565b50606093865191611fd3868461082a565b6002835286830193601f198701368637611fec84610cfc565b6001600160a01b03909116905261200283610d1d565b6001600160a01b039091169052865161201a816107f4565b308152868101905f82528881019230845288888301955f87528b80519a637c26833760e11b848d01528b6101048101915f602483015260e060448301528651809352610124820190866101248560051b8501019801945f935b8585106121e35750505050508b85036023190160648d0152505051808352910195905f5b8a8282106121c657505091516001600160a01b0390811660848a01529251151560a4890152505090511660c485015251151560e4840152829003601f19810183525f92839290916120e8908361082a565b828583519301915af16120f96119c2565b901580156121bc575b611bbf57805181019082818184019303126101e65782810151906001600160401b0382116101e657019281603f850112156101e65782840151906121458261084b565b946121528251968761082a565b82865284808088019460051b830101019384116101e65701905b8282106121ad575050505060028151106121a85761218990610d1d565b515f8112156121a857600160ff1b8114610bb857611b7b905f03612887565b505f90565b8151815290830190830161216c565b5082815110612102565b83516001600160a01b031689529788019790920191600101612097565b889294969960a06080600196989a9b946122309461012319908503018a528d5190815185528682015187860152808201519085015288810151898501520151918160808201520190611e70565b98019301930190928f938f969593948f612073565b60209089516122538161080f565b5f81525f838201525f8b8201525f60608201526060608082015282828a01015201611f71565b5f9485949193929015612310576122926122989161289c565b9261289c565b60405192635e0d443f60e01b6020850152600f0b6024840152600f0b60448301526064820152606481526122cd60848261082a565b905b602082519201905afa6122e06119c2565b90158015612305575b6121a857602081519181808201938492010103126101e6575190565b5060208151106122e9565b916040519263556d6e9f60e01b60208501526024840152604483015260648201526064815261234060848261082a565b906122cf565b5f9283926040519060208201926378a051ad60e11b8452602483015260018060a01b031660448201526044815261237e60648261082a565b51915afa6122e06119c2565b9091600160801b81101561248d5761246b5f9493611f048695604051956123b0876107f4565b86526020860192151583526001600160801b036040870195168552606086019081526001600160801b03604051958694602086019863aa9d21cb60e01b8a52602060248801525160018060a01b03815116604488015260018060a01b03602082015116606488015262ffffff6040820151166084880152606081015160020b60a4880152608060018060a01b039101511660c487015251151560e4860152511661010484015251610100610124840152610144830190611e70565b519082733972c00f7ed4885e145823eb7c655375d275a1c55af16122e06119c2565b6335278d125f526004601cfd5b60405163e6a4390560e01b602082019081526001600160a01b0392831660248301529290911660448083019190915281525f9182916124da60648261082a565b519073f1d7cc64fb4452f05c498126312ebe29f30fbcf95afa6124fb6119c2565b9015801561252e575b6121a8576020818051810103126101e6576001600160a01b039061252a906020016115e7565b1690565b506020815110612504565b604051636352813560e11b602082019081526001600160a01b03928316602483015291909216604483015260648083019390935260848201929092525f60a4808301829052825291829161258e60c48261082a565b5190827361ffe014ba17989e743c5f6cb21bf9697530b21e5af16122e06119c2565b604051636352813560e11b602082019081526001600160a01b03928316602483015291909216604483015260648201929092526101f460848201525f60a4808301829052825291829161258e60c48261082a565b604051636352813560e11b602082019081526001600160a01b0392831660248301529190921660448301526064820192909252610bb860848201525f60a4808301829052825291829161258e60c48261082a565b604051636352813560e11b602082019081526001600160a01b039283166024830152919092166044830152606482019290925261271060848201525f60a4808301829052825291829161258e60c48261082a565b908015611f4157816126bd91611a05565b670de0b6b3a7640000820291818115670de0b6b3a7640000838604141702156127a9575090045b60038102906064811560038385041417021561274b5750606490045b660aa87bee5380008101670de0b6b3a7640000111561274457670dd60e37b9108000035b67016345785d8a00008111156127375790565b5067016345785d8a000090565b505f612724565b606460035f1981840984811085019003920990806064111561279c57828211900360fe1b910360021c177f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c28f5c2902612700565b63ae47f7025f526004601cfd5b81670de0b6b3a76400005f1981840985811086019003920990825f038316928181111561279c5783900480600302600218808202600203028082026002030280820260020302808202600203028082026002030280910260020302936001848483030494805f030401921190030217026126e4565b90612827610c26565b82815282518015612882575f198101908111610bb85761284960809185610d2d565b51015160208201525f90815b84518310156128785761287060019160a06114218689610d2d565b920191612855565b6040820152925050565b509150565b5f811215611b7b576335278d125f526004601cfd5b6001607f1b81101561248d57600f0b9056fea164736f6c6343000822000a
    /// ```
    #[rustfmt::skip]
    #[allow(clippy::all)]
    pub static DEPLOYED_BYTECODE: alloy_sol_types::private::Bytes = alloy_sol_types::private::Bytes::from_static(
        b"a\x03\xA0`@R`\x046\x10\x15a\0\x12W_\x80\xFD[_5`\xE0\x1C\x80c!\xBF\x9F&\x14a\x04\xEEW\x80c\x81\xC6\xEC\xD6\x14a\x01\xEAWc\xC06\xC8\xEA\x14a\0;W_\x80\xFD[4a\x01\xE6W`\xA06`\x03\x19\x01\x12a\x01\xE6Wa\0Ta\x06\x9CV[a\0\\a\x06\xB2V[`\x845\x91`d5\x91`D5\x90`\x01`\x01`@\x1B\x03\x85\x11a\x01\xE6W6`#\x86\x01\x12\x15a\x01\xE6W\x84`\x04\x015`\x01`\x01`@\x1B\x03\x81\x11a\x01\xE6W\x85\x01\x92`$\x84\x01\x936\x85\x11a\x01\xE6W`@\x90a\0\xAEa\x08bV[Pa\0\xBB\x87\x86\x86\x86a\x08\xA1V[\x87\x90\x03\x12a\x01\xE6W`$\x86\x015\x95`\xFF\x87\x16\x80\x97\x03a\x01\xE6W`D\x81\x015\x90`\x01`\x01`@\x1B\x03\x82\x11a\x01\xE6W\x01\x84`C\x82\x01\x12\x15a\x01\xE6W`$\x81\x015\x90a\x01\x03\x82a\x08\x86V[\x95a\x01\x11`@Q\x97\x88a\x08*V[\x82\x87R`D\x82\x84\x01\x01\x11a\x01\xE6W\x81_\x92`D` \x93\x01\x83\x89\x017\x86\x01\x01R`\x02\x86\x03a\x01yWa\x01C\x94\x95Pa\x18\x06V[``\x81\x01Q\x15a\x01jWa\x01f\x91a\x01Z\x91a\x0B\xEAV[`@Q\x91\x82\x91\x82a\x06\xC8V[\x03\x90\xF3[c\x05A\x87\x11`\xE0\x1B_R`\x04_\xFD[`\x08\x86\x03a\x01\x91Wa\x01\x8C\x94\x95Pa\x17\xA9V[a\x01CV[`\x03\x86\x03a\x01\xA4Wa\x01\x8C\x94\x95Pa\x16\xF9V[`\t\x86\x03a\x01\xB7Wa\x01\x8C\x94\x95Pa\x15\xFBV[\x85`\x05\x81\x03a\x01\xD4Wc\x16\x02\xDA\x9B`\xE2\x1B_R`\x05`\x04R`$_\xFD[c\x16\x02\xDA\x9B`\xE2\x1B_R`\x04R`$_\xFD[_\x80\xFD[4a\x01\xE6W`@6`\x03\x19\x01\x12a\x01\xE6W`\x045`\x01`\x01`@\x1B\x03\x81\x11a\x01\xE6W6`#\x82\x01\x12\x15a\x01\xE6W\x80`\x04\x015\x90a\x02&\x82a\x08KV[\x90a\x024`@Q\x92\x83a\x08*V[\x82\x82R`$` \x83\x01\x93`\x05\x1B\x82\x01\x01\x906\x82\x11a\x01\xE6W`$\x81\x01\x93[\x82\x85\x10a\x03\xD4Wa\x02e`$5\x85a\rAV[`\xC0Qa\x02`Q`@Q\x91\x82\x91`@\x83\x01`@\x84R\x81Q\x80\x91R``\x84\x01\x90` ``\x82`\x05\x1B\x87\x01\x01\x93\x01\x91_\x90[\x82\x82\x10a\x03\x1DWPPPP\x82\x81\x03` \x84\x01R` \x80\x83Q\x92\x83\x81R\x01\x92\x01\x90_[\x81\x81\x10a\x02\xC5WPPP\x03\x90\xF3[\x91\x93P\x91` `\xE0`\x01\x92`\xC0\x87Q\x80Q\x83R\x84\x81\x01Q\x85\x84\x01R`@\x81\x01Q`@\x84\x01R``\x81\x01Q``\x84\x01R`\x80\x81\x01Q`\x80\x84\x01R`\xA0\x81\x01Q`\xA0\x84\x01R\x01Q`\xC0\x82\x01R\x01\x94\x01\x91\x01\x91\x84\x93\x92a\x02\xB7V[\x91\x93\x90\x92\x94\x95P`_\x19\x87\x82\x03\x01\x82R\x84Q\x90``\x81\x01\x91\x80Q\x92``\x83R\x83Q\x80\x91R` `\x80\x84\x01\x94\x01\x90_\x90[\x80\x82\x10a\x03\x80WPPP`\x01\x92` \x92`@\x80\x84\x86\x80\x96\x01Q\x86\x85\x01R\x01Q\x91\x01R\x96\x01\x92\x01\x92\x01\x86\x95\x94\x93\x91\x92a\x02\x95V[\x90\x91\x94` `\xE0`\x01\x92`\xC0\x89Q\x80Q\x83R\x84\x81\x01Q\x85\x84\x01R`@\x81\x01Q`@\x84\x01R``\x81\x01Q``\x84\x01R`\x80\x81\x01Q`\x80\x84\x01R`\xA0\x81\x01Q`\xA0\x84\x01R\x01Q`\xC0\x82\x01R\x01\x96\x01\x92\x01\x90a\x03MV[\x845`\x01`\x01`@\x1B\x03\x81\x11a\x01\xE6W\x82\x01```#\x19\x826\x03\x01\x12a\x01\xE6W`@Q\x90a\x04\x01\x82a\x07\xAAV[`$\x81\x015`\x01`\x01`@\x1B\x03\x81\x11a\x01\xE6W`$\x90\x82\x01\x016`\x1F\x82\x01\x12\x15a\x01\xE6W\x805a\x040\x81a\x08KV[\x91a\x04>`@Q\x93\x84a\x08*V[\x81\x83R` `\xE0\x81\x85\x01\x93\x02\x82\x01\x01\x906\x82\x11a\x01\xE6W` \x01\x91[\x81\x83\x10a\x04\x8AWPPP\x91`d` \x94\x92\x85\x94\x83R`D\x81\x015\x85\x84\x01R\x015`@\x82\x01R\x81R\x01\x94\x01\x93a\x02RV[`\xE0\x836\x03\x12a\x01\xE6W` `\xE0\x91`@Qa\x04\xA5\x81a\x07\xD9V[\x855\x81R\x82\x86\x015\x83\x82\x01R`@\x86\x015`@\x82\x01R``\x86\x015``\x82\x01R`\x80\x86\x015`\x80\x82\x01R`\xA0\x86\x015`\xA0\x82\x01R`\xC0\x86\x015`\xC0\x82\x01R\x81R\x01\x92\x01\x91a\x04ZV[4a\x01\xE6W`\x806`\x03\x19\x01\x12a\x01\xE6Wa\x05\x07a\x06\x9CV[a\x05\x0Fa\x06\xB2V[`d5\x91`D5a\x05\x1Ea\x08bV[Pa\x05+\x84\x82\x85\x85a\x08\xA1V[a\x056\x81\x84\x84a\x08\xEFV[\x92a\x05B\x82\x82\x85a\t?V[\x84``\x80\x83\x01Q\x91\x01Q\x10a\x06\x94W[P`\x01`\x01`\xA0\x1B\x03\x83\x16s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1\x81\x14\x15\x80a\x06mW[a\x06\x0BW[s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1\x14\x15\x80a\x05\xE4W[a\x05\xBCW[PPP``\x81\x01Q\x15a\x01jWa\x01f\x91a\x01Z\x91a\x0B\xEAV[a\x05\xC5\x92a\x0B'V[``\x81\x01Q``\x83\x01Q\x10a\x05\xDCW[\x80\x80a\x05\xA2V[\x90P\x82a\x05\xD5V[P`\x01`\x01`\xA0\x1B\x03\x81\x16s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1\x14\x15a\x05\x9DV[a\x06\x16\x83\x83\x86a\t\xA4V[a\x06!\x84\x84\x87a\n\x8EV[\x90``\x81\x01Q``\x88\x01Q\x10a\x06eW[P``\x81\x01Q``\x87\x01Q\x10a\x06IW[Pa\x05\x80V[\x94Ps\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1a\x06CV[\x95P\x87a\x062V[P`\x01`\x01`\xA0\x1B\x03\x82\x16s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1\x14\x15a\x05{V[\x93P\x85a\x05RV[`\x045\x90`\x01`\x01`\xA0\x1B\x03\x82\x16\x82\x03a\x01\xE6WV[`$5\x90`\x01`\x01`\xA0\x1B\x03\x82\x16\x82\x03a\x01\xE6WV[` \x81R`\xA0\x81\x01\x91\x80Q\x92`\x80` \x84\x01R\x83Q\x80\x91R` `\xC0\x84\x01\x94\x01\x90_[\x81\x81\x10a\x07\x8BWPPP` \x81\x81\x01Q\x83\x85\x03`\x1F\x19\x01`@\x85\x01R\x80Q\x80\x86R\x94\x82\x01\x94\x91\x01\x90_[\x81\x81\x10a\x07rWPPP`@\x81\x01Q\x92`\x1F\x19\x83\x82\x03\x01``\x84\x01R` \x80\x85Q\x92\x83\x81R\x01\x94\x01\x90_[\x81\x81\x10a\x07WWPPP```\x80\x91\x01Q\x91\x01R\x90V[\x82Qb\xFF\xFF\xFF\x16\x86R` \x95\x86\x01\x95\x90\x92\x01\x91`\x01\x01a\x07@V[\x82Q`\xFF\x16\x86R` \x95\x86\x01\x95\x90\x92\x01\x91`\x01\x01a\x07\x15V[\x82Q`\x01`\x01`\xA0\x1B\x03\x16\x86R` \x95\x86\x01\x95\x90\x92\x01\x91`\x01\x01a\x06\xEBV[``\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[cNH{q`\xE0\x1B_R`A`\x04R`$_\xFD[`\xE0\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[`\x80\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[`\xA0\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[\x90`\x1F\x80\x19\x91\x01\x16\x81\x01\x90\x81\x10`\x01`\x01`@\x1B\x03\x82\x11\x17a\x07\xC5W`@RV[`\x01`\x01`@\x1B\x03\x81\x11a\x07\xC5W`\x05\x1B` \x01\x90V[`@Q\x90a\x08o\x82a\x07\xF4V[_``\x83\x81\x81R\x81` \x82\x01R\x81`@\x82\x01R\x01RV[`\x01`\x01`@\x1B\x03\x81\x11a\x07\xC5W`\x1F\x01`\x1F\x19\x16` \x01\x90V[`\x01`\x01`\xA0\x1B\x03\x90\x81\x16\x91\x16\x14a\x08\xE0W\x15a\x08\xD1Wa\x03\xE8\x10a\x08\xC2WV[c*\x84\x06\xB9`\xE0\x1B_R`\x04_\xFD[c\x85~J\xA9`\xE0\x1B_R`\x04_\xFD[cA\x81\xF7?`\xE1\x1B_R`\x04_\xFD[\x90\x92\x91\x92a\t\x06a\x08\xFEa\x08bV[\x94\x82\x84a\x1A\x12V[\x91\x82\x15a\t:W\x90a\t\x17\x91a\x1B\xCFV[\x83Ra\t!a\x1C\x1AV[` \x84\x01Ra\t.a\x1C\x1AV[`@\x84\x01R``\x83\x01RV[PPPV[\x90\x92\x91\x92a\tVa\tNa\x08bV[\x94\x82\x84a\x1CoV[\x91\x90\x92\x83\x15a\t\x9EWa\t.\x92\x91a\tm\x91a\x1B\xCFV[\x85R`@Qa\t}`@\x82a\x08*V[`\x01\x81R` 6\x81\x83\x017`\x01a\t\x93\x82a\x0C\xFCV[R` \x86\x01Ra\x1CAV[PPPPV[\x90\x92\x91\x92a\t\xCFa\t\xB3a\x08bV[\x94s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1\x84a\x1A\x12V[\x80\x15a\t:Wa\t\xF4\x90\x82s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1a\x1A\x12V[\x91\x82\x15a\t:W\x90s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1a\n\x1A\x92a\x1C\xF7V[\x83R`@Qa\n*``\x82a\x08*V[`\x02\x81R`@\x90\x816` \x83\x017_a\nB\x82a\x0C\xFCV[R_a\nM\x82a\r\x1DV[R` \x85\x01R`@Q\x90a\nb``\x83a\x08*V[`\x02\x82R6` \x83\x017_a\nv\x82a\x0C\xFCV[R_a\n\x81\x82a\r\x1DV[R`@\x84\x01R``\x83\x01RV[\x90\x92\x91\x92a\n\xB9a\n\x9Da\x08bV[\x94s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1\x84a\x1CoV[\x90\x80\x15a\t\x9EWa\n\xDF\x90\x83s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1a\x1CoV[\x92\x90\x93\x84\x15a\x0B Wa\t.\x93\x92\x91s\x82\xAFID}\x8A\x07\xE3\xBD\x95\xBD\rV\xF3RAR?\xBA\xB1a\x0B\x0C\x92a\x1C\xF7V[\x86Ra\x0B\x16a\x1DaV[` \x87\x01Ra\x1D\x92V[PPPPPV[\x90\x92\x91\x92a\x0BRa\x0B6a\x08bV[\x94s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1\x84a\x1CoV[\x90\x80\x15a\t\x9EWa\x0Bx\x90\x83s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1a\x1CoV[\x92\x90\x93\x84\x15a\x0B Wa\t.\x93\x92\x91s\xAF\x88\xD0e\xE7|\x8C\xC2#\x93'\xC5\xED\xB3\xA42&\x8EX1a\x0B\x0C\x92a\x1C\xF7V[\x81\x81\x02\x92\x91\x81\x15\x91\x84\x04\x14\x17\x15a\x0B\xB8WV[cNH{q`\xE0\x1B_R`\x11`\x04R`$_\xFD[\x81\x15a\x0B\xD6W\x04\x90V[cNH{q`\xE0\x1B_R`\x12`\x04R`$_\xFD[\x90a\x0B\xF3a\x08bV[P\x80a\x0B\xFDWP\x90V[``\x82\x01\x90\x81Q\x90a'\x10\x03\x90a'\x10\x82\x11a\x0B\xB8Wa'\x10\x91a\x0C \x91a\x0B\xA5V[\x04\x90R\x90V[`@Q\x90a\x0C3\x82a\x07\xAAV[_`@\x83``\x81R\x82` \x82\x01R\x01RV[\x90a\x0CO\x82a\x08KV[a\x0C\\`@Q\x91\x82a\x08*V[\x82\x81R\x80\x92a\x0Cm`\x1F\x19\x91a\x08KV[\x01\x90_[\x82\x81\x10a\x0C}WPPPV[` \x90a\x0C\x88a\x0C&V[\x82\x82\x85\x01\x01R\x01a\x0CqV[`@Q\x90a\x0C\xA1\x82a\x07\xD9V[_`\xC0\x83\x82\x81R\x82` \x82\x01R\x82`@\x82\x01R\x82``\x82\x01R\x82`\x80\x82\x01R\x82`\xA0\x82\x01R\x01RV[\x90a\x0C\xD4\x82a\x08KV[a\x0C\xE1`@Q\x91\x82a\x08*V[\x82\x81R\x80\x92a\x0C\xF2`\x1F\x19\x91a\x08KV[\x01\x90` 6\x91\x017V[\x80Q\x15a\r\tW` \x01\x90V[cNH{q`\xE0\x1B_R`2`\x04R`$_\xFD[\x80Q`\x01\x10\x15a\r\tW`@\x01\x90V[\x80Q\x82\x10\x15a\r\tW` \x91`\x05\x1B\x01\x01\x90V[a\x02\xC0Ra\x01 R_a\x02`R_`\xC0Ra\x02\xC0QQ\x15a\x15uWa\ria\x02\xC0QQa\x0C\xCAV[a\x03\x80R_[a\x02\xC0QQ\x81\x10\x15a\r\xC8W\x80`\x02a\r\x8D`\x01\x93a\x02\xC0Qa\r-V[QQQ\x10\x15a\r\xACW_[a\r\xA5\x82a\x03\x80Qa\r-V[R\x01a\roV[a\r\xC3a\r\xBC\x82a\x02\xC0Qa\r-V[QQa\x1D\xCAV[a\r\x98V[Pa\r\xD6a\x02\xC0QQa\x0C\xCAV[\x90a\x02\xC0QQ\x91a\r\xE6\x83a\x08KV[\x92a\r\xF4`@Q\x94\x85a\x08*V[\x80\x84Ra\x0E\x03`\x1F\x19\x91a\x08KV[\x016` \x85\x017_a\x02\xA0R_[a\x02\xC0QQ\x81\x10\x15a\x0E\xCDWa\x0E*\x81a\x03\x80Qa\r-V[Q_\x81a\x0EqW[\x90`\x01\x92\x91\x15a\x0EDW[P\x01a\x0E\x11V[a\x0EQa\x02\xA0Q\x85a\r-V[R\x81a\x0E`a\x02\xA0Q\x87a\r-V[R\x81a\x02\xA0Q\x01a\x02\xA0R_a\x0E=V[_[a\x02\xA0Q\x81\x10a\x0E\x84W[Pa\x0E2V[\x82a\x0E\x8F\x82\x87a\r-V[Q\x14a\x0E\x9DW`\x01\x01a\x0EsV[\x92\x91\x90Pa\x0E\xAB\x83\x87a\r-V[Q\x92_\x19\x84\x14a\x0B\xB8Wa\x0E\xC4`\x01\x80\x95\x01\x91\x88a\r-V[R\x90\x91\x80a\x0E~V[P\x91\x90\x91a\x0E\xDDa\x02\xA0Qa\x0CEV[a\x02`R__[a\x02\xA0Q\x81\x10a\x156WPa\x0F\ta\x0E\xFB\x82a\x08KV[`@Q`\xA0R`\xA0Qa\x08*V[`\xA0Q\x81\x90R`\x1F\x19\x90a\x0F\x1C\x90a\x08KV[\x01_[\x81\x81\x10a\x15\x1DWPP\x90`\xA0Q`\xC0R_a\x02@R_a\x03`R_`\xE0R[a\x02\xA0Q`\xE0Q\x10a\x0FNWPPV[a\x0FZ`\xE0Q\x83a\r-V[Qa\x03 R`\x01a\x0Fm`\xE0Q\x83a\r-V[Q\x03a\x0F\xF5W_[a\x02\xC0QQ\x81\x10\x15a\x0F\xEEWa\x03 Qa\x0F\x92\x82a\x03\x80Qa\r-V[Q\x14a\x0F\xA0W`\x01\x01a\x0FuV[a\x0F\xB0\x90a\x02\xC0\x93\x92\x93Qa\r-V[Qa\x0F\xC1a\x02@Qa\x02`Qa\r-V[Ra\x0F\xD2a\x02@Qa\x02`Qa\r-V[P`\x01a\x02@Q\x01a\x02@R[`\x01`\xE0Q\x01`\xE0R\x90a\x0F>V[P\x90a\x0F\xDFV[\x90\x91a\x10\x03`\xE0Q\x83a\r-V[Qa\x01\xC0Ra\x10\x10a\x0C&V[Pa\x10\x19a\x0C\x94V[Pa\x10&a\x01\xC0Qa\x0CEV[a\x03@R_\x92_[a\x02\xC0QQ\x81\x10\x15a\x15\x15Wa\x03 Qa\x10K\x82a\x03\x80Qa\r-V[Q\x14a\x10ZW[`\x01\x01a\x10.V[\x93`\x01\x90a\x10k\x86a\x02\xC0Qa\r-V[Qa\x10y\x82a\x03@Qa\r-V[Ra\x10\x87\x81a\x03@Qa\r-V[P\x01\x93a\x01\xC0Q\x85\x03a\x10RWP\x92P[_a\x03\0Ra\x10\xA9a\x03@Qa\x0C\xFCV[QQa\x10\xB7a\x03@Qa\x0C\xFCV[QQQ_\x19\x81\x01\x90\x81\x11a\x0B\xB8Wa\x10\xCE\x91a\r-V[Q\x92`\x80\x84\x01Q\x80g\r\xE0\xB6\xB3\xA7d\0\0\x81\x02\x04g\r\xE0\xB6\xB3\xA7d\0\0\x14\x81\x15\x17\x15a\x0B\xB8W``\x85\x01Qa\x11\x0C\x91g\r\xE0\xB6\xB3\xA7d\0\0\x02a\x0B\xCCV[a\x02\xE0R_[a\x03@QQ\x81\x10\x15a\x11\xF1Wa\x11+\x81a\x03@Qa\r-V[QQQa\x11;\x82a\x03@Qa\r-V[QQ`\x01\x19\x82\x01\x82\x81\x11a\x0B\xB8Wa\x11R\x91a\r-V[Q\x90a\x11a\x83a\x03@Qa\r-V[QQ\x91_\x19\x82\x01\x91\x82\x11a\x0B\xB8Wa\x11~`\x80\x92a\x11\x8E\x94a\r-V[Qa\x01@R\x01Qa\x03\0Qa\x1A\x05V[a\x03\0R`\x80a\x01@Q\x01Qg\r\xE0\xB6\xB3\xA7d\0\0\x81\x02\x90\x80\x82\x04g\r\xE0\xB6\xB3\xA7d\0\0\x14\x90\x15\x17\x15a\x0B\xB8Wa\x01@Q``\x01Qa\x11\xCC\x91a\x0B\xCCV[a\x02\xE0Q\x81\x11a\x11\xE0W[P`\x01\x01a\x11\x12V[a\x02\xE0Ra\x01@Q\x94P`\x01a\x11\xD7V[P\x91\x90\x92g\r\xE0\xB6\xB3\xA7d\0\0a\x12\x1Ba\x12\x12`\xC0\x84\x01Qa\x03\0Qa&\xACV[a\x03\0Qa\x0B\xA5V[\x04a\x02\x80R`\xA0\x81\x01Q\x80`>\x81\x02\x04`>\x14\x81\x15\x17\x15a\x0B\xB8Wa\x12Ba\x03@Qa\x0C\xFCV[QQa\x12Pa\x03@Qa\x0C\xFCV[QQQa\x02 \x81\x90R`\x01\x19\x81\x01\x11a\x0B\xB8W`d\x91`@a\x12|`>\x93`\x01\x19a\x02 Q\x01\x90a\r-V[Q\x01Qa\x02\0R`\xC0\x84Q\x94\x01Q\x93`@Qa\x01\xE0Ra\x12\x9Ea\x01\xE0Qa\x07\xD9V[a\x01\xE0QRa\x02\0Q` a\x01\xE0Q\x01Ra\x01 Q`@a\x01\xE0Q\x01Ra\x03\0Q``a\x01\xE0Q\x01Ra\x02\x80Q`\x80a\x01\xE0Q\x01R\x02\x04`\xA0a\x01\xE0Q\x01R`\xC0a\x01\xE0Q\x01Ra\x12\xF1a\x03@Qa\x0C\xFCV[QQa\x01\xA0Ra\x01\xA0QQa\x01\x80Ra\x13\x1Fa\x13\x0Fa\x01\x80Qa\x08KV[`@Qa\x01`Ra\x01`Qa\x08*V[a\x01\x80Qa\x01`QR`\x1F\x19a\x137a\x01\x80Qa\x08KV[\x01_[\x81\x81\x10a\x14\xFBWPP_[`\x01\x81\x01\x81\x11a\x0B\xB8Wa\x01\xA0QQ`\x01\x82\x01\x10\x15a\x13\x91W\x80a\x13n`\x01\x92a\x01\xA0Qa\r-V[Qa\x13|\x82a\x01`Qa\r-V[Ra\x13\x8A\x81a\x01`Qa\r-V[P\x01a\x13EV[P\x90a\x01\xA0QQ\x80_\x19\x81\x01\x11a\x0B\xB8Wa\x13\xC7\x90a\x01\xE0Qa\x13\xBA_\x19\x83\x01a\x01`Qa\r-V[R_\x19\x01a\x01`Qa\r-V[Pa\x13\xD4a\x01`Qa(\x1EV[\x91_a\x01\0R__`\x80R[a\x03@QQ`\x80Q\x10\x15a\x14UWa\x14*\x90a\x01\0Q` a\x14\x07`\x80Qa\x03@Qa\r-V[Q\x01Q\x11a\x148W[`@a\x14!`\x80Qa\x03@Qa\r-V[Q\x01Q\x90a\x1A\x05V[`\x80\x80Q`\x01\x01\x90Ra\x13\xE0V[` a\x14I`\x80Qa\x03@Qa\r-V[Q\x01Qa\x01\0Ra\x14\x10V[\x90\x92`@\x81\x01Q\x91`@Q\x92a\x14j\x84a\x07\xD9V[a\x03 Q\x84Ra\x01\xC0Q` \x85\x01Ra\x03\0Q`@\x85\x01Ra\x02\x80Q``\x85\x01Ra\x01\0Q`\x80\x85\x01R`\xA0\x84\x01R`\xC0\x83\x01Ra\x14\xAEa\x02@Qa\x02`Qa\r-V[Ra\x14\xBFa\x02@Qa\x02`Qa\r-V[Pa\x14\xCFa\x03`Q`\xA0Qa\r-V[Ra\x14\xDFa\x03`Q`\xA0Qa\r-V[P`\x01a\x02@Q\x01a\x02@R`\x01a\x03`Q\x01a\x03`Ra\x0F\xDFV[` \x90a\x15\x06a\x0C\x94V[\x82\x82a\x01`Q\x01\x01R\x01a\x13:V[P\x92Pa\x10\x98V[` \x90a\x15(a\x0C\x94V[\x82\x82`\xA0Q\x01\x01R\x01a\x0F\x1FV[`\x01a\x15B\x82\x86a\r-V[Q\x11\x80a\x15bW[a\x15WW[`\x01\x01a\x0E\xE4V[`\x01\x90\x91\x01\x90a\x15OV[Pa\x15m\x81\x84a\r-V[Q\x15\x15a\x15JV[`@Qa\x15\x83` \x82a\x08*V[_\x81R_\x80[\x81\x81\x10a\x15\xD0WPP`@Q\x90a\x15\xA1` \x83a\x08*V[_\x82R_\x80[\x81\x81\x10a\x15\xB9WPPa\x02`R`\xC0RV[` \x90a\x15\xC4a\x0C\x94V[\x82\x82\x87\x01\x01R\x01a\x15\xA7V[` \x90a\x15\xDBa\x0C&V[\x82\x82\x86\x01\x01R\x01a\x15\x89V[Q\x90`\x01`\x01`\xA0\x1B\x03\x82\x16\x82\x03a\x01\xE6WV[\x91\x93\x92a\x16\x06a\x08bV[\x94``\x82\x80Q\x81\x01\x03\x12a\x01\xE6Wa\x16 ` \x83\x01a\x15\xE7V[\x91```@\x82\x01Q\x91\x01Q\x92`\xFF\x84\x16\x80\x94\x03a\x01\xE6W`\x01`\x01`\xA0\x1B\x03\x16\x80\x15\x80\x15a\x16\xE3W[a\x16\xDBW\x84\x91\x86\x91`\x02\x86\x03a\x16\xA9Wa\x16c\x95Pa\x1FQV[\x91[\x82\x15a\t:W\x90a\x16u\x91a\x1B\xCFV[\x83R`@Qa\x16\x85`@\x82a\x08*V[`\x01\x81R` 6\x81\x83\x017`\x05a\x16\x9B\x82a\x0C\xFCV[R` \x84\x01Ra\t.a\x1C\x1AV[\x93\x94\x90\x92P`\x03\x14\x15\x90Pa\x0B W`\x01`\x01`\xA0\x1B\x03\x16\x90\x81\x15a\x0B W\x84a\x16\xD5\x93\x92\x85\x92a\x1E\x94V[\x91a\x16eV[PPPPPPV[P\x80;\x15a\x16IV[Q\x90\x81\x15\x15\x82\x03a\x01\xE6WV[\x91\x93\x92a\x17\x04a\x08bV[\x94`\x80\x82\x80Q\x81\x01\x03\x12a\x01\xE6Wa\x17\x1E` \x83\x01a\x15\xE7V[\x91`@\x81\x01Qa\x175`\x80``\x84\x01Q\x93\x01a\x16\xECV[\x93`\x01`\x01`\xA0\x1B\x03\x16\x80\x15\x80\x15a\x17\xA0W[a\x17\x97W\x82\x82\x14a\x17\x97W\x90a\x17`\x94\x93\x92\x91a\"yV[\x91\x82\x15a\t:W\x90a\x17q\x91a\x1B\xCFV[\x83R`@Qa\x17\x81`@\x82a\x08*V[`\x01\x81R` 6\x81\x83\x017`\x03a\x16\x9B\x82a\x0C\xFCV[PPPPPPPV[P\x80;\x15a\x17HV[\x91\x93\x92\x93a\x17\xB5a\x08bV[\x94`@\x81\x80Q\x81\x01\x03\x12a\x01\xE6Wa\x17\xDB`@a\x17\xD4` \x84\x01a\x15\xE7V[\x92\x01a\x16\xECV[P`\x01`\x01`\xA0\x1B\x03\x16\x80\x15\x80\x15a\x17\xFDW[a\t\x9EW\x90\x83a\t\x06\x92a#FV[P\x80;\x15a\x17\xEEV[\x91\x93\x92\x90a\x18\x12a\x08bV[\x94\x82Q\x83\x01\x90\x83` \x83\x01\x92\x03`\xE0\x81\x12a\x01\xE6W`\xA0\x13a\x01\xE6W`@Q\x93a\x18;\x85a\x08\x0FV[a\x18G` \x82\x01a\x15\xE7V[\x85Ra\x18U`@\x82\x01a\x15\xE7V[\x94` \x81\x01\x95\x86R``\x82\x01Q\x95b\xFF\xFF\xFF\x87\x16\x87\x03a\x01\xE6W`@\x82\x01\x96\x87R`\x80\x83\x01Q\x80`\x02\x0B\x81\x03a\x01\xE6W``\x83\x01Ra\x18\x96`\xA0\x84\x01a\x15\xE7V[`\x80\x83\x01Ra\x18\xA7`\xC0\x84\x01a\x16\xECV[\x92`\xE0\x81\x01Q\x90`\x01`\x01`@\x1B\x03\x82\x11a\x01\xE6W\x01\x85`?\x82\x01\x12\x15a\x01\xE6W` \x81\x01Q\x90a\x18\xD7\x82a\x08\x86V[\x96a\x18\xE5`@Q\x98\x89a\x08*V[\x82\x88R`@\x82\x84\x01\x01\x11a\x01\xE6W\x81_\x92`@` \x93\x01\x83\x8A\x01^\x87\x01\x01R\x82\x15a\x19\x97W\x81Q`\x01`\x01`\xA0\x1B\x03\x89\x81\x16\x91\x16\x14\x90\x81a\x19\x80W[P[\x15a\x17\x97W\x90a\x194\x93\x92\x91a#\x8AV[\x92\x83\x15a\t\x9EW\x91a\x19Mb\xFF\xFF\xFF\x92a\t.\x94a\x1B\xCFV[\x86R`@Qa\x19]`@\x82a\x08*V[`\x01\x81R` 6\x81\x83\x017`\x02a\x19s\x82a\x0C\xFCV[R` \x87\x01RQ\x16a\x1CAV[Q`\x01`\x01`\xA0\x1B\x03\x87\x81\x16\x91\x16\x14\x90P_a\x19!V[Q`\x01`\x01`\xA0\x1B\x03\x88\x81\x16\x91\x16\x14\x80\x15a\x19#WP\x80Q`\x01`\x01`\xA0\x1B\x03\x86\x81\x16\x91\x16\x14a\x19#V[=\x15a\x19\xECW=\x90a\x19\xD3\x82a\x08\x86V[\x91a\x19\xE1`@Q\x93\x84a\x08*V[\x82R=_` \x84\x01>V[``\x90V[Q\x90`\x01`\x01`p\x1B\x03\x82\x16\x82\x03a\x01\xE6WV[\x91\x90\x82\x01\x80\x92\x11a\x0B\xB8WV[\x90a\x1A\x1D\x90\x82a$\x9AV[`\x01`\x01`\xA0\x1B\x03\x81\x16\x15\x80\x15a\x1B\xC6W[a\x1B\xBFW_\x80`@Q` \x81\x01\x90c\x02@\xBCk`\xE2\x1B\x82R`\x04\x81Ra\x1AV`$\x82a\x08*V[Q\x90\x84Z\xFA\x91a\x1Ada\x19\xC2V[\x92\x15\x80\x15a\x1B\xB4W[a\x1B~W``\x83\x80Q\x81\x01\x03\x12a\x01\xE6Wa\x1A\x8A` \x84\x01a\x19\xF1V[\x91``a\x1A\x99`@\x86\x01a\x19\xF1V[\x94\x01Qc\xFF\xFF\xFF\xFF\x81\x16\x03a\x01\xE6W_\x80\x91`@Q` \x81\x01\x90c\r\xFE\x16\x81`\xE0\x1B\x82R`\x04\x81Ra\x1A\xCC`$\x82a\x08*V[Q\x91Z\xFAa\x1A\xD8a\x19\xC2V[\x90\x15\x80\x15a\x1B\xA9W[a\x1B\xA0W` \x81\x80Q\x81\x01\x03\x12a\x01\xE6W`\x01`\x01`\xA0\x1B\x03\x90a\x1B\x07\x90` \x01a\x15\xE7V[`\x01`\x01`\xA0\x1B\x03\x90\x92\x16\x91\x16\x03a\x1B\x8EW`\x01`\x01`p\x1B\x03\x91\x82\x16\x91\x16[\x80\x15\x91\x82\x80\x15a\x1B\x86W[a\x1B~Wa\x03\xE5\x84\x02\x93\x80\x85\x04a\x03\xE5\x14\x90\x15\x17\x15a\x0B\xB8Wa\x1BU\x90\x84a\x0B\xA5V[\x91a\x03\xE8\x82\x02\x91\x82\x04a\x03\xE8\x14\x17\x15a\x0B\xB8Wa\x1B{\x92a\x1Bu\x91a\x1A\x05V[\x90a\x0B\xCCV[\x90V[PPPP_\x90V[P\x80\x15a\x1B2V[`\x01`\x01`p\x1B\x03\x90\x81\x16\x91\x16a\x1B'V[PPPPP_\x90V[P` \x81Q\x10a\x1A\xE1V[P``\x83Q\x10a\x1AmV[PPP_\x90V[P\x80;\x15a\x1A/V[\x91\x90a\x1C\x0B`@Qa\x1B\xE2``\x82a\x08*V[`\x02\x81R`@6` \x83\x017\x80\x94a\x1B\xF9\x82a\x0C\xFCV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90Ra\r\x1DV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90RV[`@Q\x90a\x1C)`@\x83a\x08*V[`\x01\x82R` 6\x81\x84\x017_a\x1C>\x83a\x0C\xFCV[RV[\x90`@Q\x91a\x1CQ`@\x84a\x08*V[`\x01\x83R` 6\x81\x85\x017b\xFF\xFF\xFFa\x1Ci\x84a\x0C\xFCV[\x91\x16\x90RV[\x91\x92\x90\x92_\x93_\x93a\x1C\x82\x83\x83\x83a%9V[\x80a\x1C\xEBW[Pa\x1C\x94\x83\x83\x83a%\xB0V[\x86\x81\x11a\x1C\xDEW[Pa\x1C\xA8\x83\x83\x83a&\x04V[\x86\x81\x11a\x1C\xCFW[P\x90a\x1C\xBC\x92\x91a&XV[\x83\x81\x11a\x1C\xC6WPV[\x92Pa'\x10\x91PV[\x95Pa\x0B\xB8\x94Pa\x1C\xBCa\x1C\xB0V[\x95Pa\x01\xF4\x94P_a\x1C\x9CV[\x95P`d\x94P_a\x1C\x88V[\x92\x91\x90`@Q\x90a\x1D\t`\x80\x83a\x08*V[`\x03\x82R``6` \x84\x017\x81\x94a\x1D \x83a\x0C\xFCV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90Ra\x1D6\x82a\r\x1DV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90R\x80Q`\x02\x10\x15a\r\tW`\x01`\x01`\xA0\x1B\x03\x90\x91\x16``\x91\x90\x91\x01RV[`@Q\x90a\x1Dp``\x83a\x08*V[`\x02\x82R`@6` \x84\x017`\x01a\x1C>\x83\x82a\x1D\x8C\x82a\x0C\xFCV[Ra\r\x1DV[\x91\x90b\xFF\xFF\xFFa\x1Ci`@Qa\x1D\xA9``\x82a\x08*V[`\x02\x81R`@6` \x83\x017\x80\x95\x83a\x1D\xC1\x83a\x0C\xFCV[\x91\x16\x90Ra\r\x1DV[\x90\x81Q`\x02\x81\x10a\x1EjW_\x19\x81\x01\x90\x81\x11a\x0B\xB8Wa\x1D\xE9\x81a\x0C\xCAV[\x90_[\x81\x81\x10a\x1EGWPP\x90\x91P`@Q` \x81\x01\x81\x81\x93` \x81Q\x93\x91\x01\x92_[\x81\x81\x10a\x1E.WPPa\x1E(\x92P\x03`\x1F\x19\x81\x01\x83R\x82a\x08*V[Q\x90 \x90V[\x84Q\x83R` \x94\x85\x01\x94\x86\x94P\x90\x92\x01\x91`\x01\x01a\x1E\x0CV[\x80`@a\x1EV`\x01\x93\x88a\r-V[Q\x01Qa\x1Ec\x82\x86a\r-V[R\x01a\x1D\xECV[P_\x91PV[\x80Q\x80\x83R` \x92\x91\x81\x90\x84\x01\x84\x84\x01^_\x82\x82\x01\x84\x01R`\x1F\x01`\x1F\x19\x16\x01\x01\x90V[\x90_\x80\x94a\x1F\x12\x82\x95a\x1F\x04` \x99`@Q\x90a\x1E\xB1\x8C\x83a\x08*V[\x86\x82R`@Qc\x07\xD2E\xE9`\xE4\x1B\x8D\x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x99\x8A\x16`$\x83\x01R\x94\x89\x16`D\x82\x01R\x95\x90\x97\x16`d\x86\x01R`\x84\x85\x01\x96\x90\x96R`\xA0`\xA4\x85\x01R\x90\x94\x83\x91\x90`\xC4\x83\x01\x90a\x1EpV[\x03`\x1F\x19\x81\x01\x83R\x82a\x08*V[Q\x92Z\xF1\x90a\x1F\x1Fa\x19\xC2V[\x91\x15\x80\x15a\x1FGW[a\x1FAW\x81Q\x81\x83\x01\x92\x01\x81\x01\x82\x90\x03\x12a\x01\xE6WQ\x90V[PP_\x90V[P\x80\x82Q\x10a\x1F(V[\x90\x91\x93\x92\x93`@\x94\x85Q\x93a\x1Ff\x87\x86a\x08*V[`\x01\x85R`\x1F\x19\x87\x01_[\x81\x81\x10a\"EWPP\x86Q` \x96a\x1F\x89\x88\x83a\x08*V[_\x82R\x88Q\x92a\x1F\x98\x84a\x08\x0FV[\x83R_\x88\x84\x01R`\x01\x89\x84\x01R``\x83\x01R`\x80\x82\x01Ra\x1F\xB8\x85a\x0C\xFCV[Ra\x1F\xC2\x84a\x0C\xFCV[P``\x93\x86Q\x91a\x1F\xD3\x86\x84a\x08*V[`\x02\x83R\x86\x83\x01\x93`\x1F\x19\x87\x016\x867a\x1F\xEC\x84a\x0C\xFCV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90Ra \x02\x83a\r\x1DV[`\x01`\x01`\xA0\x1B\x03\x90\x91\x16\x90R\x86Qa \x1A\x81a\x07\xF4V[0\x81R\x86\x81\x01\x90_\x82R\x88\x81\x01\x920\x84R\x88\x88\x83\x01\x95_\x87R\x8B\x80Q\x9Ac|&\x837`\xE1\x1B\x84\x8D\x01R\x8Ba\x01\x04\x81\x01\x91_`$\x83\x01R`\xE0`D\x83\x01R\x86Q\x80\x93Ra\x01$\x82\x01\x90\x86a\x01$\x85`\x05\x1B\x85\x01\x01\x98\x01\x94_\x93[\x85\x85\x10a!\xE3WPPPPP\x8B\x85\x03`#\x19\x01`d\x8D\x01RPPQ\x80\x83R\x91\x01\x95\x90_[\x8A\x82\x82\x10a!\xC6WPP\x91Q`\x01`\x01`\xA0\x1B\x03\x90\x81\x16`\x84\x8A\x01R\x92Q\x15\x15`\xA4\x89\x01RPP\x90Q\x16`\xC4\x85\x01RQ\x15\x15`\xE4\x84\x01R\x82\x90\x03`\x1F\x19\x81\x01\x83R_\x92\x83\x92\x90\x91a \xE8\x90\x83a\x08*V[\x82\x85\x83Q\x93\x01\x91Z\xF1a \xF9a\x19\xC2V[\x90\x15\x80\x15a!\xBCW[a\x1B\xBFW\x80Q\x81\x01\x90\x82\x81\x81\x84\x01\x93\x03\x12a\x01\xE6W\x82\x81\x01Q\x90`\x01`\x01`@\x1B\x03\x82\x11a\x01\xE6W\x01\x92\x81`?\x85\x01\x12\x15a\x01\xE6W\x82\x84\x01Q\x90a!E\x82a\x08KV[\x94a!R\x82Q\x96\x87a\x08*V[\x82\x86R\x84\x80\x80\x88\x01\x94`\x05\x1B\x83\x01\x01\x01\x93\x84\x11a\x01\xE6W\x01\x90[\x82\x82\x10a!\xADWPPPP`\x02\x81Q\x10a!\xA8Wa!\x89\x90a\r\x1DV[Q_\x81\x12\x15a!\xA8W`\x01`\xFF\x1B\x81\x14a\x0B\xB8Wa\x1B{\x90_\x03a(\x87V[P_\x90V[\x81Q\x81R\x90\x83\x01\x90\x83\x01a!lV[P\x82\x81Q\x10a!\x02V[\x83Q`\x01`\x01`\xA0\x1B\x03\x16\x89R\x97\x88\x01\x97\x90\x92\x01\x91`\x01\x01a \x97V[\x88\x92\x94\x96\x99`\xA0`\x80`\x01\x96\x98\x9A\x9B\x94a\"0\x94a\x01#\x19\x90\x85\x03\x01\x8AR\x8DQ\x90\x81Q\x85R\x86\x82\x01Q\x87\x86\x01R\x80\x82\x01Q\x90\x85\x01R\x88\x81\x01Q\x89\x85\x01R\x01Q\x91\x81`\x80\x82\x01R\x01\x90a\x1EpV[\x98\x01\x93\x01\x93\x01\x90\x92\x8F\x93\x8F\x96\x95\x93\x94\x8Fa sV[` \x90\x89Qa\"S\x81a\x08\x0FV[_\x81R_\x83\x82\x01R_\x8B\x82\x01R_``\x82\x01R```\x80\x82\x01R\x82\x82\x8A\x01\x01R\x01a\x1FqV[_\x94\x85\x94\x91\x93\x92\x90\x15a#\x10Wa\"\x92a\"\x98\x91a(\x9CV[\x92a(\x9CV[`@Q\x92c^\rD?`\xE0\x1B` \x85\x01R`\x0F\x0B`$\x84\x01R`\x0F\x0B`D\x83\x01R`d\x82\x01R`d\x81Ra\"\xCD`\x84\x82a\x08*V[\x90[` \x82Q\x92\x01\x90Z\xFAa\"\xE0a\x19\xC2V[\x90\x15\x80\x15a#\x05W[a!\xA8W` \x81Q\x91\x81\x80\x82\x01\x93\x84\x92\x01\x01\x03\x12a\x01\xE6WQ\x90V[P` \x81Q\x10a\"\xE9V[\x91`@Q\x92cUmn\x9F`\xE0\x1B` \x85\x01R`$\x84\x01R`D\x83\x01R`d\x82\x01R`d\x81Ra#@`\x84\x82a\x08*V[\x90a\"\xCFV[_\x92\x83\x92`@Q\x90` \x82\x01\x92cx\xA0Q\xAD`\xE1\x1B\x84R`$\x83\x01R`\x01\x80`\xA0\x1B\x03\x16`D\x82\x01R`D\x81Ra#~`d\x82a\x08*V[Q\x91Z\xFAa\"\xE0a\x19\xC2V[\x90\x91`\x01`\x80\x1B\x81\x10\x15a$\x8DWa$k_\x94\x93a\x1F\x04\x86\x95`@Q\x95a#\xB0\x87a\x07\xF4V[\x86R` \x86\x01\x92\x15\x15\x83R`\x01`\x01`\x80\x1B\x03`@\x87\x01\x95\x16\x85R``\x86\x01\x90\x81R`\x01`\x01`\x80\x1B\x03`@Q\x95\x86\x94` \x86\x01\x98c\xAA\x9D!\xCB`\xE0\x1B\x8AR` `$\x88\x01RQ`\x01\x80`\xA0\x1B\x03\x81Q\x16`D\x88\x01R`\x01\x80`\xA0\x1B\x03` \x82\x01Q\x16`d\x88\x01Rb\xFF\xFF\xFF`@\x82\x01Q\x16`\x84\x88\x01R``\x81\x01Q`\x02\x0B`\xA4\x88\x01R`\x80`\x01\x80`\xA0\x1B\x03\x91\x01Q\x16`\xC4\x87\x01RQ\x15\x15`\xE4\x86\x01RQ\x16a\x01\x04\x84\x01RQa\x01\0a\x01$\x84\x01Ra\x01D\x83\x01\x90a\x1EpV[Q\x90\x82s9r\xC0\x0F~\xD4\x88^\x14X#\xEB|eSu\xD2u\xA1\xC5Z\xF1a\"\xE0a\x19\xC2V[c5'\x8D\x12_R`\x04`\x1C\xFD[`@Qc\xE6\xA49\x05`\xE0\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x92\x90\x91\x16`D\x80\x83\x01\x91\x90\x91R\x81R_\x91\x82\x91a$\xDA`d\x82a\x08*V[Q\x90s\xF1\xD7\xCCd\xFBDR\xF0\\I\x81&1.\xBE)\xF3\x0F\xBC\xF9Z\xFAa$\xFBa\x19\xC2V[\x90\x15\x80\x15a%.W[a!\xA8W` \x81\x80Q\x81\x01\x03\x12a\x01\xE6W`\x01`\x01`\xA0\x1B\x03\x90a%*\x90` \x01a\x15\xE7V[\x16\x90V[P` \x81Q\x10a%\x04V[`@QccR\x815`\xE1\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x91\x90\x92\x16`D\x83\x01R`d\x80\x83\x01\x93\x90\x93R`\x84\x82\x01\x92\x90\x92R_`\xA4\x80\x83\x01\x82\x90R\x82R\x91\x82\x91a%\x8E`\xC4\x82a\x08*V[Q\x90\x82sa\xFF\xE0\x14\xBA\x17\x98\x9Et<_l\xB2\x1B\xF9iu0\xB2\x1EZ\xF1a\"\xE0a\x19\xC2V[`@QccR\x815`\xE1\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x91\x90\x92\x16`D\x83\x01R`d\x82\x01\x92\x90\x92Ra\x01\xF4`\x84\x82\x01R_`\xA4\x80\x83\x01\x82\x90R\x82R\x91\x82\x91a%\x8E`\xC4\x82a\x08*V[`@QccR\x815`\xE1\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x91\x90\x92\x16`D\x83\x01R`d\x82\x01\x92\x90\x92Ra\x0B\xB8`\x84\x82\x01R_`\xA4\x80\x83\x01\x82\x90R\x82R\x91\x82\x91a%\x8E`\xC4\x82a\x08*V[`@QccR\x815`\xE1\x1B` \x82\x01\x90\x81R`\x01`\x01`\xA0\x1B\x03\x92\x83\x16`$\x83\x01R\x91\x90\x92\x16`D\x83\x01R`d\x82\x01\x92\x90\x92Ra'\x10`\x84\x82\x01R_`\xA4\x80\x83\x01\x82\x90R\x82R\x91\x82\x91a%\x8E`\xC4\x82a\x08*V[\x90\x80\x15a\x1FAW\x81a&\xBD\x91a\x1A\x05V[g\r\xE0\xB6\xB3\xA7d\0\0\x82\x02\x91\x81\x81\x15g\r\xE0\xB6\xB3\xA7d\0\0\x83\x86\x04\x14\x17\x02\x15a'\xA9WP\x90\x04[`\x03\x81\x02\x90`d\x81\x15`\x03\x83\x85\x04\x14\x17\x02\x15a'KWP`d\x90\x04[f\n\xA8{\xEES\x80\0\x81\x01g\r\xE0\xB6\xB3\xA7d\0\0\x11\x15a'DWg\r\xD6\x0E7\xB9\x10\x80\0\x03[g\x01cEx]\x8A\0\0\x81\x11\x15a'7W\x90V[Pg\x01cEx]\x8A\0\0\x90V[P_a'$V[`d`\x03_\x19\x81\x84\t\x84\x81\x10\x85\x01\x90\x03\x92\t\x90\x80`d\x11\x15a'\x9CW\x82\x82\x11\x90\x03`\xFE\x1B\x91\x03`\x02\x1C\x17\x7F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\(\xF5\xC2\x8F\\)\x02a'\0V[c\xAEG\xF7\x02_R`\x04`\x1C\xFD[\x81g\r\xE0\xB6\xB3\xA7d\0\0_\x19\x81\x84\t\x85\x81\x10\x86\x01\x90\x03\x92\t\x90\x82_\x03\x83\x16\x92\x81\x81\x11\x15a'\x9CW\x83\x90\x04\x80`\x03\x02`\x02\x18\x80\x82\x02`\x02\x03\x02\x80\x82\x02`\x02\x03\x02\x80\x82\x02`\x02\x03\x02\x80\x82\x02`\x02\x03\x02\x80\x82\x02`\x02\x03\x02\x80\x91\x02`\x02\x03\x02\x93`\x01\x84\x84\x83\x03\x04\x94\x80_\x03\x04\x01\x92\x11\x90\x03\x02\x17\x02a&\xE4V[\x90a('a\x0C&V[\x82\x81R\x82Q\x80\x15a(\x82W_\x19\x81\x01\x90\x81\x11a\x0B\xB8Wa(I`\x80\x91\x85a\r-V[Q\x01Q` \x82\x01R_\x90\x81[\x84Q\x83\x10\x15a(xWa(p`\x01\x91`\xA0a\x14!\x86\x89a\r-V[\x92\x01\x91a(UV[`@\x82\x01R\x92PPV[P\x91PV[_\x81\x12\x15a\x1B{Wc5'\x8D\x12_R`\x04`\x1C\xFD[`\x01`\x7F\x1B\x81\x10\x15a$\x8DW`\x0F\x0B\x90V\xFE\xA1dsolcC\0\x08\"\0\n",
    );
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**```solidity
struct Route { address[] path; uint8[] venues; uint24[] fees; uint256 amountOut; }
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct Route {
        #[allow(missing_docs)]
        pub path: alloy::sol_types::private::Vec<alloy::sol_types::private::Address>,
        #[allow(missing_docs)]
        pub venues: alloy::sol_types::private::Vec<u8>,
        #[allow(missing_docs)]
        pub fees: alloy::sol_types::private::Vec<
            alloy::sol_types::private::primitives::aliases::U24,
        >,
        #[allow(missing_docs)]
        pub amountOut: alloy::sol_types::private::primitives::aliases::U256,
    }
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        #[doc(hidden)]
        #[allow(dead_code)]
        type UnderlyingSolTuple<'a> = (
            alloy::sol_types::sol_data::Array<alloy::sol_types::sol_data::Address>,
            alloy::sol_types::sol_data::Array<alloy::sol_types::sol_data::Uint<8>>,
            alloy::sol_types::sol_data::Array<alloy::sol_types::sol_data::Uint<24>>,
            alloy::sol_types::sol_data::Uint<256>,
        );
        #[doc(hidden)]
        type UnderlyingRustTuple<'a> = (
            alloy::sol_types::private::Vec<alloy::sol_types::private::Address>,
            alloy::sol_types::private::Vec<u8>,
            alloy::sol_types::private::Vec<
                alloy::sol_types::private::primitives::aliases::U24,
            >,
            alloy::sol_types::private::primitives::aliases::U256,
        );
        #[cfg(test)]
        #[allow(dead_code, unreachable_patterns)]
        fn _type_assertion(
            _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
        ) {
            match _t {
                alloy_sol_types::private::AssertTypeEq::<
                    <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                >(_) => {}
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<Route> for UnderlyingRustTuple<'_> {
            fn from(value: Route) -> Self {
                (value.path, value.venues, value.fees, value.amountOut)
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<UnderlyingRustTuple<'_>> for Route {
            fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                Self {
                    path: tuple.0,
                    venues: tuple.1,
                    fees: tuple.2,
                    amountOut: tuple.3,
                }
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolValue for Route {
            type SolType = Self;
        }
        #[automatically_derived]
        impl alloy_sol_types::private::SolTypeValue<Self> for Route {
            #[inline]
            fn stv_to_tokens(&self) -> <Self as alloy_sol_types::SolType>::Token<'_> {
                (
                    <alloy::sol_types::sol_data::Array<
                        alloy::sol_types::sol_data::Address,
                    > as alloy_sol_types::SolType>::tokenize(&self.path),
                    <alloy::sol_types::sol_data::Array<
                        alloy::sol_types::sol_data::Uint<8>,
                    > as alloy_sol_types::SolType>::tokenize(&self.venues),
                    <alloy::sol_types::sol_data::Array<
                        alloy::sol_types::sol_data::Uint<24>,
                    > as alloy_sol_types::SolType>::tokenize(&self.fees),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.amountOut),
                )
            }
            #[inline]
            fn stv_abi_encoded_size(&self) -> usize {
                if let Some(size) = <Self as alloy_sol_types::SolType>::ENCODED_SIZE {
                    return size;
                }
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_encoded_size(&tuple)
            }
            #[inline]
            fn stv_eip712_data_word(&self) -> alloy_sol_types::Word {
                <Self as alloy_sol_types::SolStruct>::eip712_hash_struct(self)
            }
            #[inline]
            fn stv_abi_encode_packed_to(
                &self,
                out: &mut alloy_sol_types::private::Vec<u8>,
            ) {
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_encode_packed_to(&tuple, out)
            }
            #[inline]
            fn stv_abi_packed_encoded_size(&self) -> usize {
                if let Some(size) = <Self as alloy_sol_types::SolType>::PACKED_ENCODED_SIZE {
                    return size;
                }
                let tuple = <UnderlyingRustTuple<
                    '_,
                > as ::core::convert::From<Self>>::from(self.clone());
                <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_packed_encoded_size(&tuple)
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolType for Route {
            type RustType = Self;
            type Token<'a> = <UnderlyingSolTuple<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SOL_NAME: &'static str = <Self as alloy_sol_types::SolStruct>::NAME;
            const ENCODED_SIZE: Option<usize> = <UnderlyingSolTuple<
                '_,
            > as alloy_sol_types::SolType>::ENCODED_SIZE;
            const PACKED_ENCODED_SIZE: Option<usize> = <UnderlyingSolTuple<
                '_,
            > as alloy_sol_types::SolType>::PACKED_ENCODED_SIZE;
            #[inline]
            fn valid_token(token: &Self::Token<'_>) -> bool {
                <UnderlyingSolTuple<'_> as alloy_sol_types::SolType>::valid_token(token)
            }
            #[inline]
            fn detokenize(token: Self::Token<'_>) -> Self::RustType {
                let tuple = <UnderlyingSolTuple<
                    '_,
                > as alloy_sol_types::SolType>::detokenize(token);
                <Self as ::core::convert::From<UnderlyingRustTuple<'_>>>::from(tuple)
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolStruct for Route {
            const NAME: &'static str = "Route";
            #[inline]
            fn eip712_root_type() -> alloy_sol_types::private::Cow<'static, str> {
                alloy_sol_types::private::Cow::Borrowed(
                    "Route(address[] path,uint8[] venues,uint24[] fees,uint256 amountOut)",
                )
            }
            #[inline]
            fn eip712_components() -> alloy_sol_types::private::Vec<
                alloy_sol_types::private::Cow<'static, str>,
            > {
                alloy_sol_types::private::Vec::new()
            }
            #[inline]
            fn eip712_encode_type() -> alloy_sol_types::private::Cow<'static, str> {
                <Self as alloy_sol_types::SolStruct>::eip712_root_type()
            }
            #[inline]
            fn eip712_encode_data(&self) -> alloy_sol_types::private::Vec<u8> {
                [
                    <alloy::sol_types::sol_data::Array<
                        alloy::sol_types::sol_data::Address,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.path)
                        .0,
                    <alloy::sol_types::sol_data::Array<
                        alloy::sol_types::sol_data::Uint<8>,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.venues)
                        .0,
                    <alloy::sol_types::sol_data::Array<
                        alloy::sol_types::sol_data::Uint<24>,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.fees)
                        .0,
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::eip712_data_word(&self.amountOut)
                        .0,
                ]
                    .concat()
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::EventTopic for Route {
            #[inline]
            fn topic_preimage_length(rust: &Self::RustType) -> usize {
                0usize
                    + <alloy::sol_types::sol_data::Array<
                        alloy::sol_types::sol_data::Address,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(&rust.path)
                    + <alloy::sol_types::sol_data::Array<
                        alloy::sol_types::sol_data::Uint<8>,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.venues,
                    )
                    + <alloy::sol_types::sol_data::Array<
                        alloy::sol_types::sol_data::Uint<24>,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(&rust.fees)
                    + <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::EventTopic>::topic_preimage_length(
                        &rust.amountOut,
                    )
            }
            #[inline]
            fn encode_topic_preimage(
                rust: &Self::RustType,
                out: &mut alloy_sol_types::private::Vec<u8>,
            ) {
                out.reserve(
                    <Self as alloy_sol_types::EventTopic>::topic_preimage_length(rust),
                );
                <alloy::sol_types::sol_data::Array<
                    alloy::sol_types::sol_data::Address,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.path,
                    out,
                );
                <alloy::sol_types::sol_data::Array<
                    alloy::sol_types::sol_data::Uint<8>,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.venues,
                    out,
                );
                <alloy::sol_types::sol_data::Array<
                    alloy::sol_types::sol_data::Uint<24>,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.fees,
                    out,
                );
                <alloy::sol_types::sol_data::Uint<
                    256,
                > as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    &rust.amountOut,
                    out,
                );
            }
            #[inline]
            fn encode_topic(
                rust: &Self::RustType,
            ) -> alloy_sol_types::abi::token::WordToken {
                let mut out = alloy_sol_types::private::Vec::new();
                <Self as alloy_sol_types::EventTopic>::encode_topic_preimage(
                    rust,
                    &mut out,
                );
                alloy_sol_types::abi::token::WordToken(
                    alloy_sol_types::private::keccak256(out),
                )
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**Custom error with signature `PathFinder__NoRoute()` and selector `0x05418711`.
```solidity
error PathFinder__NoRoute();
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct PathFinder__NoRoute;
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        #[doc(hidden)]
        #[allow(dead_code)]
        type UnderlyingSolTuple<'a> = ();
        #[doc(hidden)]
        type UnderlyingRustTuple<'a> = ();
        #[cfg(test)]
        #[allow(dead_code, unreachable_patterns)]
        fn _type_assertion(
            _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
        ) {
            match _t {
                alloy_sol_types::private::AssertTypeEq::<
                    <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                >(_) => {}
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<PathFinder__NoRoute> for UnderlyingRustTuple<'_> {
            fn from(value: PathFinder__NoRoute) -> Self {
                ()
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<UnderlyingRustTuple<'_>> for PathFinder__NoRoute {
            fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                Self
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolError for PathFinder__NoRoute {
            type Parameters<'a> = UnderlyingSolTuple<'a>;
            type Token<'a> = <Self::Parameters<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SIGNATURE: &'static str = "PathFinder__NoRoute()";
            const SELECTOR: [u8; 4] = [5u8, 65u8, 135u8, 17u8];
            #[inline]
            fn new<'a>(
                tuple: <Self::Parameters<'a> as alloy_sol_types::SolType>::RustType,
            ) -> Self {
                tuple.into()
            }
            #[inline]
            fn tokenize(&self) -> Self::Token<'_> {
                ()
            }
            #[inline]
            fn abi_decode_raw_validate(data: &[u8]) -> alloy_sol_types::Result<Self> {
                <Self::Parameters<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence_validate(data)
                    .map(Self::new)
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**Custom error with signature `PathFinder__SameToken()` and selector `0x8303ee7e`.
```solidity
error PathFinder__SameToken();
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct PathFinder__SameToken;
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        #[doc(hidden)]
        #[allow(dead_code)]
        type UnderlyingSolTuple<'a> = ();
        #[doc(hidden)]
        type UnderlyingRustTuple<'a> = ();
        #[cfg(test)]
        #[allow(dead_code, unreachable_patterns)]
        fn _type_assertion(
            _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
        ) {
            match _t {
                alloy_sol_types::private::AssertTypeEq::<
                    <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                >(_) => {}
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<PathFinder__SameToken> for UnderlyingRustTuple<'_> {
            fn from(value: PathFinder__SameToken) -> Self {
                ()
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<UnderlyingRustTuple<'_>> for PathFinder__SameToken {
            fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                Self
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolError for PathFinder__SameToken {
            type Parameters<'a> = UnderlyingSolTuple<'a>;
            type Token<'a> = <Self::Parameters<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SIGNATURE: &'static str = "PathFinder__SameToken()";
            const SELECTOR: [u8; 4] = [131u8, 3u8, 238u8, 126u8];
            #[inline]
            fn new<'a>(
                tuple: <Self::Parameters<'a> as alloy_sol_types::SolType>::RustType,
            ) -> Self {
                tuple.into()
            }
            #[inline]
            fn tokenize(&self) -> Self::Token<'_> {
                ()
            }
            #[inline]
            fn abi_decode_raw_validate(data: &[u8]) -> alloy_sol_types::Result<Self> {
                <Self::Parameters<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence_validate(data)
                    .map(Self::new)
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**Custom error with signature `PathFinder__SlippageOutOfRange()` and selector `0x2a8406b9`.
```solidity
error PathFinder__SlippageOutOfRange();
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct PathFinder__SlippageOutOfRange;
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        #[doc(hidden)]
        #[allow(dead_code)]
        type UnderlyingSolTuple<'a> = ();
        #[doc(hidden)]
        type UnderlyingRustTuple<'a> = ();
        #[cfg(test)]
        #[allow(dead_code, unreachable_patterns)]
        fn _type_assertion(
            _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
        ) {
            match _t {
                alloy_sol_types::private::AssertTypeEq::<
                    <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                >(_) => {}
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<PathFinder__SlippageOutOfRange>
        for UnderlyingRustTuple<'_> {
            fn from(value: PathFinder__SlippageOutOfRange) -> Self {
                ()
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<UnderlyingRustTuple<'_>>
        for PathFinder__SlippageOutOfRange {
            fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                Self
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolError for PathFinder__SlippageOutOfRange {
            type Parameters<'a> = UnderlyingSolTuple<'a>;
            type Token<'a> = <Self::Parameters<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SIGNATURE: &'static str = "PathFinder__SlippageOutOfRange()";
            const SELECTOR: [u8; 4] = [42u8, 132u8, 6u8, 185u8];
            #[inline]
            fn new<'a>(
                tuple: <Self::Parameters<'a> as alloy_sol_types::SolType>::RustType,
            ) -> Self {
                tuple.into()
            }
            #[inline]
            fn tokenize(&self) -> Self::Token<'_> {
                ()
            }
            #[inline]
            fn abi_decode_raw_validate(data: &[u8]) -> alloy_sol_types::Result<Self> {
                <Self::Parameters<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence_validate(data)
                    .map(Self::new)
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**Custom error with signature `PathFinder__VenueNotImplemented(uint8)` and selector `0x580b6a6c`.
```solidity
error PathFinder__VenueNotImplemented(uint8 venue);
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct PathFinder__VenueNotImplemented {
        #[allow(missing_docs)]
        pub venue: u8,
    }
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        #[doc(hidden)]
        #[allow(dead_code)]
        type UnderlyingSolTuple<'a> = (alloy::sol_types::sol_data::Uint<8>,);
        #[doc(hidden)]
        type UnderlyingRustTuple<'a> = (u8,);
        #[cfg(test)]
        #[allow(dead_code, unreachable_patterns)]
        fn _type_assertion(
            _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
        ) {
            match _t {
                alloy_sol_types::private::AssertTypeEq::<
                    <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                >(_) => {}
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<PathFinder__VenueNotImplemented>
        for UnderlyingRustTuple<'_> {
            fn from(value: PathFinder__VenueNotImplemented) -> Self {
                (value.venue,)
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<UnderlyingRustTuple<'_>>
        for PathFinder__VenueNotImplemented {
            fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                Self { venue: tuple.0 }
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolError for PathFinder__VenueNotImplemented {
            type Parameters<'a> = UnderlyingSolTuple<'a>;
            type Token<'a> = <Self::Parameters<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SIGNATURE: &'static str = "PathFinder__VenueNotImplemented(uint8)";
            const SELECTOR: [u8; 4] = [88u8, 11u8, 106u8, 108u8];
            #[inline]
            fn new<'a>(
                tuple: <Self::Parameters<'a> as alloy_sol_types::SolType>::RustType,
            ) -> Self {
                tuple.into()
            }
            #[inline]
            fn tokenize(&self) -> Self::Token<'_> {
                (
                    <alloy::sol_types::sol_data::Uint<
                        8,
                    > as alloy_sol_types::SolType>::tokenize(&self.venue),
                )
            }
            #[inline]
            fn abi_decode_raw_validate(data: &[u8]) -> alloy_sol_types::Result<Self> {
                <Self::Parameters<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence_validate(data)
                    .map(Self::new)
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**Custom error with signature `PathFinder__ZeroAmount()` and selector `0x857e4aa9`.
```solidity
error PathFinder__ZeroAmount();
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct PathFinder__ZeroAmount;
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        #[doc(hidden)]
        #[allow(dead_code)]
        type UnderlyingSolTuple<'a> = ();
        #[doc(hidden)]
        type UnderlyingRustTuple<'a> = ();
        #[cfg(test)]
        #[allow(dead_code, unreachable_patterns)]
        fn _type_assertion(
            _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
        ) {
            match _t {
                alloy_sol_types::private::AssertTypeEq::<
                    <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                >(_) => {}
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<PathFinder__ZeroAmount> for UnderlyingRustTuple<'_> {
            fn from(value: PathFinder__ZeroAmount) -> Self {
                ()
            }
        }
        #[automatically_derived]
        #[doc(hidden)]
        impl ::core::convert::From<UnderlyingRustTuple<'_>> for PathFinder__ZeroAmount {
            fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                Self
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolError for PathFinder__ZeroAmount {
            type Parameters<'a> = UnderlyingSolTuple<'a>;
            type Token<'a> = <Self::Parameters<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SIGNATURE: &'static str = "PathFinder__ZeroAmount()";
            const SELECTOR: [u8; 4] = [133u8, 126u8, 74u8, 169u8];
            #[inline]
            fn new<'a>(
                tuple: <Self::Parameters<'a> as alloy_sol_types::SolType>::RustType,
            ) -> Self {
                tuple.into()
            }
            #[inline]
            fn tokenize(&self) -> Self::Token<'_> {
                ()
            }
            #[inline]
            fn abi_decode_raw_validate(data: &[u8]) -> alloy_sol_types::Result<Self> {
                <Self::Parameters<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence_validate(data)
                    .map(Self::new)
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**Function with signature `findRoute(address,address,uint256,uint256)` and selector `0x21bf9f26`.
```solidity
function findRoute(address tokenIn, address tokenOut, uint256 amountIn, uint256 slippageBps) external returns (Route memory route);
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct findRouteCall {
        #[allow(missing_docs)]
        pub tokenIn: alloy::sol_types::private::Address,
        #[allow(missing_docs)]
        pub tokenOut: alloy::sol_types::private::Address,
        #[allow(missing_docs)]
        pub amountIn: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub slippageBps: alloy::sol_types::private::primitives::aliases::U256,
    }
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    ///Container type for the return parameters of the [`findRoute(address,address,uint256,uint256)`](findRouteCall) function.
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct findRouteReturn {
        #[allow(missing_docs)]
        pub route: <Route as alloy::sol_types::SolType>::RustType,
    }
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        {
            #[doc(hidden)]
            #[allow(dead_code)]
            type UnderlyingSolTuple<'a> = (
                alloy::sol_types::sol_data::Address,
                alloy::sol_types::sol_data::Address,
                alloy::sol_types::sol_data::Uint<256>,
                alloy::sol_types::sol_data::Uint<256>,
            );
            #[doc(hidden)]
            type UnderlyingRustTuple<'a> = (
                alloy::sol_types::private::Address,
                alloy::sol_types::private::Address,
                alloy::sol_types::private::primitives::aliases::U256,
                alloy::sol_types::private::primitives::aliases::U256,
            );
            #[cfg(test)]
            #[allow(dead_code, unreachable_patterns)]
            fn _type_assertion(
                _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
            ) {
                match _t {
                    alloy_sol_types::private::AssertTypeEq::<
                        <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                    >(_) => {}
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<findRouteCall> for UnderlyingRustTuple<'_> {
                fn from(value: findRouteCall) -> Self {
                    (value.tokenIn, value.tokenOut, value.amountIn, value.slippageBps)
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<UnderlyingRustTuple<'_>> for findRouteCall {
                fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                    Self {
                        tokenIn: tuple.0,
                        tokenOut: tuple.1,
                        amountIn: tuple.2,
                        slippageBps: tuple.3,
                    }
                }
            }
        }
        {
            #[doc(hidden)]
            #[allow(dead_code)]
            type UnderlyingSolTuple<'a> = (Route,);
            #[doc(hidden)]
            type UnderlyingRustTuple<'a> = (
                <Route as alloy::sol_types::SolType>::RustType,
            );
            #[cfg(test)]
            #[allow(dead_code, unreachable_patterns)]
            fn _type_assertion(
                _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
            ) {
                match _t {
                    alloy_sol_types::private::AssertTypeEq::<
                        <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                    >(_) => {}
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<findRouteReturn> for UnderlyingRustTuple<'_> {
                fn from(value: findRouteReturn) -> Self {
                    (value.route,)
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<UnderlyingRustTuple<'_>> for findRouteReturn {
                fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                    Self { route: tuple.0 }
                }
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolCall for findRouteCall {
            type Parameters<'a> = (
                alloy::sol_types::sol_data::Address,
                alloy::sol_types::sol_data::Address,
                alloy::sol_types::sol_data::Uint<256>,
                alloy::sol_types::sol_data::Uint<256>,
            );
            type Token<'a> = <Self::Parameters<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            type Return = <Route as alloy::sol_types::SolType>::RustType;
            type ReturnTuple<'a> = (Route,);
            type ReturnToken<'a> = <Self::ReturnTuple<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SIGNATURE: &'static str = "findRoute(address,address,uint256,uint256)";
            const SELECTOR: [u8; 4] = [33u8, 191u8, 159u8, 38u8];
            #[inline]
            fn new<'a>(
                tuple: <Self::Parameters<'a> as alloy_sol_types::SolType>::RustType,
            ) -> Self {
                tuple.into()
            }
            #[inline]
            fn tokenize(&self) -> Self::Token<'_> {
                (
                    <alloy::sol_types::sol_data::Address as alloy_sol_types::SolType>::tokenize(
                        &self.tokenIn,
                    ),
                    <alloy::sol_types::sol_data::Address as alloy_sol_types::SolType>::tokenize(
                        &self.tokenOut,
                    ),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.amountIn),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.slippageBps),
                )
            }
            #[inline]
            fn tokenize_returns(ret: &Self::Return) -> Self::ReturnToken<'_> {
                (<Route as alloy_sol_types::SolType>::tokenize(ret),)
            }
            #[inline]
            fn abi_decode_returns(data: &[u8]) -> alloy_sol_types::Result<Self::Return> {
                <Self::ReturnTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence(data)
                    .map(|r| {
                        let r: findRouteReturn = r.into();
                        r.route
                    })
            }
            #[inline]
            fn abi_decode_returns_validate(
                data: &[u8],
            ) -> alloy_sol_types::Result<Self::Return> {
                <Self::ReturnTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence_validate(data)
                    .map(|r| {
                        let r: findRouteReturn = r.into();
                        r.route
                    })
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    /**Function with signature `findRouteWithHints(address,address,uint256,uint256,bytes)` and selector `0xc036c8ea`.
```solidity
function findRouteWithHints(address tokenIn, address tokenOut, uint256 amountIn, uint256 slippageBps, bytes memory extraData) external returns (Route memory route);
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct findRouteWithHintsCall {
        #[allow(missing_docs)]
        pub tokenIn: alloy::sol_types::private::Address,
        #[allow(missing_docs)]
        pub tokenOut: alloy::sol_types::private::Address,
        #[allow(missing_docs)]
        pub amountIn: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub slippageBps: alloy::sol_types::private::primitives::aliases::U256,
        #[allow(missing_docs)]
        pub extraData: alloy::sol_types::private::Bytes,
    }
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Default, Debug, PartialEq, Eq, Hash)]
    ///Container type for the return parameters of the [`findRouteWithHints(address,address,uint256,uint256,bytes)`](findRouteWithHintsCall) function.
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct findRouteWithHintsReturn {
        #[allow(missing_docs)]
        pub route: <Route as alloy::sol_types::SolType>::RustType,
    }
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        {
            #[doc(hidden)]
            #[allow(dead_code)]
            type UnderlyingSolTuple<'a> = (
                alloy::sol_types::sol_data::Address,
                alloy::sol_types::sol_data::Address,
                alloy::sol_types::sol_data::Uint<256>,
                alloy::sol_types::sol_data::Uint<256>,
                alloy::sol_types::sol_data::Bytes,
            );
            #[doc(hidden)]
            type UnderlyingRustTuple<'a> = (
                alloy::sol_types::private::Address,
                alloy::sol_types::private::Address,
                alloy::sol_types::private::primitives::aliases::U256,
                alloy::sol_types::private::primitives::aliases::U256,
                alloy::sol_types::private::Bytes,
            );
            #[cfg(test)]
            #[allow(dead_code, unreachable_patterns)]
            fn _type_assertion(
                _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
            ) {
                match _t {
                    alloy_sol_types::private::AssertTypeEq::<
                        <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                    >(_) => {}
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<findRouteWithHintsCall>
            for UnderlyingRustTuple<'_> {
                fn from(value: findRouteWithHintsCall) -> Self {
                    (
                        value.tokenIn,
                        value.tokenOut,
                        value.amountIn,
                        value.slippageBps,
                        value.extraData,
                    )
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<UnderlyingRustTuple<'_>>
            for findRouteWithHintsCall {
                fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                    Self {
                        tokenIn: tuple.0,
                        tokenOut: tuple.1,
                        amountIn: tuple.2,
                        slippageBps: tuple.3,
                        extraData: tuple.4,
                    }
                }
            }
        }
        {
            #[doc(hidden)]
            #[allow(dead_code)]
            type UnderlyingSolTuple<'a> = (Route,);
            #[doc(hidden)]
            type UnderlyingRustTuple<'a> = (
                <Route as alloy::sol_types::SolType>::RustType,
            );
            #[cfg(test)]
            #[allow(dead_code, unreachable_patterns)]
            fn _type_assertion(
                _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
            ) {
                match _t {
                    alloy_sol_types::private::AssertTypeEq::<
                        <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                    >(_) => {}
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<findRouteWithHintsReturn>
            for UnderlyingRustTuple<'_> {
                fn from(value: findRouteWithHintsReturn) -> Self {
                    (value.route,)
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<UnderlyingRustTuple<'_>>
            for findRouteWithHintsReturn {
                fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                    Self { route: tuple.0 }
                }
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolCall for findRouteWithHintsCall {
            type Parameters<'a> = (
                alloy::sol_types::sol_data::Address,
                alloy::sol_types::sol_data::Address,
                alloy::sol_types::sol_data::Uint<256>,
                alloy::sol_types::sol_data::Uint<256>,
                alloy::sol_types::sol_data::Bytes,
            );
            type Token<'a> = <Self::Parameters<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            type Return = <Route as alloy::sol_types::SolType>::RustType;
            type ReturnTuple<'a> = (Route,);
            type ReturnToken<'a> = <Self::ReturnTuple<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SIGNATURE: &'static str = "findRouteWithHints(address,address,uint256,uint256,bytes)";
            const SELECTOR: [u8; 4] = [192u8, 54u8, 200u8, 234u8];
            #[inline]
            fn new<'a>(
                tuple: <Self::Parameters<'a> as alloy_sol_types::SolType>::RustType,
            ) -> Self {
                tuple.into()
            }
            #[inline]
            fn tokenize(&self) -> Self::Token<'_> {
                (
                    <alloy::sol_types::sol_data::Address as alloy_sol_types::SolType>::tokenize(
                        &self.tokenIn,
                    ),
                    <alloy::sol_types::sol_data::Address as alloy_sol_types::SolType>::tokenize(
                        &self.tokenOut,
                    ),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.amountIn),
                    <alloy::sol_types::sol_data::Uint<
                        256,
                    > as alloy_sol_types::SolType>::tokenize(&self.slippageBps),
                    <alloy::sol_types::sol_data::Bytes as alloy_sol_types::SolType>::tokenize(
                        &self.extraData,
                    ),
                )
            }
            #[inline]
            fn tokenize_returns(ret: &Self::Return) -> Self::ReturnToken<'_> {
                (<Route as alloy_sol_types::SolType>::tokenize(ret),)
            }
            #[inline]
            fn abi_decode_returns(data: &[u8]) -> alloy_sol_types::Result<Self::Return> {
                <Self::ReturnTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence(data)
                    .map(|r| {
                        let r: findRouteWithHintsReturn = r.into();
                        r.route
                    })
            }
            #[inline]
            fn abi_decode_returns_validate(
                data: &[u8],
            ) -> alloy_sol_types::Result<Self::Return> {
                <Self::ReturnTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence_validate(data)
                    .map(|r| {
                        let r: findRouteWithHintsReturn = r.into();
                        r.route
                    })
            }
        }
    };
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive()]
    /**Function with signature `mergeRoutes(((bytes32,bytes32,bytes32,uint256,uint256,uint256,uint256)[],uint256,uint256)[],bytes32)` and selector `0x81c6ecd6`.
```solidity
function mergeRoutes(StepMerging.Route[] memory routes, bytes32 finalToken) external pure returns (StepMerging.Route[] memory optimised, StepMerging.MergedGroup[] memory groups);
```*/
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct mergeRoutesCall {
        #[allow(missing_docs)]
        pub routes: alloy::sol_types::private::Vec<
            <StepMerging::Route as alloy::sol_types::SolType>::RustType,
        >,
        #[allow(missing_docs)]
        pub finalToken: alloy::sol_types::private::FixedBytes<32>,
    }
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive()]
    ///Container type for the return parameters of the [`mergeRoutes(((bytes32,bytes32,bytes32,uint256,uint256,uint256,uint256)[],uint256,uint256)[],bytes32)`](mergeRoutesCall) function.
    #[allow(non_camel_case_types, non_snake_case, clippy::pub_underscore_fields)]
    #[derive(Clone)]
    pub struct mergeRoutesReturn {
        #[allow(missing_docs)]
        pub optimised: alloy::sol_types::private::Vec<
            <StepMerging::Route as alloy::sol_types::SolType>::RustType,
        >,
        #[allow(missing_docs)]
        pub groups: alloy::sol_types::private::Vec<
            <StepMerging::MergedGroup as alloy::sol_types::SolType>::RustType,
        >,
    }
    #[allow(
        non_camel_case_types,
        non_snake_case,
        clippy::pub_underscore_fields,
        clippy::style
    )]
    const _: () = {
        use alloy::sol_types as alloy_sol_types;
        {
            #[doc(hidden)]
            #[allow(dead_code)]
            type UnderlyingSolTuple<'a> = (
                alloy::sol_types::sol_data::Array<StepMerging::Route>,
                alloy::sol_types::sol_data::FixedBytes<32>,
            );
            #[doc(hidden)]
            type UnderlyingRustTuple<'a> = (
                alloy::sol_types::private::Vec<
                    <StepMerging::Route as alloy::sol_types::SolType>::RustType,
                >,
                alloy::sol_types::private::FixedBytes<32>,
            );
            #[cfg(test)]
            #[allow(dead_code, unreachable_patterns)]
            fn _type_assertion(
                _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
            ) {
                match _t {
                    alloy_sol_types::private::AssertTypeEq::<
                        <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                    >(_) => {}
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<mergeRoutesCall> for UnderlyingRustTuple<'_> {
                fn from(value: mergeRoutesCall) -> Self {
                    (value.routes, value.finalToken)
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<UnderlyingRustTuple<'_>> for mergeRoutesCall {
                fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                    Self {
                        routes: tuple.0,
                        finalToken: tuple.1,
                    }
                }
            }
        }
        {
            #[doc(hidden)]
            #[allow(dead_code)]
            type UnderlyingSolTuple<'a> = (
                alloy::sol_types::sol_data::Array<StepMerging::Route>,
                alloy::sol_types::sol_data::Array<StepMerging::MergedGroup>,
            );
            #[doc(hidden)]
            type UnderlyingRustTuple<'a> = (
                alloy::sol_types::private::Vec<
                    <StepMerging::Route as alloy::sol_types::SolType>::RustType,
                >,
                alloy::sol_types::private::Vec<
                    <StepMerging::MergedGroup as alloy::sol_types::SolType>::RustType,
                >,
            );
            #[cfg(test)]
            #[allow(dead_code, unreachable_patterns)]
            fn _type_assertion(
                _t: alloy_sol_types::private::AssertTypeEq<UnderlyingRustTuple>,
            ) {
                match _t {
                    alloy_sol_types::private::AssertTypeEq::<
                        <UnderlyingSolTuple as alloy_sol_types::SolType>::RustType,
                    >(_) => {}
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<mergeRoutesReturn> for UnderlyingRustTuple<'_> {
                fn from(value: mergeRoutesReturn) -> Self {
                    (value.optimised, value.groups)
                }
            }
            #[automatically_derived]
            #[doc(hidden)]
            impl ::core::convert::From<UnderlyingRustTuple<'_>> for mergeRoutesReturn {
                fn from(tuple: UnderlyingRustTuple<'_>) -> Self {
                    Self {
                        optimised: tuple.0,
                        groups: tuple.1,
                    }
                }
            }
        }
        impl mergeRoutesReturn {
            fn _tokenize(
                &self,
            ) -> <mergeRoutesCall as alloy_sol_types::SolCall>::ReturnToken<'_> {
                (
                    <alloy::sol_types::sol_data::Array<
                        StepMerging::Route,
                    > as alloy_sol_types::SolType>::tokenize(&self.optimised),
                    <alloy::sol_types::sol_data::Array<
                        StepMerging::MergedGroup,
                    > as alloy_sol_types::SolType>::tokenize(&self.groups),
                )
            }
        }
        #[automatically_derived]
        impl alloy_sol_types::SolCall for mergeRoutesCall {
            type Parameters<'a> = (
                alloy::sol_types::sol_data::Array<StepMerging::Route>,
                alloy::sol_types::sol_data::FixedBytes<32>,
            );
            type Token<'a> = <Self::Parameters<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            type Return = mergeRoutesReturn;
            type ReturnTuple<'a> = (
                alloy::sol_types::sol_data::Array<StepMerging::Route>,
                alloy::sol_types::sol_data::Array<StepMerging::MergedGroup>,
            );
            type ReturnToken<'a> = <Self::ReturnTuple<
                'a,
            > as alloy_sol_types::SolType>::Token<'a>;
            const SIGNATURE: &'static str = "mergeRoutes(((bytes32,bytes32,bytes32,uint256,uint256,uint256,uint256)[],uint256,uint256)[],bytes32)";
            const SELECTOR: [u8; 4] = [129u8, 198u8, 236u8, 214u8];
            #[inline]
            fn new<'a>(
                tuple: <Self::Parameters<'a> as alloy_sol_types::SolType>::RustType,
            ) -> Self {
                tuple.into()
            }
            #[inline]
            fn tokenize(&self) -> Self::Token<'_> {
                (
                    <alloy::sol_types::sol_data::Array<
                        StepMerging::Route,
                    > as alloy_sol_types::SolType>::tokenize(&self.routes),
                    <alloy::sol_types::sol_data::FixedBytes<
                        32,
                    > as alloy_sol_types::SolType>::tokenize(&self.finalToken),
                )
            }
            #[inline]
            fn tokenize_returns(ret: &Self::Return) -> Self::ReturnToken<'_> {
                mergeRoutesReturn::_tokenize(ret)
            }
            #[inline]
            fn abi_decode_returns(data: &[u8]) -> alloy_sol_types::Result<Self::Return> {
                <Self::ReturnTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence(data)
                    .map(Into::into)
            }
            #[inline]
            fn abi_decode_returns_validate(
                data: &[u8],
            ) -> alloy_sol_types::Result<Self::Return> {
                <Self::ReturnTuple<
                    '_,
                > as alloy_sol_types::SolType>::abi_decode_sequence_validate(data)
                    .map(Into::into)
            }
        }
    };
    ///Container for all the [`PathFinder`](self) function calls.
    #[derive(Clone)]
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive()]
    pub enum PathFinderCalls {
        #[allow(missing_docs)]
        findRoute(findRouteCall),
        #[allow(missing_docs)]
        findRouteWithHints(findRouteWithHintsCall),
        #[allow(missing_docs)]
        mergeRoutes(mergeRoutesCall),
    }
    impl PathFinderCalls {
        /// All the selectors of this enum.
        ///
        /// Note that the selectors might not be in the same order as the variants.
        /// No guarantees are made about the order of the selectors.
        ///
        /// Prefer using `SolInterface` methods instead.
        pub const SELECTORS: &'static [[u8; 4usize]] = &[
            [33u8, 191u8, 159u8, 38u8],
            [129u8, 198u8, 236u8, 214u8],
            [192u8, 54u8, 200u8, 234u8],
        ];
        /// The names of the variants in the same order as `SELECTORS`.
        pub const VARIANT_NAMES: &'static [&'static str] = &[
            ::core::stringify!(findRoute),
            ::core::stringify!(mergeRoutes),
            ::core::stringify!(findRouteWithHints),
        ];
        /// The signatures in the same order as `SELECTORS`.
        pub const SIGNATURES: &'static [&'static str] = &[
            <findRouteCall as alloy_sol_types::SolCall>::SIGNATURE,
            <mergeRoutesCall as alloy_sol_types::SolCall>::SIGNATURE,
            <findRouteWithHintsCall as alloy_sol_types::SolCall>::SIGNATURE,
        ];
        /// Returns the signature for the given selector, if known.
        #[inline]
        pub fn signature_by_selector(
            selector: [u8; 4usize],
        ) -> ::core::option::Option<&'static str> {
            match Self::SELECTORS.binary_search(&selector) {
                ::core::result::Result::Ok(idx) => {
                    ::core::option::Option::Some(Self::SIGNATURES[idx])
                }
                ::core::result::Result::Err(_) => ::core::option::Option::None,
            }
        }
        /// Returns the enum variant name for the given selector, if known.
        #[inline]
        pub fn name_by_selector(
            selector: [u8; 4usize],
        ) -> ::core::option::Option<&'static str> {
            let sig = Self::signature_by_selector(selector)?;
            sig.split_once('(').map(|(name, _)| name)
        }
    }
    #[automatically_derived]
    impl alloy_sol_types::SolInterface for PathFinderCalls {
        const NAME: &'static str = "PathFinderCalls";
        const MIN_DATA_LENGTH: usize = 96usize;
        const COUNT: usize = 3usize;
        #[inline]
        fn selector(&self) -> [u8; 4] {
            match self {
                Self::findRoute(_) => {
                    <findRouteCall as alloy_sol_types::SolCall>::SELECTOR
                }
                Self::findRouteWithHints(_) => {
                    <findRouteWithHintsCall as alloy_sol_types::SolCall>::SELECTOR
                }
                Self::mergeRoutes(_) => {
                    <mergeRoutesCall as alloy_sol_types::SolCall>::SELECTOR
                }
            }
        }
        #[inline]
        fn selector_at(i: usize) -> ::core::option::Option<[u8; 4]> {
            Self::SELECTORS.get(i).copied()
        }
        #[inline]
        fn valid_selector(selector: [u8; 4]) -> bool {
            Self::SELECTORS.binary_search(&selector).is_ok()
        }
        #[inline]
        #[allow(non_snake_case)]
        fn abi_decode_raw(
            selector: [u8; 4],
            data: &[u8],
        ) -> alloy_sol_types::Result<Self> {
            static DECODE_SHIMS: &[fn(
                &[u8],
            ) -> alloy_sol_types::Result<PathFinderCalls>] = &[
                {
                    fn findRoute(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderCalls> {
                        <findRouteCall as alloy_sol_types::SolCall>::abi_decode_raw(data)
                            .map(PathFinderCalls::findRoute)
                    }
                    findRoute
                },
                {
                    fn mergeRoutes(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderCalls> {
                        <mergeRoutesCall as alloy_sol_types::SolCall>::abi_decode_raw(
                                data,
                            )
                            .map(PathFinderCalls::mergeRoutes)
                    }
                    mergeRoutes
                },
                {
                    fn findRouteWithHints(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderCalls> {
                        <findRouteWithHintsCall as alloy_sol_types::SolCall>::abi_decode_raw(
                                data,
                            )
                            .map(PathFinderCalls::findRouteWithHints)
                    }
                    findRouteWithHints
                },
            ];
            let Ok(idx) = Self::SELECTORS.binary_search(&selector) else {
                return Err(
                    alloy_sol_types::Error::unknown_selector(
                        <Self as alloy_sol_types::SolInterface>::NAME,
                        selector,
                    ),
                );
            };
            DECODE_SHIMS[idx](data)
        }
        #[inline]
        #[allow(non_snake_case)]
        fn abi_decode_raw_validate(
            selector: [u8; 4],
            data: &[u8],
        ) -> alloy_sol_types::Result<Self> {
            static DECODE_VALIDATE_SHIMS: &[fn(
                &[u8],
            ) -> alloy_sol_types::Result<PathFinderCalls>] = &[
                {
                    fn findRoute(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderCalls> {
                        <findRouteCall as alloy_sol_types::SolCall>::abi_decode_raw_validate(
                                data,
                            )
                            .map(PathFinderCalls::findRoute)
                    }
                    findRoute
                },
                {
                    fn mergeRoutes(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderCalls> {
                        <mergeRoutesCall as alloy_sol_types::SolCall>::abi_decode_raw_validate(
                                data,
                            )
                            .map(PathFinderCalls::mergeRoutes)
                    }
                    mergeRoutes
                },
                {
                    fn findRouteWithHints(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderCalls> {
                        <findRouteWithHintsCall as alloy_sol_types::SolCall>::abi_decode_raw_validate(
                                data,
                            )
                            .map(PathFinderCalls::findRouteWithHints)
                    }
                    findRouteWithHints
                },
            ];
            let Ok(idx) = Self::SELECTORS.binary_search(&selector) else {
                return Err(
                    alloy_sol_types::Error::unknown_selector(
                        <Self as alloy_sol_types::SolInterface>::NAME,
                        selector,
                    ),
                );
            };
            DECODE_VALIDATE_SHIMS[idx](data)
        }
        #[inline]
        fn abi_encoded_size(&self) -> usize {
            match self {
                Self::findRoute(inner) => {
                    <findRouteCall as alloy_sol_types::SolCall>::abi_encoded_size(inner)
                }
                Self::findRouteWithHints(inner) => {
                    <findRouteWithHintsCall as alloy_sol_types::SolCall>::abi_encoded_size(
                        inner,
                    )
                }
                Self::mergeRoutes(inner) => {
                    <mergeRoutesCall as alloy_sol_types::SolCall>::abi_encoded_size(
                        inner,
                    )
                }
            }
        }
        #[inline]
        fn abi_encode_raw(&self, out: &mut alloy_sol_types::private::Vec<u8>) {
            match self {
                Self::findRoute(inner) => {
                    <findRouteCall as alloy_sol_types::SolCall>::abi_encode_raw(
                        inner,
                        out,
                    )
                }
                Self::findRouteWithHints(inner) => {
                    <findRouteWithHintsCall as alloy_sol_types::SolCall>::abi_encode_raw(
                        inner,
                        out,
                    )
                }
                Self::mergeRoutes(inner) => {
                    <mergeRoutesCall as alloy_sol_types::SolCall>::abi_encode_raw(
                        inner,
                        out,
                    )
                }
            }
        }
    }
    ///Container for all the [`PathFinder`](self) custom errors.
    #[derive(Clone)]
    #[derive(serde::Serialize, serde::Deserialize)]
    #[derive(Debug, PartialEq, Eq, Hash)]
    pub enum PathFinderErrors {
        #[allow(missing_docs)]
        PathFinder__NoRoute(PathFinder__NoRoute),
        #[allow(missing_docs)]
        PathFinder__SameToken(PathFinder__SameToken),
        #[allow(missing_docs)]
        PathFinder__SlippageOutOfRange(PathFinder__SlippageOutOfRange),
        #[allow(missing_docs)]
        PathFinder__VenueNotImplemented(PathFinder__VenueNotImplemented),
        #[allow(missing_docs)]
        PathFinder__ZeroAmount(PathFinder__ZeroAmount),
    }
    impl PathFinderErrors {
        /// All the selectors of this enum.
        ///
        /// Note that the selectors might not be in the same order as the variants.
        /// No guarantees are made about the order of the selectors.
        ///
        /// Prefer using `SolInterface` methods instead.
        pub const SELECTORS: &'static [[u8; 4usize]] = &[
            [5u8, 65u8, 135u8, 17u8],
            [42u8, 132u8, 6u8, 185u8],
            [88u8, 11u8, 106u8, 108u8],
            [131u8, 3u8, 238u8, 126u8],
            [133u8, 126u8, 74u8, 169u8],
        ];
        /// The names of the variants in the same order as `SELECTORS`.
        pub const VARIANT_NAMES: &'static [&'static str] = &[
            ::core::stringify!(PathFinder__NoRoute),
            ::core::stringify!(PathFinder__SlippageOutOfRange),
            ::core::stringify!(PathFinder__VenueNotImplemented),
            ::core::stringify!(PathFinder__SameToken),
            ::core::stringify!(PathFinder__ZeroAmount),
        ];
        /// The signatures in the same order as `SELECTORS`.
        pub const SIGNATURES: &'static [&'static str] = &[
            <PathFinder__NoRoute as alloy_sol_types::SolError>::SIGNATURE,
            <PathFinder__SlippageOutOfRange as alloy_sol_types::SolError>::SIGNATURE,
            <PathFinder__VenueNotImplemented as alloy_sol_types::SolError>::SIGNATURE,
            <PathFinder__SameToken as alloy_sol_types::SolError>::SIGNATURE,
            <PathFinder__ZeroAmount as alloy_sol_types::SolError>::SIGNATURE,
        ];
        /// Returns the signature for the given selector, if known.
        #[inline]
        pub fn signature_by_selector(
            selector: [u8; 4usize],
        ) -> ::core::option::Option<&'static str> {
            match Self::SELECTORS.binary_search(&selector) {
                ::core::result::Result::Ok(idx) => {
                    ::core::option::Option::Some(Self::SIGNATURES[idx])
                }
                ::core::result::Result::Err(_) => ::core::option::Option::None,
            }
        }
        /// Returns the enum variant name for the given selector, if known.
        #[inline]
        pub fn name_by_selector(
            selector: [u8; 4usize],
        ) -> ::core::option::Option<&'static str> {
            let sig = Self::signature_by_selector(selector)?;
            sig.split_once('(').map(|(name, _)| name)
        }
    }
    #[automatically_derived]
    impl alloy_sol_types::SolInterface for PathFinderErrors {
        const NAME: &'static str = "PathFinderErrors";
        const MIN_DATA_LENGTH: usize = 0usize;
        const COUNT: usize = 5usize;
        #[inline]
        fn selector(&self) -> [u8; 4] {
            match self {
                Self::PathFinder__NoRoute(_) => {
                    <PathFinder__NoRoute as alloy_sol_types::SolError>::SELECTOR
                }
                Self::PathFinder__SameToken(_) => {
                    <PathFinder__SameToken as alloy_sol_types::SolError>::SELECTOR
                }
                Self::PathFinder__SlippageOutOfRange(_) => {
                    <PathFinder__SlippageOutOfRange as alloy_sol_types::SolError>::SELECTOR
                }
                Self::PathFinder__VenueNotImplemented(_) => {
                    <PathFinder__VenueNotImplemented as alloy_sol_types::SolError>::SELECTOR
                }
                Self::PathFinder__ZeroAmount(_) => {
                    <PathFinder__ZeroAmount as alloy_sol_types::SolError>::SELECTOR
                }
            }
        }
        #[inline]
        fn selector_at(i: usize) -> ::core::option::Option<[u8; 4]> {
            Self::SELECTORS.get(i).copied()
        }
        #[inline]
        fn valid_selector(selector: [u8; 4]) -> bool {
            Self::SELECTORS.binary_search(&selector).is_ok()
        }
        #[inline]
        #[allow(non_snake_case)]
        fn abi_decode_raw(
            selector: [u8; 4],
            data: &[u8],
        ) -> alloy_sol_types::Result<Self> {
            static DECODE_SHIMS: &[fn(
                &[u8],
            ) -> alloy_sol_types::Result<PathFinderErrors>] = &[
                {
                    fn PathFinder__NoRoute(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__NoRoute as alloy_sol_types::SolError>::abi_decode_raw(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__NoRoute)
                    }
                    PathFinder__NoRoute
                },
                {
                    fn PathFinder__SlippageOutOfRange(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__SlippageOutOfRange as alloy_sol_types::SolError>::abi_decode_raw(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__SlippageOutOfRange)
                    }
                    PathFinder__SlippageOutOfRange
                },
                {
                    fn PathFinder__VenueNotImplemented(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__VenueNotImplemented as alloy_sol_types::SolError>::abi_decode_raw(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__VenueNotImplemented)
                    }
                    PathFinder__VenueNotImplemented
                },
                {
                    fn PathFinder__SameToken(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__SameToken as alloy_sol_types::SolError>::abi_decode_raw(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__SameToken)
                    }
                    PathFinder__SameToken
                },
                {
                    fn PathFinder__ZeroAmount(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__ZeroAmount as alloy_sol_types::SolError>::abi_decode_raw(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__ZeroAmount)
                    }
                    PathFinder__ZeroAmount
                },
            ];
            let Ok(idx) = Self::SELECTORS.binary_search(&selector) else {
                return Err(
                    alloy_sol_types::Error::unknown_selector(
                        <Self as alloy_sol_types::SolInterface>::NAME,
                        selector,
                    ),
                );
            };
            DECODE_SHIMS[idx](data)
        }
        #[inline]
        #[allow(non_snake_case)]
        fn abi_decode_raw_validate(
            selector: [u8; 4],
            data: &[u8],
        ) -> alloy_sol_types::Result<Self> {
            static DECODE_VALIDATE_SHIMS: &[fn(
                &[u8],
            ) -> alloy_sol_types::Result<PathFinderErrors>] = &[
                {
                    fn PathFinder__NoRoute(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__NoRoute as alloy_sol_types::SolError>::abi_decode_raw_validate(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__NoRoute)
                    }
                    PathFinder__NoRoute
                },
                {
                    fn PathFinder__SlippageOutOfRange(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__SlippageOutOfRange as alloy_sol_types::SolError>::abi_decode_raw_validate(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__SlippageOutOfRange)
                    }
                    PathFinder__SlippageOutOfRange
                },
                {
                    fn PathFinder__VenueNotImplemented(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__VenueNotImplemented as alloy_sol_types::SolError>::abi_decode_raw_validate(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__VenueNotImplemented)
                    }
                    PathFinder__VenueNotImplemented
                },
                {
                    fn PathFinder__SameToken(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__SameToken as alloy_sol_types::SolError>::abi_decode_raw_validate(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__SameToken)
                    }
                    PathFinder__SameToken
                },
                {
                    fn PathFinder__ZeroAmount(
                        data: &[u8],
                    ) -> alloy_sol_types::Result<PathFinderErrors> {
                        <PathFinder__ZeroAmount as alloy_sol_types::SolError>::abi_decode_raw_validate(
                                data,
                            )
                            .map(PathFinderErrors::PathFinder__ZeroAmount)
                    }
                    PathFinder__ZeroAmount
                },
            ];
            let Ok(idx) = Self::SELECTORS.binary_search(&selector) else {
                return Err(
                    alloy_sol_types::Error::unknown_selector(
                        <Self as alloy_sol_types::SolInterface>::NAME,
                        selector,
                    ),
                );
            };
            DECODE_VALIDATE_SHIMS[idx](data)
        }
        #[inline]
        fn abi_encoded_size(&self) -> usize {
            match self {
                Self::PathFinder__NoRoute(inner) => {
                    <PathFinder__NoRoute as alloy_sol_types::SolError>::abi_encoded_size(
                        inner,
                    )
                }
                Self::PathFinder__SameToken(inner) => {
                    <PathFinder__SameToken as alloy_sol_types::SolError>::abi_encoded_size(
                        inner,
                    )
                }
                Self::PathFinder__SlippageOutOfRange(inner) => {
                    <PathFinder__SlippageOutOfRange as alloy_sol_types::SolError>::abi_encoded_size(
                        inner,
                    )
                }
                Self::PathFinder__VenueNotImplemented(inner) => {
                    <PathFinder__VenueNotImplemented as alloy_sol_types::SolError>::abi_encoded_size(
                        inner,
                    )
                }
                Self::PathFinder__ZeroAmount(inner) => {
                    <PathFinder__ZeroAmount as alloy_sol_types::SolError>::abi_encoded_size(
                        inner,
                    )
                }
            }
        }
        #[inline]
        fn abi_encode_raw(&self, out: &mut alloy_sol_types::private::Vec<u8>) {
            match self {
                Self::PathFinder__NoRoute(inner) => {
                    <PathFinder__NoRoute as alloy_sol_types::SolError>::abi_encode_raw(
                        inner,
                        out,
                    )
                }
                Self::PathFinder__SameToken(inner) => {
                    <PathFinder__SameToken as alloy_sol_types::SolError>::abi_encode_raw(
                        inner,
                        out,
                    )
                }
                Self::PathFinder__SlippageOutOfRange(inner) => {
                    <PathFinder__SlippageOutOfRange as alloy_sol_types::SolError>::abi_encode_raw(
                        inner,
                        out,
                    )
                }
                Self::PathFinder__VenueNotImplemented(inner) => {
                    <PathFinder__VenueNotImplemented as alloy_sol_types::SolError>::abi_encode_raw(
                        inner,
                        out,
                    )
                }
                Self::PathFinder__ZeroAmount(inner) => {
                    <PathFinder__ZeroAmount as alloy_sol_types::SolError>::abi_encode_raw(
                        inner,
                        out,
                    )
                }
            }
        }
    }
    use alloy::contract as alloy_contract;
    /**Creates a new wrapper around an on-chain [`PathFinder`](self) contract instance.

See the [wrapper's documentation](`PathFinderInstance`) for more details.*/
    #[inline]
    pub const fn new<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    >(
        address: alloy_sol_types::private::Address,
        __provider: P,
    ) -> PathFinderInstance<P, N> {
        PathFinderInstance::<P, N>::new(address, __provider)
    }
    /**Deploys this contract using the given `provider` and constructor arguments, if any.

Returns a new instance of the contract, if the deployment was successful.

For more fine-grained control over the deployment process, use [`deploy_builder`] instead.*/
    #[inline]
    pub fn deploy<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    >(
        __provider: P,
    ) -> impl ::core::future::Future<
        Output = alloy_contract::Result<PathFinderInstance<P, N>>,
    > {
        PathFinderInstance::<P, N>::deploy(__provider)
    }
    /**Creates a `RawCallBuilder` for deploying this contract using the given `provider`
and constructor arguments, if any.

This is a simple wrapper around creating a `RawCallBuilder` with the data set to
the bytecode concatenated with the constructor's ABI-encoded arguments.*/
    #[inline]
    pub fn deploy_builder<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    >(__provider: P) -> alloy_contract::RawCallBuilder<P, N> {
        PathFinderInstance::<P, N>::deploy_builder(__provider)
    }
    /**A [`PathFinder`](self) instance.

Contains type-safe methods for interacting with an on-chain instance of the
[`PathFinder`](self) contract located at a given `address`, using a given
provider `P`.

If the contract bytecode is available (see the [`sol!`](alloy_sol_types::sol!)
documentation on how to provide it), the `deploy` and `deploy_builder` methods can
be used to deploy a new instance of the contract.

See the [module-level documentation](self) for all the available methods.*/
    #[derive(Clone)]
    pub struct PathFinderInstance<P, N = alloy_contract::private::Ethereum> {
        address: alloy_sol_types::private::Address,
        provider: P,
        _network: ::core::marker::PhantomData<N>,
    }
    #[automatically_derived]
    impl<P, N> ::core::fmt::Debug for PathFinderInstance<P, N> {
        #[inline]
        fn fmt(&self, f: &mut ::core::fmt::Formatter<'_>) -> ::core::fmt::Result {
            f.debug_tuple("PathFinderInstance").field(&self.address).finish()
        }
    }
    /// Instantiation and getters/setters.
    impl<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    > PathFinderInstance<P, N> {
        /**Creates a new wrapper around an on-chain [`PathFinder`](self) contract instance.

See the [wrapper's documentation](`PathFinderInstance`) for more details.*/
        #[inline]
        pub const fn new(
            address: alloy_sol_types::private::Address,
            __provider: P,
        ) -> Self {
            Self {
                address,
                provider: __provider,
                _network: ::core::marker::PhantomData,
            }
        }
        /**Deploys this contract using the given `provider` and constructor arguments, if any.

Returns a new instance of the contract, if the deployment was successful.

For more fine-grained control over the deployment process, use [`deploy_builder`] instead.*/
        #[inline]
        pub async fn deploy(
            __provider: P,
        ) -> alloy_contract::Result<PathFinderInstance<P, N>> {
            let call_builder = Self::deploy_builder(__provider);
            let contract_address = call_builder.deploy().await?;
            Ok(Self::new(contract_address, call_builder.provider))
        }
        /**Creates a `RawCallBuilder` for deploying this contract using the given `provider`
and constructor arguments, if any.

This is a simple wrapper around creating a `RawCallBuilder` with the data set to
the bytecode concatenated with the constructor's ABI-encoded arguments.*/
        #[inline]
        pub fn deploy_builder(__provider: P) -> alloy_contract::RawCallBuilder<P, N> {
            alloy_contract::RawCallBuilder::new_raw_deploy(
                __provider,
                ::core::clone::Clone::clone(&BYTECODE),
            )
        }
        /// Returns a reference to the address.
        #[inline]
        pub const fn address(&self) -> &alloy_sol_types::private::Address {
            &self.address
        }
        /// Sets the address.
        #[inline]
        pub fn set_address(&mut self, address: alloy_sol_types::private::Address) {
            self.address = address;
        }
        /// Sets the address and returns `self`.
        pub fn at(mut self, address: alloy_sol_types::private::Address) -> Self {
            self.set_address(address);
            self
        }
        /// Returns a reference to the provider.
        #[inline]
        pub const fn provider(&self) -> &P {
            &self.provider
        }
    }
    impl<P: ::core::clone::Clone, N> PathFinderInstance<&P, N> {
        /// Clones the provider and returns a new instance with the cloned provider.
        #[inline]
        pub fn with_cloned_provider(self) -> PathFinderInstance<P, N> {
            PathFinderInstance {
                address: self.address,
                provider: ::core::clone::Clone::clone(&self.provider),
                _network: ::core::marker::PhantomData,
            }
        }
    }
    /// Function calls.
    impl<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    > PathFinderInstance<P, N> {
        /// Creates a new call builder using this contract instance's provider and address.
        ///
        /// Note that the call can be any function call, not just those defined in this
        /// contract. Prefer using the other methods for building type-safe contract calls.
        pub fn call_builder<C: alloy_sol_types::SolCall>(
            &self,
            call: &C,
        ) -> alloy_contract::SolCallBuilder<&P, C, N> {
            alloy_contract::SolCallBuilder::new_sol(&self.provider, &self.address, call)
        }
        ///Creates a new call builder for the [`findRoute`] function.
        pub fn findRoute(
            &self,
            tokenIn: alloy::sol_types::private::Address,
            tokenOut: alloy::sol_types::private::Address,
            amountIn: alloy::sol_types::private::primitives::aliases::U256,
            slippageBps: alloy::sol_types::private::primitives::aliases::U256,
        ) -> alloy_contract::SolCallBuilder<&P, findRouteCall, N> {
            self.call_builder(
                &findRouteCall {
                    tokenIn,
                    tokenOut,
                    amountIn,
                    slippageBps,
                },
            )
        }
        ///Creates a new call builder for the [`findRouteWithHints`] function.
        pub fn findRouteWithHints(
            &self,
            tokenIn: alloy::sol_types::private::Address,
            tokenOut: alloy::sol_types::private::Address,
            amountIn: alloy::sol_types::private::primitives::aliases::U256,
            slippageBps: alloy::sol_types::private::primitives::aliases::U256,
            extraData: alloy::sol_types::private::Bytes,
        ) -> alloy_contract::SolCallBuilder<&P, findRouteWithHintsCall, N> {
            self.call_builder(
                &findRouteWithHintsCall {
                    tokenIn,
                    tokenOut,
                    amountIn,
                    slippageBps,
                    extraData,
                },
            )
        }
        ///Creates a new call builder for the [`mergeRoutes`] function.
        pub fn mergeRoutes(
            &self,
            routes: alloy::sol_types::private::Vec<
                <StepMerging::Route as alloy::sol_types::SolType>::RustType,
            >,
            finalToken: alloy::sol_types::private::FixedBytes<32>,
        ) -> alloy_contract::SolCallBuilder<&P, mergeRoutesCall, N> {
            self.call_builder(
                &mergeRoutesCall {
                    routes,
                    finalToken,
                },
            )
        }
    }
    /// Event filters.
    impl<
        P: alloy_contract::private::Provider<N>,
        N: alloy_contract::private::Network,
    > PathFinderInstance<P, N> {
        /// Creates a new event filter using this contract instance's provider and address.
        ///
        /// Note that the type can be any event, not just those defined in this contract.
        /// Prefer using the other methods for building type-safe event filters.
        pub fn event_filter<E: alloy_sol_types::SolEvent>(
            &self,
        ) -> alloy_contract::Event<&P, E, N> {
            alloy_contract::Event::new_sol(&self.provider, &self.address)
        }
    }
}
