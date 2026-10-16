<h1 align="center">SAP Business One plugin for Claude</h1>

<p align="center">
  <em>Talk to your ERP. Look up balances, post invoices and payments, and build live dashboards —<br>
  in plain language.</em>
</p>

---

## See it in action

> **You:** What does customer C50000 owe, and what's overdue?
>
> **Claude:** C50000 has an open balance of 48,200.00 DKK across 3 invoices; 2 are overdue
> (14,500.00 DKK, oldest 41 days past due). Want the invoice list or a payment reminder drafted?

> **You:** Create an invoice for 10 hours of consulting to C50000.
>
> **Claude:** *Shows a receipt — customer, line, quantity, unit price, VAT, total, currency — and
> posts only after you say yes.*

> **You:** Registrer betaling fra kunden på faktura 1042.
>
> **Claude:** *Finds the open invoice, proposes the bank account, and asks you to confirm.*

## What you get

Thirteen skills that Claude picks up automatically, based on what you ask:

| Area | What Claude can do |
| --- | --- |
| **Lookups** | Balances, aging, top debtors, order / quotation / PO status — read-only |
| **Invoices & credit memos** | AR and AP invoices (item and service lines); credit memos; reversing posted documents |
| **Payments** | Apply incoming and outgoing payments to open invoices |
| **Sales & purchasing** | Quotation → order → delivery → invoice, and PO → goods receipt → AP invoice |
| **Journal entries** | Manual G/L postings, expense and receipt bookings, debits always equal credits |
| **Service calls** | Support tickets and activity logging |
| **Master data** | Create and maintain business partners and items |
| **Messages** | Send internal SAP messages and alerts to users or whole departments |
| **Live artifacts** | Refreshable dashboards and custom pages (work queues, forms, approvals) on live data |
| **Onboarding & orientation** | First-run tour, connection check, scheduled digests, and a reference for everything else |

Every skill answers in the language you write in — and triggers on Danish phrasing too
(*faktura*, *kassekladde*, *kreditnota*, *kunde har betalt*, …).

## Design principles

- **Discovery-first.** Every company database has its own chart of accounts, VAT groups, items, and
  payment accounts. The skills never hardcode them — they look everything up live in the connected
  database, so one plugin works for every company.
- **Confirm before posting.** Invoices, credit memos, payments, and journal entries are shown as a
  receipt (partner, lines, totals, tax, currency) and posted only after you say yes. Claude can also
  leave a draft in SAP for you to review there.
- **Graceful degradation.** A read-only or restricted server is fine: the skills detect which tools
  exist, fall back where they can, and tell you what is missing.
- **Skills only.** No bundled code, no telemetry, no data leaves through the plugin. See
  [PRIVACY.md](PRIVACY.md).

## How it fits together

```
 You ──▶ Claude Desktop ──▶ sap-b1 skills (this plugin: how to work in SAP B1)
                │
                └──▶ your SAP B1 MCP server (custom connector) ──▶ Service Layer ──▶ company DB
```

The plugin is the know-how; the MCP server is the connection. **The server is not part of this
repository**, so the plugin does nothing on its own — see [Requirements](#requirements).

## Requirements

- **Claude Desktop** (the skills also use Cowork for scheduled tasks, and claude.ai artifacts for
  dashboards and custom pages).
- **SAP Business One** with the **Service Layer** enabled.
- An **MCP server** reachable over HTTPS that exposes the `sap_b1_*` tools these skills call:
  `sap_b1_discover`, `sap_b1_get_document`, `sap_b1_sl_query`, `sap_b1_sl_write`,
  `sap_b1_create_draft`, `sap_b1_prepare_upload`, `sap_b1_attach_file`, and optionally
  `sap_b1_sql_query` / `sap_b1_sql_reference`. A server may expose fewer tools (for example
  read-only); the skills detect what is available and fall back or tell you what is missing.

## Install

**1. Install the plugin**

In **Claude Desktop**, add this repository as a plugin marketplace using its GitHub URL,
`https://github.com/Askinator/sap-b1-plugin`, then install the `sap-b1` plugin.

**2. Connect your company's server**

In **Claude Desktop**, go to **Settings → Connectors → Add custom connector**, give it a name
(e.g. `sap-b1`), and paste your server's MCP endpoint. Sign in when the connector prompts —
authentication is whatever your server uses (typically OAuth), handled by Claude's normal connector
flow.

**3. Say hello**

Ask Claude *"how do I get started with SAP B1?"* — the `sap-b1-getting-started` skill checks the
connection and walks you through the rest.

## Skills reference

| Skill | Purpose |
| --- | --- |
| `sap-b1-getting-started` | First-run onboarding: verify the connection, tour the skills, work in Cowork, set up a scheduled digest |
| `sap-b1-overview` | Orientation for anything the task skills don't cover: tool map, skill index, tenant-invariant reference |
| `sap-b1-lookups` | Read-only balances, aging, and order / quotation / PO status |
| `sap-b1-invoices` | AR / AP invoices (item and service lines) |
| `sap-b1-credit-memos` | AR / AP credit memos and reversing posted documents |
| `sap-b1-payments` | Apply incoming / outgoing payments to open invoices |
| `sap-b1-sales-process` | Quotation → order → delivery → invoice (copy-from-base) |
| `sap-b1-purchasing` | Purchase order → goods receipt → AP invoice (copy-from-base) |
| `sap-b1-journal-entries` | Manual G/L postings, debits = credits |
| `sap-b1-service-calls` | Support tickets and activity logging |
| `sap-b1-master-data` | Create / maintain business partners and items |
| `sap-b1-messages` | Send internal SAP B1 messages / alerts to users, named recipients, or a department |
| `sap-b1-live-artifacts` | Live claude.ai dashboards, or custom pages for anything else (work queues, forms, approvals), on live SAP B1 data |

## Use with care

These skills can create and post real documents in your ERP. Try them against a **test or demo
company database** first, read every summary before confirming it, and give the server's SAP user
only the permissions you are comfortable with Claude using. The software is provided as-is, without
warranty; you remain responsible for what gets posted.

## Contributing

Issues and questions are welcome on
[GitHub Issues](https://github.com/Askinator/sap-b1-plugin/issues). If you work in this repo —
human or AI agent — read [AGENTS.md](AGENTS.md) first; the short version is that the repo is public,
so **never commit real tenant data** (company or customer names, account or tax codes, server URLs,
credentials).

## License and trademarks

Copyright © 2026 Aske Paustian. All rights reserved. You may install and use the plugin; copying,
modifying, or redistributing it requires permission — see [LICENSE](LICENSE). The plugin collects
no data; see [PRIVACY.md](PRIVACY.md) and [TERMS.md](TERMS.md).

This is an independent project, not affiliated with or endorsed by SAP SE. SAP and
SAP Business One are trademarks or registered trademarks of SAP SE.
