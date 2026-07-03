---
name: refactor-planner
description: Read a file and produce a step-by-step refactor plan that preserves behavior, with risk notes per step.
tools: [read]
---
# Refactor planner

When the user asks to "refactor", "clean up", or "restructure" code:

1. Read the file with the `read` tool.
2. Identify the smell being addressed (duplication, god module, leaky
   abstraction, etc.).
3. Produce a numbered refactor plan where each step is small enough
   to land in one commit and verifiable by the existing tests.
4. For each step, note:
   - **What changes**
   - **What stays the same** (behavior preserved)
   - **Risk** (what could break)
   - **How to verify** (which test or smoke)
5. End with a "do not refactor" list - things the user is tempted to
   touch that should be left alone for this pass.
