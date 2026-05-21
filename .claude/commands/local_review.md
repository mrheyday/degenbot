# Local Review

Use this command to review a local or remote branch without disturbing current work.

## Process

1. Parse the target:
   - local branch: `<branch>`
   - remote branch: `<remote>/<branch>`
   - GitHub fork form: `<username>:<branch>`
2. Check current dirty state with `git status --short`.
3. Add or fetch the remote only when needed.
4. Create a review worktree under:

```bash
/Volumes/PNYRP60PSSD/dev-projects/mev-arbitrum/worktrees/degenbot-review-<short-name>
```

5. Review as findings-first:
   - correctness and regressions;
   - deterministic accounting;
   - Rust/Python binding compatibility;
   - test coverage;
   - docs or debug report updates.

## Verification

Run focused checks based on the changed surface:

- `just test-python`
- `just test-rust`
- `just lint-rust`
- `just lint`

If a command is too broad for the review, run the narrow equivalent and state the residual risk.

## Output

Lead with findings ordered by severity. Include file and line references, then list verification
commands and remaining risks.
