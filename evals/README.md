# Skill evals

Checks that the right skill triggers for a realistic request (English and Danish) and that the
skill then behaves as written: codes resolved live, nothing posted without confirmation, no SAP
draft unless asked, lookups stay read-only. Each case runs as a single headless `claude -p`
session with this repo loaded via `--plugin-dir`, against a live company database.

## Safety: evals never write

A `PreToolUse` hook ([hooks/block_writes.py](hooks/block_writes.py)) blocks `sap_b1_sl_write`,
`sap_b1_create_draft`, `sap_b1_attach_file`, `sap_b1_prepare_upload`, and
`send_email_notification`. The tools stay *visible* so the skills follow their real
confirm-before-posting path; a call to one is blocked and fails the case. Runs also use
`--permission-mode default` with an allowlist of read tools only, so a CLI default of auto mode
is never inherited. Runs start in an empty temp directory, so this repo's `.claude/CLAUDE.md` and
project memory don't leak into the agent's context.

## Setup (once)

1. `evals/local.mcp.json` — the SAP server to test against (gitignored):
   `{ "mcpServers": { "sap-b1": { "type": "http", "url": "https://<your-server>/mcp" } } }`.
   If the server uses OAuth, start `claude --mcp-config evals/local.mcp.json` once, run `/mcp`,
   and authenticate; headless runs reuse the token.
2. `evals/local.json` — fills the `{placeholders}` in case prompts with records that exist in
   that database (gitignored). Copy [local.example.json](local.example.json) and fill it in.
3. `python3 evals/run.py --probe` — confirms the plugin loads, the `sap_b1_*` tools are present,
   the write-block hook fires, and the no-plugin baseline is clean.

## Running

```bash
python3 evals/run.py --runs 1                 # quick pass over every case
python3 evals/run.py --case 'invoices-*'      # one area, 3 runs each
python3 evals/run.py --baseline               # also run each case without the plugin
```

Default model is `claude-sonnet-5-5`; the rubric is graded by `haiku`. Results go to
`evals/results/<timestamp>/` (gitignored — traces contain live company data). Runs bill like any
Claude Code session: against the subscription's usage limits when logged in with claude.ai, or the
API key otherwise. The printed dollar figure is the API-price equivalent either way.

## Writing a case

One JSON file per case in [cases/](cases/):

| Field | Meaning |
| --- | --- |
| `name` | Case id (matches the file name) |
| `query` | The user prompt, sent verbatim. `{key}` is filled from `local.json` |
| `needs_sap` | Skip unless an MCP config is present |
| `expect_skills` | Skills that must be invoked (bare names, e.g. `sap-b1-invoices`) |
| `forbid_sap_skills` | Negative case: no `sap-b1-*` skill may be invoked |
| `must_call_any` | At least one of these `sap_b1_*` tools must be called |
| `must_not_call` | Tools that must not be called (defaults to every write tool) |
| `expected_behavior` | Rubric for the judge — only what the trace can't show deterministically |

**This repo is public.** Case files must not name a company, customer, item, account, or
document from any real database — put those in `local.json` and reference them as `{key}`.
