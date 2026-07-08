# SAP Business One plugin for Claude

A Claude plugin of **skills** that teach Claude how to work with a hosted SAP Business One MCP
server. Install it from this repo, add your company's server as a custom connector, and Claude gets
both the `sap_b1_*` tools and the SAP B1 workflow know-how.

The MCP **server** is a separate project and stays hosted as-is (HTTP + OAuth / Cloudflare
Access). This repo contains only the skills — the connection is added per company as a custom
connector (see [Install](#install)), because each company database has its own server URL.

## What's inside

- `.claude-plugin/plugin.json` — plugin manifest (skills only; no bundled MCP server).
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

You run **one hosted server per company database** (one URL each). This single plugin serves all of
them: the skills are company-agnostic and the connection is added per company as a custom connector,
so each user points at their own company's server. Chart-of-accounts, VAT groups, items, and
payment accounts are **resolved live** per DB, never hardcoded.

## Install

**1. Install the skills**

Add this repo from the plugin/marketplace section of the customize panel (Claude Desktop /
claude.ai), then install the `sap-b1` plugin. In Claude Code the equivalent is:
```
/plugin marketplace add <this-repo-url-or-local-path>
/plugin install sap-b1@sap-b1-plugins
```

**2. Add your company's server as a custom connector**

In **Claude Desktop / claude.ai**: **Settings → Connectors → Add custom connector** (or
**Customize → Connectors**), name it (e.g. `sap-b1`), and paste your `https://…/mcp` endpoint. This
is a separate step from installing the plugin — the plugin ships skills only and does not bundle a
server, so each company enters its own URL here.

## Authentication

The client handles remote-server auth via its normal OAuth flow, so your existing Cloudflare Access
/ OAuth setup is unchanged. Authenticate the connector when it prompts.

## Updating

Bump `version` in `.claude-plugin/plugin.json`, commit, and push. Users run
`/plugin marketplace update` to pull the new skills/config. Keep skills current as SAP
configurations and workflows evolve.

## Validate

```
claude plugin validate . --strict
```
