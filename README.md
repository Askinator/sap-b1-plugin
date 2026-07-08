# SAP Business One plugin for Claude

A Claude plugin that **bundles the connection to a hosted SAP Business One MCP server together
with the skills** that teach Claude how to use it. Install it from this repo and Claude gets both
the `sap_b1_*` tools and the SAP B1 workflow know-how in one step.

The MCP **server** is a separate project and stays hosted as-is (HTTP + OAuth / Cloudflare
Access). This repo contains only the plugin: the remote connection config and the skills.

## What's inside

- `.mcp.json` — a **remote** MCP entry pointing at your hosted server (`type: "http"`). No local
  process is launched.
- `.claude-plugin/plugin.json` — plugin manifest with a `userConfig.mcp_url` field.
- `.claude-plugin/marketplace.json` — single-plugin marketplace so the repo is installable.
- `skills/` — workflow skills, auto-discovered and invoked by Claude on relevant tasks:
  - `sap-b1-getting-started` — first-run onboarding: verify the connection, tour the skills, work in Cowork, set up a scheduled digest.
  - `sap-b1-overview` — orientation, tool map, and the **discovery-first rule** (+ `reference.md`).
  - `sap-b1-lookups` — read-only balances, aging, and order/quotation/PO status.
  - `sap-b1-invoices` — AR/AP invoices (item and service lines).
  - `sap-b1-credit-memos` — AR/AP credit memos and reversing posted documents.
  - `sap-b1-payments` — apply incoming/outgoing payments to open invoices.
  - `sap-b1-sales-process` — quotation → order → delivery → invoice (copy-from-base).
  - `sap-b1-purchasing` — purchase order → goods receipt → AP invoice (copy-from-base).
  - `sap-b1-journal-entries` — manual GL postings, debits = credits.
  - `sap-b1-service-calls` — support tickets and activity logging.
  - `sap-b1-master-data` — create/maintain business partners and items.

## Multi-tenant model

You run **one hosted server per company database** (one URL each). This is a single plugin that
serves all of them: the endpoint is entered at install time via the `mcp_url` config value, so
each install points at that company's server. The skills are company-agnostic — chart-of-accounts,
VAT groups, items, and payment accounts are **resolved live** per DB, never hardcoded.

## Install

**Claude Code**
```
/plugin marketplace add <this-repo-url-or-local-path>
/plugin install sap-b1@sap-b1-plugins
```
You'll be prompted for the SAP B1 MCP server URL. Authenticate the remote server with `/mcp` if it
prompts for OAuth.

**Claude Desktop**
Add this repo from the plugin/marketplace section of the customize panel, install the `sap-b1`
plugin, and enter the server URL when prompted.

## Authentication

The client handles remote-server auth via its normal OAuth flow (`/mcp`), so your existing
Cloudflare Access / OAuth setup is unchanged. If a deployment needs a static token instead, add a
`headers` object to the server entry in `.mcp.json` (e.g. `"Authorization": "Bearer …"`), optionally
sourced from a `sensitive` `userConfig` field.

## Updating

Bump `version` in `.claude-plugin/plugin.json`, commit, and push. Users run
`/plugin marketplace update` to pull the new skills/config. Keep skills current as SAP
configurations and workflows evolve.

## Validate

```
claude plugin validate . --strict
```
