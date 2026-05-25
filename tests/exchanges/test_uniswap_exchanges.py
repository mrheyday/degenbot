import random

import pytest
from eth_typing import ChainId, ChecksumAddress

from degenbot.checksum_cache import get_checksum_address
from degenbot.exceptions import DegenbotValueError
from degenbot.uniswap.deployments import (
    FACTORY_DEPLOYMENTS,
    ArbitrumCamelotV2,
    ArbitrumSushiswapV2,
    ArbitrumSushiswapV3,
    ArbitrumUniswapV2,
    ArbitrumUniswapV3,
    ArbitrumUniswapV4,
    UniswapFactoryDeployment,
    UniswapV2ExchangeDeployment,
    UniswapV3ExchangeDeployment,
    register_exchange,
)


def _generate_random_address() -> ChecksumAddress:
    return get_checksum_address(random.randbytes(20))


def test_register_v2_exchange() -> None:
    deployment_chain = 69
    factory_deployment_address = get_checksum_address(_generate_random_address())

    exchange = UniswapV2ExchangeDeployment(
        name="V2 DEX",
        chain_id=deployment_chain,
        factory=UniswapFactoryDeployment(
            address=factory_deployment_address,
            deployer=None,
            pool_init_hash="0x0420",
        ),
    )

    register_exchange(exchange)
    with pytest.raises(DegenbotValueError):
        register_exchange(exchange)
    assert deployment_chain in FACTORY_DEPLOYMENTS
    assert factory_deployment_address in FACTORY_DEPLOYMENTS[deployment_chain]
    assert FACTORY_DEPLOYMENTS[deployment_chain][factory_deployment_address] is exchange.factory

    del FACTORY_DEPLOYMENTS[deployment_chain][factory_deployment_address]
    del FACTORY_DEPLOYMENTS[deployment_chain]


def test_arbitrum_exchange_deployments_are_registered() -> None:
    assert ChainId.ARB1 in FACTORY_DEPLOYMENTS

    for exchange in (
        ArbitrumCamelotV2,
        ArbitrumSushiswapV2,
        ArbitrumSushiswapV3,
        ArbitrumUniswapV2,
        ArbitrumUniswapV3,
    ):
        assert exchange.factory.address in FACTORY_DEPLOYMENTS[ChainId.ARB1]
        assert FACTORY_DEPLOYMENTS[ChainId.ARB1][exchange.factory.address] is exchange.factory


def test_arbitrum_uniswap_v4_deployment_is_pinned() -> None:
    assert ArbitrumUniswapV4.chain_id == ChainId.ARB1
    assert ArbitrumUniswapV4.pool_manager.address == get_checksum_address(
        "0x360E68faCcca8cA495c1B759Fd9EEe466db9FB32"
    )
    assert ArbitrumUniswapV4.state_view.address == get_checksum_address(
        "0x76Fd297e2D437cd7f76d50F01AfE6160f86e9990"
    )


def test_register_v3_exchange() -> None:
    deployment_chain = 69
    factory_deployment_address = get_checksum_address(_generate_random_address())

    exchange = UniswapV3ExchangeDeployment(
        name="V3 DEX",
        chain_id=deployment_chain,
        factory=UniswapFactoryDeployment(
            address=factory_deployment_address,
            deployer=None,
            pool_init_hash="0x0420",
        ),
    )

    register_exchange(exchange)
    with pytest.raises(DegenbotValueError):
        register_exchange(exchange)

    assert deployment_chain in FACTORY_DEPLOYMENTS
    assert factory_deployment_address in FACTORY_DEPLOYMENTS[deployment_chain]
    assert FACTORY_DEPLOYMENTS[deployment_chain][factory_deployment_address] is exchange.factory

    del FACTORY_DEPLOYMENTS[deployment_chain][factory_deployment_address]
    del FACTORY_DEPLOYMENTS[deployment_chain]
