from __future__ import annotations

import pytest

from degenbot.strategy_signals.github_reference_catalog import (
    GithubReferenceRisk,
    github_reference_repo,
    ranked_github_reference_repos,
    references_for_import_surface,
)


def test_github_reference_catalog_preserves_top_five_order() -> None:
    repos = ranked_github_reference_repos()

    assert [repo.repo_id for repo in repos] == [
        "cowprotocol-solvers-dto-alloy",
        "swap-path",
        "phantom-filler",
        "compass",
        "mev-kernel-final",
    ]
    assert [repo.rank for repo in repos] == [1, 2, 3, 4, 5]


def test_github_reference_catalog_records_guardrails_and_next_steps() -> None:
    for repo in ranked_github_reference_repos():
        assert repo.full_name.startswith("mrheyday/")
        assert repo.url.startswith("https://github.com/mrheyday/")
        assert repo.primary_use
        assert repo.import_surfaces
        assert repo.inspected_refs
        assert repo.guardrails
        assert repo.next_steps

    assert github_reference_repo("mev-kernel-final").risk is GithubReferenceRisk.HIGH
    assert any(
        "not a wholesale" in guardrail
        for guardrail in github_reference_repo("phantom-filler").guardrails
    )


def test_references_for_import_surface_matches_expected_repos() -> None:
    assert [
        repo.repo_id for repo in references_for_import_surface("cow")
    ] == ["cowprotocol-solvers-dto-alloy"]
    assert [repo.repo_id for repo in references_for_import_surface("route_hash")] == [
        "swap-path"
    ]
    assert [repo.repo_id for repo in references_for_import_surface("execution_policy")] == [
        "mev-kernel-final"
    ]
    assert references_for_import_surface("missing") == ()


def test_unknown_github_reference_repo_is_rejected() -> None:
    with pytest.raises(KeyError, match="unknown GitHub reference repo"):
        github_reference_repo("unknown")
