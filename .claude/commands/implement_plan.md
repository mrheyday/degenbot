# Implement Plan

Use this command to implement an approved plan.

## Starting Steps

1. Read the plan completely.
2. Read all files referenced by the plan.
3. Run `git status --short` and preserve unrelated changes.
4. Identify the first unchecked or unimplemented phase.
5. Use red/green TDD when adding behavior.

## Implementation Rules

- Keep edits scoped to the phase.
- Prefer existing local patterns over new abstractions.
- For Rust changes, do not manually rebuild or reinstall the extension; run the relevant tests.
- For database work, use `with db_session() as session:` from `degenbot.database.db_session`.
- For Aave/accounting work, exact matching is required.
- For MEV-Arbitrum integration logic, keep durable Python/Rust logic in this repo and parent glue thin.

## Verification

Use the smallest meaningful command first:

- Python narrow test: `uv run pytest path/to/test.py -q`
- Python suite: `just test-python`
- Rust suite: `just test-rust`
- Rust lint: `just lint-rust`
- Full gate: `just test-all` and `just lint`

Record every command and result in the final response.

## Stop Conditions

Stop and report clearly when:

- the plan contradicts current code;
- required secrets or network access are missing;
- a command fails for an environment reason after a reasonable retry;
- proceeding would overwrite unrelated local changes.
