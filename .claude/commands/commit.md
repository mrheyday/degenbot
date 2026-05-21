# Commit Changes

Use this command when the user asks to commit local changes.

## Process

1. Run:

```bash
git status --short
git diff --stat
git diff
```

2. Separate unrelated local changes from this session's changes.
3. Stage only explicit files:

```bash
git add <file1> <file2>
```

4. Use concise imperative commit messages, for example:

```text
Add degenbot Claude workflow layer
Fix Aave liquidation debt burn matching
```

5. Commit only after the user confirms the staged file list and message.

## Rules

- Never use `git add -A` or `git add .` when unrelated changes exist.
- Never add Claude attribution, co-author lines, or generated-by text.
- Do not commit secrets, caches, build artifacts, `.venv`, `htmlcov`, or local databases.
- Include verification results in the final response after committing.
