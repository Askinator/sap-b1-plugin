# AGENTS.md

Guidance for AI agents (and humans) working in this repository.

## What this repo is — and is not

This is a **Claude Code / Claude Desktop plugin**, not an application. There is **no build, test,
lint, or runtime step**. The deliverable is:

- `.claude-plugin/plugin.json` — the plugin manifest (name, version). **Skills only — no bundled
  MCP server.**
- `.claude-plugin/marketplace.json` — a single-plugin marketplace so the repo is installable.
- `skills/` — markdown skills that teach Claude the SAP B1 workflows.

The connection is **not** bundled: each company adds its hosted server as a custom connector (see
"Multi-tenant model"). Users target Claude Desktop / claude.ai, where plugin `userConfig`
substitution does not run — so a bundled `.mcp.json` with `${user_config.mcp_url}` would only
produce a broken, locked connector dialog. Don't reintroduce one.

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
them: it ships skills only, and each company adds its server URL as a **custom connector** (Claude
Desktop / claude.ai: Settings → Connectors → Add custom connector). Keeping the connection out of
the plugin is why skills are company-agnostic — the same skill text works against any tenant because
all specifics are resolved live and the URL is never baked in.

## Skills layout and how they relate

- **`sap-b1-getting-started`** — first-run onboarding: confirms the MCP connection, tours the skills,
  recommends Cowork, and offers to set up a recurring read-only scheduled digest. Routing only — no
  writes of its own.
- **`sap-b1-overview`** — orientation: the discovery-first rule, the tool map, and tool-availability
  caveats. Its `reference.md` is the shared tenant-invariant knowledge base other skills point to —
  entity/DocObjectCode maps, the object-type table, the **copy-from-base** recipe, the **draft-first
  finalize** rule, and the file-attachment (`prepare_upload`/`attach_file`) flow.
- **Task skills** — `sap-b1-lookups` (read-only balances/aging/status), `sap-b1-invoices`,
  `sap-b1-credit-memos`, `sap-b1-payments`, `sap-b1-sales-process`, `sap-b1-purchasing`,
  `sap-b1-journal-entries`, `sap-b1-service-calls`, `sap-b1-master-data`, `sap-b1-messages`
  (internal SAP B1 messages/alerts), `sap-b1-live-artifacts` (refreshable Cowork dashboards).
  Each is self-contained
  but defers cross-cutting facts to the overview/reference rather than duplicating them. The
  lifecycle skills (sales, purchasing) and credit memos share the single copy-from-base recipe in
  `reference.md` instead of each re-explaining `BaseType`/`BaseEntry`/`BaseLine`.

Skills are auto-discovered and invoked based on their frontmatter **`description`** — that field is
the trigger surface, so keep it dense with the phrasings a real user would type.

**When you add or rename a skill, update all three hub docs that list the skill set:** the overview
skill index (`skills/sap-b1-overview/SKILL.md`), the `README.md` skills list, and the task-skill list
above in this file. These drifted twice (PRs #8/#9 added skills without touching them). `scripts/check.sh`
now enforces this — it fails if a `skills/*/` dir is missing from any hub, and CI runs it on every PR.
Run it locally before opening a PR: `scripts/check.sh`.

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
# Consistency check: skill-index coverage across the hub docs + manifest validation
scripts/check.sh

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

The first wave of planned skills has shipped: payments (`sap-b1-payments`), credit memos and
reversals (`sap-b1-credit-memos`), the purchasing lifecycle (`sap-b1-purchasing`), the sales
lifecycle (`sap-b1-sales-process`), and master-data creation (`sap-b1-master-data`). The shared
"copy from base document" recipe now lives in `reference.md` and is reused by all of them.

Still open (tracked as GitHub issues on
[Askinator/sap-b1-plugin](https://github.com/Askinator/sap-b1-plugin/issues)): deeper reconciliation
(bank statement matching), returns/RMA flows, and a dedicated attachments skill once the
`prepare_upload`/`attach_file` flow has been exercised against a live tenant. When adding one, keep
tenant-specific values resolved live and push any new tenant-invariant fact into `reference.md`.
