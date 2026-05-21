# Validate Plan

Use this command to validate that an implementation matches a plan and is ready for review.

## Process

1. Read the plan completely.
2. Check `git status --short`.
3. Review the relevant diff and changed files.
4. Compare actual changes to each plan phase and success criterion.
5. Run the required verification commands or state why they cannot run.

## Validation Report

```markdown
## Validation Report: [plan]

### Status
- Phase 1: implemented / partial / missing
- Phase 2: implemented / partial / missing

### Evidence
- `path:line` - matches plan
- `path:line` - deviation or risk

### Verification
- `command` - pass/fail/not run with reason

### Findings
- severity, file:line, risk, recommendation

### Residual Risk
- remaining manual checks or environment gaps
```

## Rules

- Findings lead the report when reviewing another change.
- Do not mark a phase complete only because a checkbox says so; verify code and tests.
- Do not hide failed commands.
- Preserve unrelated local changes.
