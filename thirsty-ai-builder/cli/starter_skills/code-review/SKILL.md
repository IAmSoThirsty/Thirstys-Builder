---
name: code-review
description: Read a source file and return a structured review covering correctness, security, style, and tests.
tools: [read]
---
# Code review

When the user asks you to "review", "audit", or "look at" a source file,
follow these steps:

1. Read the file with the `read` tool.
2. Return a review with four sections:
   - **Correctness** - bugs, edge cases, error handling
   - **Security** - auth, input validation, secrets, injection
   - **Style** - naming, structure, comments, dead code
   - **Tests** - what is covered, what is missing
3. Be specific: cite line numbers or function names.
4. End with a one-line summary: APPROVE / APPROVE-WITH-NITS / CHANGES-REQUESTED.
