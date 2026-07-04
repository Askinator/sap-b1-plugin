# AGENTS.md

Guidance for AI agents (and humans) working in this repository.

## What this repo is — and is not

This is a **Claude Code / Claude Desktop plugin**, not an application. There is **no build, test,
lint, or runtime step**. The deliverable is:

- `.mcp.json` — a **remote** MCP connection (`type: "http"`) whose URL is injected at install time.
- `.claude-plugin/plugin.json` — the plugin manifest (name, version, `userConfig.mcp_url`).
- `.claude-plugin/marketplace.json` — a single-plugin marketplace so the repo is installable.
- `skills/` — markdown skills that teach Claude the SAP B1 workflows.

The SAP B1 **MCP server itself is a separate, hosted project and is NOT in this repo.** Do not look
for server code, request handlers, or `sap_b1_*` tool implementations here — they don't exist in
this tree. This repo only ships the *connection config* + the *skills*. Changes here are almost
always edits to skill markdown or the manifest/marketplace JSON.

## The one architectural invariant: discovery-first

Every company database has a **different chart of accounts, VAT/tax groups, item catalog, and
payment accounts.** The central design rule — stated in [skills/sap-b1-overview/SKILL.md](skills/sap-b1-overview/SKILL.md)
and repeated in every task skill — is that skills **never hardcode or guess** an account number,
tax code, item code, or G/L account. They **resolve them live** against the connected DB via
`sap_b1_discover` / `sap_b1_sl_query` / `sap_b1_sql_query`.

When editing or adding a skill, preserve this: any value that varies per tenant must be looked up,
not baked in. `skills/sap-b1-overview/reference.md` is the deliberate exception — it holds only
**tenant-invariant** knowledge (entity-set names, `DocObjectCode`s, line-type shapes, lookup
recipes). Company-specific numbers must never enter it.

## Multi-tenant model

One hosted server runs **per company database** (one URL each). This single plugin serves all of
them: the endpoint is entered at install via the `mcp_url` `userConfig` field, which flows into
`.mcp.json` as `${user_config.mcp_url}`. That indirection is why skills are company-agnostic — the
same skill text works against any tenant because all specifics are resolved live.

## Skills layout and how they relate

- **`sap-b1-overview`** — orientation: the discovery-first rule, the tool map, and tool-availability
  caveats. Its `reference.md` is the shared tenant-invariant knowledge base other skills point to.
- **Task skills** — `sap-b1-invoices`, `sap-b1-journal-entries`, `sap-b1-service-calls`,
  `sap-b1-work-logging`, `sap-b1-lookups` (read-only balances/aging/status). Each is self-contained
  but defers cross-cutting facts to the overview/reference rather than duplicating them.

Skills are auto-discovered and invoked based on their frontmatter **`description`** — that field is
the trigger surface, so keep it dense with the phrasings a real user would type.

## The MCP tools skills orchestrate

Skills assume these `sap_b1_*` tools (implemented in the separate server): `discover`,
`get_document`, `sl_query`, `sl_write` (POST/PATCH/DELETE), `create_draft`, `attach_file`,
`sql_query`, `sql_reference`. **Tool availability is gated per deployment by server capabilities** —
a restricted server may expose only reads, and SQL tools exist only when a SQL dialect is
configured. Skills must degrade gracefully (fall back to `sl_query`, read-only, and tell the user
what to enable) rather than assume a tool is present. Financial actions follow a **draft-first**
pattern: `create_draft` → show a compact receipt → post the real document only after user
confirmation.

## Localization decision (don't re-litigate)

We do **not** maintain per-language skill files. Claude replies in whatever language the user
writes, regardless of the skill body's language, and triggering keys off the `description`
frontmatter. So Danish support lives as **Danish trigger terms inside each skill's `description`**
(e.g. `faktura`, `kassekladde`, `bilag`, `kreditnota`), not as translated skill bodies. When adding
a skill, include Danish trigger terms in the description from the first draft. See
[issue #5](https://github.com/Askinator/sap-b1-plugin/issues/5) for the rationale.

## Common operations

There are no code commands. The operations that exist:

```bash
# Validate the plugin manifest + skills (run from repo root)
claude plugin validate . --strict

# Install locally for testing (in a Claude Code session)
/plugin marketplace add <this-repo-path-or-url>
/plugin install sap-b1@sap-b1-plugins

# Ship an update: bump "version" in .claude-plugin/plugin.json, commit, push.
# Users pull it with:
/plugin marketplace update
```

Note: the `claude` CLI must be on PATH for `plugin validate`; it is not available inside this repo's
Bash tool environment, so validation typically runs in an interactive Claude Code terminal.

## Planned work

Future skills are tracked as GitHub issues on
[Askinator/sap-b1-plugin](https://github.com/Askinator/sap-b1-plugin/issues): payments/reconciliation,
credit memos, the purchasing lifecycle (PO → goods receipt → AP invoice), and the sales lifecycle
(quotation → order → delivery → invoice). Several will need a shared "copy from base document"
recipe — add it once to `reference.md` rather than duplicating across skills.
