"""Test double for CurveDataProvider."""


class FakeCurveDataProvider:
    def __init__(
        self,
        *,
        virtual_price: int | None = None,
        base_virtual_price: int | None = None,
        base_cache_updated: int | None = None,
        block_timestamp: int = 1_700_000_000,
        redemption_price: int | None = None,
        admin_balances: tuple[int, ...] | None = None,
        d: int | None = None,
        gamma: int | None = None,
        price_scale: tuple[int, ...] | None = None,
    ) -> None:
        self._virtual_price = virtual_price
        self._base_virtual_price = base_virtual_price
        self._base_cache_updated = base_cache_updated
        self._block_timestamp = block_timestamp
        self._redemption_price = redemption_price
        self._admin_balances = admin_balances
        self._d_value = d
        self._gamma = gamma
        self._price_scale = price_scale

    def virtual_price(self, block_number: int) -> int:
        if self._virtual_price is None:
            msg = "virtual_price not configured"
            raise ValueError(msg)
        return self._virtual_price

    def base_virtual_price(self, block_number: int) -> int:
        if self._base_virtual_price is None:
            msg = "base_virtual_price not configured"
            raise ValueError(msg)
        return self._base_virtual_price

    def base_cache_updated(self, block_number: int) -> int:
        if self._base_cache_updated is None:
            msg = "base_cache_updated not configured"
            raise ValueError(msg)
        return self._base_cache_updated

    def block_timestamp(self, block_number: int) -> int:
        return self._block_timestamp

    def redemption_price(self, block_number: int) -> int:
        if self._redemption_price is None:
            msg = "redemption_price not configured"
            raise ValueError(msg)
        return self._redemption_price

    def admin_balances(self, block_number: int) -> tuple[int, ...]:
        if self._admin_balances is None:
            msg = "admin_balances not configured"
            raise ValueError(msg)
        return self._admin_balances

    def d(self, block_number: int) -> int:
        if self._d_value is None:
            msg = "D not configured"
            raise ValueError(msg)
        return self._d_value

    def gamma(self, block_number: int) -> int:
        if self._gamma is None:
            msg = "gamma not configured"
            raise ValueError(msg)
        return self._gamma

    def price_scale(self, block_number: int) -> tuple[int, ...]:
        if self._price_scale is None:
            msg = "price_scale not configured"
            raise ValueError(msg)
        return self._price_scale
