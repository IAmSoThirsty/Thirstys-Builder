---
name: release-runbook
description: Walk through the steps of cutting a ThirstyAI Builder release - run the gate, regenerate the artifact, tag, push.
tools: [read, shell]
---
# Release runbook

When the user says "release", "cut a release", "tag v0.x.0", or asks
about the release process, follow these steps IN ORDER. Do not skip a
step. Do not reorder.

1. **Confirm the working tree is clean.** `git status --short` should
   print nothing. If anything is dirty, stop and ask the user.
2. **Run the full local gate.** `python scripts/verify_all.py` from
   the repository root. The expected final line is
   `PASS: full local verification gate completed`. If anything fails,
   stop and report.
3. **Run the product test suite.** `python -m unittest discover -s
   thirsty-ai-builder/backend/tests`. Expect `OK` and 0 failures.
4. **Regenerate the release artifact.** Run, in order:
   - `python scripts/generate_release_evidence.py`
   - `python scripts/build_release_package.py`
   - `python scripts/sign_release_package.py`
   Each must print `PASS:`.
5. **Commit** the changes (gate, regenerated artifact, CHANGELOG).
   Use a Conventional Commits message.
6. **Tag** the commit. `git tag -a v0.X.Y -m "v0.X.Y - <one-line
   summary>"`. The tag message is the release headline.
7. **Push** both the branch and the tag: `git push origin main` then
   `git push origin v0.X.Y`.
8. **Report** the commit hash, the tag, and the SHA-256 of the
   release ZIP back to the user.

The user MUST confirm step 7 (the push) before it happens. The push
is not automatic.
