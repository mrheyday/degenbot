"""
Tests for AlloyProvider's direct interface.

These tests verify that AlloyProvider exposes the EthereumProvider
interface with correct method signatures and default values.
"""

import inspect

import pytest

from degenbot.anvil_fork import AnvilFork
from degenbot.provider import AlloyProvider

WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


@pytest.fixture
def alloy_provider(fork_mainnet_full: AnvilFork) -> AlloyProvider:
    """Create an AlloyProvider from the mainnet fork."""
    return AlloyProvider(fork_mainnet_full.http_url)


class TestAlloyProviderInterface:
    """Test AlloyProvider's direct interface."""

    def test_provider_has_required_properties(self, alloy_provider: AlloyProvider):
        """Test that AlloyProvider has required properties."""
        # Properties should exist on the class
        assert hasattr(type(alloy_provider), "chain_id")
        assert hasattr(type(alloy_provider), "block_number")

        # Properties should be property descriptors
        assert isinstance(type(alloy_provider).__dict__["chain_id"], property)
        assert isinstance(type(alloy_provider).__dict__["block_number"], property)

    def test_provider_has_required_methods(self, alloy_provider: AlloyProvider):
        """Test that AlloyProvider has required methods."""
        # Methods should be callable
        assert callable(alloy_provider.get_block_number)
        assert callable(alloy_provider.get_block)
        assert callable(alloy_provider.get_logs)
        assert callable(alloy_provider.call)
        assert callable(alloy_provider.get_code)
        assert callable(alloy_provider.is_connected)

    def test_provider_has_account_methods(self, alloy_provider: AlloyProvider):
        """Test that AlloyProvider has account-state methods."""
        assert callable(alloy_provider.get_balance)
        assert callable(alloy_provider.get_storage_at)
        assert callable(alloy_provider.get_transaction_count)

    def test_provider_accepts_any_network(self, fork_mainnet_full: AnvilFork):
        """Test provider can be constructed with the permissive Alloy network type."""
        provider = AlloyProvider(fork_mainnet_full.http_url, network="any")
        assert provider.network == "any"


class TestAlloyProviderMethodSignatures:
    """Test method signatures match the expected interface."""

    def test_get_code_signature(self, alloy_provider: AlloyProvider):
        """Test get_code accepts address and block_number parameters."""
        sig = inspect.signature(alloy_provider.get_code)
        params = list(sig.parameters.keys())
        assert "address" in params
        assert "block_number" in params

    def test_call_signature(self, alloy_provider: AlloyProvider):
        """Test call accepts to, data, and block_number parameters."""
        sig = inspect.signature(alloy_provider.call)
        params = list(sig.parameters.keys())
        assert "to" in params
        assert "data" in params
        assert "block_number" in params

    def test_get_block_signature(self, alloy_provider: AlloyProvider):
        """Test get_block accepts block_number parameter."""
        sig = inspect.signature(alloy_provider.get_block)
        params = list(sig.parameters.keys())
        assert "block_number" in params

    def test_get_logs_signature(self, alloy_provider: AlloyProvider):
        """Test get_logs accepts filter parameters."""
        sig = inspect.signature(alloy_provider.get_logs)
        params = list(sig.parameters.keys())
        # Should accept either LogFilter or keyword arguments
        assert "filter_param" in params or "from_block" in params


class TestAlloyProviderAccountMethods:
    """Test account-state methods backed by Alloy RPC calls."""

    def test_get_balance(self, alloy_provider: AlloyProvider):
        """Test get_balance returns a native balance."""
        balance = alloy_provider.get_balance(WETH_ADDRESS)
        assert isinstance(balance, int)
        assert balance >= 0

    def test_get_balance_with_block(self, alloy_provider: AlloyProvider):
        """Test get_balance supports an explicit block."""
        balance = alloy_provider.get_balance(WETH_ADDRESS, 18_000_000)
        assert isinstance(balance, int)
        assert balance >= 0

    def test_get_storage_at_is_callable(self, alloy_provider: AlloyProvider):
        """Test get_storage_at is callable (now implemented)."""
        assert callable(alloy_provider.get_storage_at)

    def test_get_transaction_count(self, alloy_provider: AlloyProvider):
        """Test get_transaction_count returns a nonce."""
        nonce = alloy_provider.get_transaction_count(WETH_ADDRESS)
        assert isinstance(nonce, int)
        assert nonce >= 0

    def test_get_transaction_count_with_block(self, alloy_provider: AlloyProvider):
        """Test get_transaction_count supports an explicit block."""
        nonce = alloy_provider.get_transaction_count(WETH_ADDRESS, 18_000_000)
        assert isinstance(nonce, int)
        assert nonce >= 0


class TestAlloyProviderConnection:
    """Test connection-related methods."""

    def test_is_connected_returns_true(self, alloy_provider: AlloyProvider):
        """Test is_connected returns True for AlloyProvider."""
        assert alloy_provider.is_connected() is True

    def test_close_method_exists(self, alloy_provider: AlloyProvider):
        """Test close method exists."""
        assert callable(alloy_provider.close)


class TestAlloyProviderContextManager:
    """Test context manager functionality."""

    def test_context_manager_enter_exit(self, fork_mainnet_full: AnvilFork):
        """Test AlloyProvider works as context manager."""
        with AlloyProvider(fork_mainnet_full.http_url) as provider:
            assert provider is not None
            assert isinstance(provider, AlloyProvider)


class TestProviderDefaults:
    """Test default parameter values."""

    def test_get_code_default_block_number(self, alloy_provider: AlloyProvider):
        """Test get_code has None default for block_number (latest)."""
        sig = inspect.signature(alloy_provider.get_code)
        default = sig.parameters["block_number"].default
        assert default is None

    def test_call_default_block_number(self, alloy_provider: AlloyProvider):
        """Test call has None default for block_number (latest)."""
        sig = inspect.signature(alloy_provider.call)
        default = sig.parameters["block_number"].default
        assert default is None

    def test_get_block_default_block_number(self, alloy_provider: AlloyProvider):
        """Test get_block has no default - requires block number."""
        sig = inspect.signature(alloy_provider.get_block)
        # block_number is required, no default
        assert sig.parameters["block_number"].default is inspect.Parameter.empty

    def test_get_storage_at_default_block_number(self, alloy_provider: AlloyProvider):
        """Test get_storage_at has None default for block_number (latest)."""
        sig = inspect.signature(alloy_provider.get_storage_at)
        default = sig.parameters["block_number"].default
        assert default is None

    def test_get_balance_default_block_number(self, alloy_provider: AlloyProvider):
        """Test get_balance has None default for block_number (latest)."""
        sig = inspect.signature(alloy_provider.get_balance)
        default = sig.parameters["block_number"].default
        assert default is None

    def test_get_transaction_count_default_block_number(self, alloy_provider: AlloyProvider):
        """Test get_transaction_count has None default for block_number (latest)."""
        sig = inspect.signature(alloy_provider.get_transaction_count)
        default = sig.parameters["block_number"].default
        assert default is None
