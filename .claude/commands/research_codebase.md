# Research Codebase

Use this command to answer a codebase question with current repository evidence.

## Process

1. Read any user-mentioned files completely before decomposing the question.
2. Use locator/analyzer/pattern agents when the topic spans more than one area.
3. Treat live code and tests as primary evidence; docs and `debug/aave/` are supporting context.
4. Include exact file paths and line numbers for important claims.
5. If the user asks for a durable writeup, create it under `docs/research/` and gather metadata with:

```bash
bash scripts/claude_spec_metadata.sh
```

## Research Scope Checklist

- Python package: `src/degenbot`
- Rust helpers: `rust/src`
- Tests: `tests`, `rust/tests`
- Architecture docs: `docs/architecture`
- Aave docs and debug reports: `docs/aave`, `debug/aave`
- Contract references: `contract_reference`

## Output Format

```markdown
## Summary
[direct answer]

## Evidence
- `path:line` - finding
- `path:line` - finding

## Architecture Notes
- code ownership boundary
- determinism/accounting implication

## Verification
- command that would verify the claim, if applicable

## Open Questions
- facts not proven from current repo state
```

## Rules

- Do not rely only on old notes.
- Do not write a plan when the user asked for research.
- Do not browse the web unless the user asks for external/current information or repo evidence is
  insufficient for a protocol fact.
