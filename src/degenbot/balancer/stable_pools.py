from fractions import Fraction
from threading import Lock

import eth_abi.abi
from eth_typing import ChecksumAddress
from web3.types import TxParams

from degenbot.balancer.libraries import stable_math
from degenbot.balancer.libraries.scaling_helpers import (
    _compute_scaling_factor,
    _downscale_down,
    _upscale,
    _upscale_array,
)
from degenbot.balancer.libraries.weighted_math import _subtract_swap_fee_amount
from degenbot.balancer.types import BalancerV2PoolState
from degenbot.checksum_cache import get_checksum_address
from degenbot.connection import connection_manager
from degenbot.erc20 import Erc20Token, Erc20TokenManager
from degenbot.functions import encode_function_calldata
from degenbot.types.abstract import AbstractLiquidityPool
from degenbot.types.aliases import BlockNumber, ChainId
from degenbot.types.concrete import PublisherMixin


class BalancerV2StablePool(PublisherMixin, AbstractLiquidityPool):
    type PoolState = BalancerV2PoolState
    FEE_DENOMINATOR = 1 * 10**18

    def __init__(
        self,
        address: ChecksumAddress | str,
        *,
        chain_id: ChainId | None = None,
        state_block: BlockNumber | None = None,
        verify_address: bool = False,
        silent: bool = False,
    ) -> None:
        self.address = get_checksum_address(address)

        self._chain_id = chain_id if chain_id is not None else connection_manager.default_chain_id
        w3 = connection_manager.get_web3(self.chain_id)
        state_block = state_block if state_block is not None else w3.eth.block_number

        pool_id: bytes
        (pool_id,) = eth_abi.abi.decode(
            types=["bytes32"],
            data=w3.eth.call(
                transaction=TxParams(
                    to=self.address,
                    data=encode_function_calldata(
                        function_prototype="getPoolId()",
                        function_arguments=None,
                    ),
                ),
                block_identifier=state_block,
            ),
        )
        self.pool_id = pool_id

        vault_address: str
        (vault_address,) = eth_abi.abi.decode(
            types=["address"],
            data=w3.eth.call(
                transaction=TxParams(
                    to=self.address,
                    data=encode_function_calldata(
                        function_prototype="getVault()",
                        function_arguments=None,
                    ),
                ),
                block_identifier=state_block,
            ),
        )
        self.vault = get_checksum_address(vault_address)

        tokens: list[str]
        balances: list[int]
        tokens, balances, _ = eth_abi.abi.decode(
            types=["address[]", "uint256[]", "uint256"],
            data=w3.eth.call(
                transaction=TxParams(
                    to=self.vault,
                    data=encode_function_calldata(
                        function_prototype="getPoolTokens(bytes32)",
                        function_arguments=[self.pool_id],
                    ),
                ),
                block_identifier=state_block,
            ),
        )

        token_manager = Erc20TokenManager(chain_id=self.chain_id)
        self.tokens = tuple(
            token_manager.get_erc20token(
                address=get_checksum_address(token),
                silent=silent,
            )
            for token in tokens
        )

        # Scaling factors for Stable Pools are just 10**(18-decimals)
        # unless it's a Composable Stable Pool with rates, but we'll start with base Stable Pool.
        self.scaling_factors = tuple(_compute_scaling_factor(token) for token in self.tokens)

        (amp_value, _, _) = eth_abi.abi.decode(
            types=["uint256", "bool", "uint256"],
            data=w3.eth.call(
                transaction=TxParams(
                    to=self.address,
                    data=encode_function_calldata(
                        function_prototype="getAmplificationParameter()",
                        function_arguments=None,
                    ),
                ),
                block_identifier=state_block,
            ),
        )
        self.amplification_parameter = amp_value

        (fee,) = eth_abi.abi.decode(
            types=["uint256"],
            data=w3.eth.call(
                transaction=TxParams(
                    to=self.address,
                    data=encode_function_calldata(
                        function_prototype="getSwapFeePercentage()",
                        function_arguments=None,
                    ),
                ),
                block_identifier=state_block,
            ),
        )
        self.fee = Fraction(fee, self.FEE_DENOMINATOR)

        self._state_lock = Lock()
        self._state = BalancerV2PoolState(
            address=self.address,
            block=state_block,
            balances=tuple(balances),
        )

    @property
    def balances(self) -> tuple[int, ...]:
        return self.state.balances

    @property
    def chain_id(self) -> int:
        return self._chain_id

    @property
    def state(self) -> PoolState:
        return self._state

    def calculate_tokens_out_from_tokens_in(
        self,
        token_in: Erc20Token,
        token_in_quantity: int,
        token_out: Erc20Token,
        override_state: PoolState | None = None,
    ) -> int:
        token_in_index = self.tokens.index(token_in)
        token_out_index = self.tokens.index(token_out)

        # Apply fee to token_in_quantity
        amount_in_after_fee = _subtract_swap_fee_amount(
            amount=token_in_quantity,
            fee_percentage=int(self.fee * self.FEE_DENOMINATOR),
        )

        if override_state is not None:
            balances = list(override_state.balances)
        else:
            balances = list(self.balances)

        _upscale_array(amounts=balances, scaling_factors=self.scaling_factors)
        amount_in_scaled = _upscale(
            amount_in_after_fee, scaling_factor=self.scaling_factors[token_in_index]
        )

        invariant = stable_math._calculateInvariant(  # noqa: SLF001
            amplification_parameter=self.amplification_parameter,
            balances=balances,
        )

        amount_out_scaled = stable_math._calcOutGivenIn(  # noqa: SLF001
            amplification_parameter=self.amplification_parameter,
            balances=balances,
            token_index_in=token_in_index,
            token_index_out=token_out_index,
            token_amount_in=amount_in_scaled,
            invariant=invariant,
        )

        return int(
            _downscale_down(
                amount=amount_out_scaled, scaling_factor=self.scaling_factors[token_out_index]
            )
        )
