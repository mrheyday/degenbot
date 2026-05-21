# Create Worktree

Use this command when a change should be isolated from the current dirty checkout.

## Process

1. Check current state:

```bash
git status --short
git branch --show-current
git rev-parse --show-toplevel
```

2. Choose a branch name that describes the work:

```text
feature/<short-topic>
fix/<short-topic>
research/<short-topic>
```

3. Create the worktree outside the current checkout. Preferred location:

```bash
git worktree add -b <branch-name> /Volumes/PNYRP60PSSD/dev-projects/mev-arbitrum/worktrees/degenbot-<short-topic> HEAD
```

4. In the worktree, verify basic tooling:

```bash
just --list
git status --short
```

## Rules

- Do not overwrite or move the current checkout.
- Do not copy `.venv`, caches, build artifacts, or secrets.
- Keep parent `mev-arbitrum` worktrees separate from this nested degenbot repository unless the user
  explicitly asks for parent-repo changes.
- If the task touches only docs or `.claude`, a worktree is optional.
