import eth_abi.abi
from eth_typing import ChecksumAddress
from web3.types import TxParams

from degenbot.balancer.libraries.fixed_point import mul_down
from degenbot.balancer.libraries.scaling_helpers import _compute_scaling_factor
from degenbot.balancer.stable_pools import BalancerV2StablePool
from degenbot.connection import connection_manager
from degenbot.functions import encode_function_calldata
from degenbot.types.aliases import BlockNumber, ChainId


class BalancerV2ComposableStablePool(BalancerV2StablePool):
    def __init__(
        self,
        address: ChecksumAddress | str,
        *,
        chain_id: ChainId | None = None,
        state_block: BlockNumber | None = None,
        verify_address: bool = False,
        silent: bool = False,
    ) -> None:
        super().__init__(
            address=address,
            chain_id=chain_id,
            state_block=state_block,
            verify_address=verify_address,
            silent=silent,
        )

        w3 = connection_manager.get_web3(self.chain_id)
        state_block = state_block if state_block is not None else w3.eth.block_number

        # Fetch rates for all tokens
        rates = []
        for token in self.tokens:
            try:
                # Composable Stable Pools usually have a getRate() method
                (rate,) = eth_abi.abi.decode(
                    types=["uint256"],
                    data=w3.eth.call(
                        transaction=TxParams(
                            to=self.address,
                            data=encode_function_calldata(
                                function_prototype="getTokenRate(address)",
                                function_arguments=[token.address],
                            ),
                        ),
                        block_identifier=state_block,
                    ),
                )
                rates.append(rate)
            except Exception:
                # Fallback if getTokenRate is not available or fails
                rates.append(10**18)

        self.rates = tuple(rates)

        # Update scaling factors to include rates
        # Scaling factor = (10**(18-decimals)) * rate / 1e18
        # In Balancer Solidity: _upscale(amount, scalingFactor) where scalingFactor = _computeScalingFactor(token) * rate / 1e18

        self.scaling_factors = tuple(
            mul_down(_compute_scaling_factor(token), rate)
            for token, rate in zip(self.tokens, self.rates, strict=True)
        )
