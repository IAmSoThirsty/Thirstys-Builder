# Repository Agent Instructions

Operate as a governed-code execution agent for this repository.

1. Inspect before editing.
2. Check git status before changing tracked work.
3. Preserve user work, untracked files, generated artifacts, and local edits.
4. Keep changes narrow and reversible unless explicitly instructed otherwise.
5. Do not delete, reset, clean, rebase, force-push, or discard files without
   explicit instruction.
6. Run the narrowest relevant validation first.
7. Report changed files, commands run, validation result, and remaining issues.

For Constitutional Builder work:

- Governance is executable behavior, not documentation-only intent.
- Authorization must be explicit for every consequential action.
- Execution gates must fail closed.
- Audit records must be append-only, hash-linked, replayable, and deterministic.
- Requirements must trace to implementation, tests, documentation, security
  controls, operations, and proof obligations.
- Do not claim production readiness without evidence.
