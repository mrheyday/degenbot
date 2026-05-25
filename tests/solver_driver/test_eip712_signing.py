from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from degenbot.signing.eip712 import Eip712SigningError, sign_solution
from pydantic import BaseModel, SecretStr


def _typed_data() -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "Solution": [
                {"name": "auctionId", "type": "bytes32"},
                {"name": "score", "type": "uint256"},
            ],
        },
        "primaryType": "Solution",
        "domain": {
            "name": "Gnosis Protocol",
            "version": "v2",
            "chainId": 42161,
            "verifyingContract": "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
        },
        "message": {
            "auctionId": "0x" + "11" * 32,
            "score": 123,
        },
    }


def _install_fake_eth_account(monkeypatch: pytest.MonkeyPatch, captured: dict[str, Any]) -> None:
    class FakeAccount:
        @staticmethod
        def sign_typed_data(private_key: str, *, full_message: dict[str, Any]) -> SimpleNamespace:
            captured["private_key"] = private_key
            captured["full_message"] = full_message
            return SimpleNamespace(signature=b"\x44" * 65)

    # Patch the name where it is looked up: eip712 binds `Account` at import
    # time, so swapping sys.modules["eth_account"] after import has no effect.
    monkeypatch.setattr("driver.signing.eip712.Account", FakeAccount)


def test_sign_solution_signs_full_typed_data(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    _install_fake_eth_account(monkeypatch, captured)

    typed_data = _typed_data()
    signature = sign_solution(typed_data, SecretStr("0x" + "22" * 32))

    assert signature == b"\x44" * 65
    assert captured["private_key"] == "0x" + "22" * 32
    assert captured["full_message"] == typed_data
    assert captured["full_message"] is not typed_data


def test_sign_solution_unwraps_nested_typed_data(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    _install_fake_eth_account(monkeypatch, captured)

    typed_data = _typed_data()
    signature = sign_solution({"typedData": typed_data}, SecretStr("0x" + "33" * 32))

    assert signature == b"\x44" * 65
    assert captured["full_message"] == typed_data


def test_sign_solution_accepts_pydantic_container(monkeypatch: pytest.MonkeyPatch) -> None:
    class Container(BaseModel):
        typedData: dict[str, Any]  # noqa: N815 -- exercises the `typedData` extraction path in sign_solution

    captured: dict[str, Any] = {}
    _install_fake_eth_account(monkeypatch, captured)

    typed_data = _typed_data()
    signature = sign_solution(Container(typedData=typed_data), SecretStr("0x" + "44" * 32))

    assert signature == b"\x44" * 65
    assert captured["full_message"] == typed_data


def test_sign_solution_rejects_missing_primary_type() -> None:
    typed_data = _typed_data()
    del typed_data["primaryType"]

    with pytest.raises(Eip712SigningError, match="primaryType"):
        sign_solution(typed_data, SecretStr("0x" + "55" * 32))
