import functools
from typing import cast

from eth_typing import ChecksumAddress, HexAddress
from eth_utils.address import to_checksum_address as py_to_checksum_address

try:
    from degenbot.degenbot_rs import to_checksum_address as rs_to_checksum_address
except BaseException:
    rs_to_checksum_address = None


@functools.lru_cache(maxsize=512)
def get_checksum_address(address: HexAddress | bytes) -> ChecksumAddress:
    converter = rs_to_checksum_address or py_to_checksum_address
    return cast("ChecksumAddress", converter(address))
