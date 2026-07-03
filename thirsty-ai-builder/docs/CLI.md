# Thirsty CLI — Reference

`thirsty` is a local coding agent that talks to the ThirstyAI Builder
backend. It runs on your hardware, signs no keys to the cloud, and is
honest about what's on and what's off.

## Activation

**One-time install:**

```bash
cd thirsty-ai-builder/cli
pip install -e .
```

This puts `thirsty` on your PATH. First run creates:

```
~/.thirsty-ai-builder/
├── config.toml        # backend URL, model, profile
├── skills/             # user-installed skills (SKILL.md)
│   ├── code-review/
│   ├── refactor-planner/
│   ├── release-runbook/
│   └── _drafts/        # drafts from `thirsty skill distill`
└── sessions/           # one JSON per CLI invocation
```

**Required env vars:**

```bash
export THIRSTY_AI_API_KEY=<your CB_API_KEY>          # bearer token
export THIRSTY_AI_TOOLS_ENABLED=1                    # opt-in for /api/tools/*
```

The CLI uses `THIRSTY_AI_BACKEND_URL` (default `http://127.0.0.1:8001`)
and `THIRSTY_AI_MODEL` (default `qwen2.5-coder:7b`) if set.

**Verify the install:**

```bash
thirsty doctor
# expected: backend health: ok  product=ThirstyAI Builder
#           llm_provider:  ollama
```

## Subcommands

### REPL (interactive)

```bash
thirsty                                # default profile (balanced)
thirsty --profile precise              # lower temperature, shorter context
thirsty --profile creative             # higher temperature, longer context
```

Inside the REPL:

```
:q / :quit / :exit    leave
:help                this help
:skills              list loaded skills
:profile <name>      switch profile (precise|balanced|creative)
```

### One-shot (single message, no REPL)

```bash
thirsty "fix the auth bug in server.py"
thirsty --profile precise "refactor the policy bundle"
thirsty "what does the audit log say about the last 5 PRs"
```

### Config

```bash
thirsty config show                    # print effective config
thirsty config set <key> <value>       # keys: backend_url, model, profile
thirsty config set profile precise
```

### Skills

```bash
thirsty skill list                     # live (loaded) skills
thirsty skill list --drafts            # draft skills awaiting approval
thirsty skill show <name>              # print a skill's SKILL.md
thirsty skill new <name>               # scaffold a new skill directory
thirsty skill edit <name>              # open SKILL.md in $EDITOR
thirsty skill distill --last 10        # extract patterns from 10 recent sessions
thirsty skill distill --last 20 --min-occurrences 5
thirsty skill approve <name>           # promote a draft to live
thirsty skill reject <name>            # delete a draft
```

### Sessions

```bash
thirsty session list                   # 20 most recent session JSON files
```

### Doctor

```bash
thirsty doctor                         # connectivity + config + LLM health
```

## Model profiles (skill level)

Three named profiles. Each maps to Ollama generation options. Switch
with `--profile <name>` or in the REPL with `:profile <name>`.

| Profile    | Temperature | num_ctx | top_p | Best for |
|------------|-------------|---------|-------|----------|
| `precise`  | 0.2         | 4096    | 0.9   | Factual Q&A, audits, code review |
| `balanced` | 0.7         | 8192    | 0.95  | Default. Coding, refactoring, debugging |
| `creative` | 0.9         | 16384   | 0.98  | Design exploration, brainstorming, naming |

Profiles live in `cli/thirsty_ai_builder_cli/config.py::PROFILES`. Add
yours by extending the dict.

## Tools (backend)

The CLI dispatches to 6 backend tool endpoints. They are **opt-in**:
the backend refuses to serve them unless `THIRSTY_AI_TOOLS_ENABLED=1`
is set. Two of them — `write` and `shell` — additionally require a
6-digit `confirm_token` that the CLI prints to your terminal. You
type the code back. The token is valid for 60 seconds and tied to
the exact (tool, args) pair.

| Tool       | Args                              | Confirm? | Purpose |
|------------|-----------------------------------|----------|---------|
| `read`     | `path`, `max_bytes`               | No       | Read a text file |
| `write`    | `path`, `content`                 | **Yes**  | Write a file |
| `edit`     | `path`, `find`, `replace`, `expected_occurrences` | No | Find-and-replace in a file |
| `shell`    | `command`, `cwd`, `timeout_seconds` | **Yes** | Run a shell command |
| `grep`     | `pattern`, `path`, `max_matches`  | No       | Regex search across files |
| `listdir`  | `path`, `max_entries`             | No       | List directory entries |

The shell tool has a 12-pattern blocklist (rm -rf /, dd of=/dev/,
mkfs, fork bombs, shutdown/reboot/halt, etc.). It is defence in
depth — the confirm token is the primary control.

## Skills (self-improvement)

A skill is a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: my-skill
description: One-line description used for matching.
tools: [read, grep]
---
# Steps
1. Read the file at <path>
2. ...
```

The CLI loads all skills from `~/.thirsty-ai-builder/skills/` on
launch. For each user message, it picks the best-matching skill by
description token overlap and injects the body into the system prompt.

**Self-improvement:** after several sessions, run

```bash
thirsty skill distill --last 20
```

The CLI reads the last 20 session logs, finds tool sequences that
appeared 3+ times (default), and writes each pattern as a draft
skill to `~/.thirsty-ai-builder/skills/_drafts/`. You then:

```bash
thirsty skill list --drafts           # see the drafts
thirsty skill show distill-03-read    # read one
thirsty skill edit distill-03-read    # refine it in $EDITOR
thirsty skill approve distill-03-read  # promote to live
# or
thirsty skill reject distill-03-read   # discard
```

Once approved, the skill loads on the next `thirsty` launch and
matches future user messages against its description.

The three starter skills ship under
`thirsty-ai-builder/cli/starter_skills/`:

```bash
cp -r thirsty-ai-builder/cli/starter_skills/* ~/.thirsty-ai-builder/skills/
```

## Security model

- The bearer token (`THIRSTY_AI_API_KEY`) is sent on every request.
  Set it via env, not via `~/.thirsty-ai-builder/config.toml`.
- Tool endpoints are OFF by default. The backend returns 503 from
  every tool route until `THIRSTY_AI_TOOLS_ENABLED=1` is set.
- `write` and `shell` are gated by a `confirm_token`. The CLI asks
  the user; the backend verifies. The token is single-use,
  fingerprint-bound, and 60s-TTL.
- All file paths must be relative. Absolute paths and `..` are
  rejected. The CLI and the backend both enforce this.
- All bodies are capped at 1 MiB by the existing
  `RequestSizeLimitMiddleware`.

## What the CLI does NOT do

- It does not fine-tune the model. The Ollama GGUF weights are
  fixed; "self-improvement" is a *user-approved* skill registry,
  not weight updates.
- It does not run a server. It is a client. The backend is the
  FastAPI process you already run.
- It does not pull models. Run `ollama pull <model>` yourself.
- It does not bypass the confirm-token gate. There is no
  `--force-write` flag, no `--no-confirm` flag, no escape hatch.
