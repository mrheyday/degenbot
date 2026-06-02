from pathlib import Path

import pytest

from degenbot.devtools.foundry_bindings import (
    DEFAULT_ALLOY_VERSION,
    DEFAULT_SELECTED_CONTRACTS,
    BindingWorkflowConfig,
    default_bindings_path,
    default_contracts_root,
    directories_match,
    normalize_generated_crate_manifest,
    validate_contracts_root,
)


def test_default_paths_match_mev_arbitrum_layout() -> None:
    repo_root = Path("/work/mev-arbitrum/vendor/degenbot")

    assert default_contracts_root(repo_root) == Path("/work/mev-arbitrum/contracts")
    assert default_bindings_path(repo_root) == repo_root / "rust/crates/contract_bindings"


def test_forge_commands_build_parent_contracts_then_bind_alloy_crate() -> None:
    config = BindingWorkflowConfig(
        contracts_root=Path("/work/mev-arbitrum/contracts"),
        bindings_path=Path("/work/mev-arbitrum/vendor/degenbot/rust/crates/contract_bindings"),
    )
    out_path = Path("/tmp/degenbot-contract-artifacts/out")
    cache_path = Path("/tmp/degenbot-contract-artifacts/cache")

    assert config.forge_build_command(out_path=out_path, cache_path=cache_path) == [
        "forge",
        "build",
        "--root",
        "/work/mev-arbitrum/contracts",
        "src",
        "--skip",
        "test",
        "--skip",
        "script",
        "--out",
        "/tmp/degenbot-contract-artifacts/out",
        "--cache-path",
        "/tmp/degenbot-contract-artifacts/cache",
    ]
    bind_command = config.forge_bind_command(
        overwrite=True,
        out_path=out_path,
        cache_path=cache_path,
    )
    assert bind_command[:11] == [
        "forge",
        "bind",
        "--bindings-path",
        "/work/mev-arbitrum/vendor/degenbot/rust/crates/contract_bindings",
        "--root",
        "/work/mev-arbitrum/contracts",
        "--crate-name",
        "degenbot_contract_bindings",
        "--skip-build",
        "--alloy-version",
        DEFAULT_ALLOY_VERSION,
    ]
    assert "--out" in bind_command
    assert "--cache-path" in bind_command
    assert bind_command[-1] == "--overwrite"
    for contract_name in DEFAULT_SELECTED_CONTRACTS:
        assert contract_name in bind_command


def test_validate_contracts_root_requires_foundry_workspace(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"foundry\.toml"):
        validate_contracts_root(tmp_path)

    (tmp_path / "foundry.toml").write_text("[profile.default]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="src"):
        validate_contracts_root(tmp_path)


def test_directories_match_ignores_foundry_and_cargo_build_artifacts(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    for root in (left, right):
        (root / "src").mkdir(parents=True)
        (root / "target").mkdir()
        (root / "cache").mkdir()
        (root / "src/lib.rs").write_text("pub mod executor;\n", encoding="utf-8")

    (left / "target/build.log").write_text("left build\n", encoding="utf-8")
    (right / "target/build.log").write_text("right build\n", encoding="utf-8")
    (left / "cache/solidity.json").write_text("left cache\n", encoding="utf-8")
    (right / "cache/solidity.json").write_text("right cache\n", encoding="utf-8")

    assert directories_match(left, right)

    (right / "src/lib.rs").write_text("pub mod settlement;\n", encoding="utf-8")

    assert not directories_match(left, right)


def test_generated_crate_manifest_uses_narrow_alloy_features(tmp_path: Path) -> None:
    bindings_path = tmp_path / "contract_bindings"
    bindings_path.mkdir()
    manifest = bindings_path / "Cargo.toml"
    manifest.write_text(
        "\n".join(
            [
                "[package]",
                'name = "degenbot_contract_bindings"',
                "",
                "[dependencies]",
                f'alloy = {{ version = "{DEFAULT_ALLOY_VERSION}", features = ["sol-types", "contract"] }}',
                'serde = { version = "1.0", features = ["derive"] }',
                "",
            ]
        ),
        encoding="utf-8",
    )

    normalize_generated_crate_manifest(bindings_path, alloy_version=DEFAULT_ALLOY_VERSION)

    assert (
        f'alloy = {{ version = "{DEFAULT_ALLOY_VERSION}", default-features = false, '
        'features = ["contract", "sol-types"] }'
    ) in manifest.read_text(encoding="utf-8")


def test_justfile_exposes_generated_contract_binding_recipes() -> None:
    justfile = Path(__file__).resolve().parents[1] / "justfile"

    text = justfile.read_text(encoding="utf-8")

    assert "gen-contract-bindings" in text
    assert "check-contract-bindings" in text
    assert 'contracts_root="../../contracts"' in text
    assert 'bindings_path="rust/crates/contract_bindings"' in text
    assert "degenbot.devtools.foundry_bindings generate" in text
    assert "degenbot.devtools.foundry_bindings check" in text
