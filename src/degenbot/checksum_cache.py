import functools
from collections.abc import Callable
from typing import cast

from eth_typing import ChecksumAddress, HexAddress
from eth_utils.address import to_checksum_address as py_to_checksum_address

_rs_to_checksum_address: Callable[[HexAddress | bytes], str] | None
try:
    from degenbot.degenbot_rs import to_checksum_address as _imported_to_checksum_address

    _rs_to_checksum_address = cast(
        "Callable[[HexAddress | bytes], str]",
        _imported_to_checksum_address,
    )
except BaseException:
    _rs_to_checksum_address = None


@functools.lru_cache(maxsize=512)
def get_checksum_address(address: HexAddress | bytes) -> ChecksumAddress:
    converter = _rs_to_checksum_address or py_to_checksum_address
    return cast("ChecksumAddress", converter(address))
