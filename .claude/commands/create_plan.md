# Create Plan

Use this command to create a degenbot implementation plan grounded in current code.

## Process

1. Read all provided files completely.
2. Locate current implementation, tests, and docs.
3. Identify the correct code home:
   - reusable Python market/protocol logic: `src/degenbot`
   - hot-path deterministic Rust helper: `rust/src`
   - parent TypeScript decision workflow: parent `coordinator/`
   - parent Solidity enforcement: parent `contracts/`
4. Present only questions that cannot be answered from the repository.
5. Write durable plans under `docs/plans/` when the user asks for a saved plan.

Use metadata from:

```bash
bash scripts/claude_spec_metadata.sh
```

## Plan Template

```markdown
# [Feature or Fix] Plan

## Current State
- `path:line` - existing behavior

## Desired End State
- observable behavior after the change
- verification command

## Out of Scope
- explicit exclusions

## Implementation Phases

### Phase 1: [name]
- Files:
- Changes:
- Tests:
- Success criteria:

### Phase 2: [name]
- Files:
- Changes:
- Tests:
- Success criteria:

## Risks
- determinism, accounting, database, or Rust binding risk

## Verification
- narrow command first
- broader command if warranted
```

## Rules

- Avoid backwards compatibility layers unless the user asks for one or production safety requires it.
- Do not propose tolerance-based accounting fixes.
- Do not move logic across repository boundaries without citing the boundary reason.
