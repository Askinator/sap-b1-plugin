# SAP Business One plugin for Claude

Skills that teach Claude how to work in **SAP Business One** — look up balances and order status,
create invoices, credit memos, payments, and journal entries, run the sales and purchasing
lifecycles, log service calls, and maintain business partners and items.

The plugin contains **skills only**. The actual connection to SAP B1 comes from an MCP server that
talks to your company's Service Layer; you add that server to Claude yourself as a custom connector.
**The server is not part of this repository**, so the plugin does nothing on its own — see
[Requirements](#requirements).

## Requirements

- **Claude Desktop** (the skills also use Cowork for dashboards and scheduled tasks).
- **SAP Business One** with the **Service Layer** enabled.
- An **MCP server** reachable over HTTPS that exposes the `sap_b1_*` tools these skills call:
  `sap_b1_discover`, `sap_b1_get_document`, `sap_b1_sl_query`, `sap_b1_sl_write`,
  `sap_b1_create_draft`, `sap_b1_prepare_upload`, `sap_b1_attach_file`, and optionally
  `sap_b1_sql_query` / `sap_b1_sql_reference`. A server may expose fewer tools (for example read-only); the skills
  detect what is available and fall back or tell you what is missing.

## Install

**1. Install the plugin**

In **Claude Desktop**, add this repository as a plugin marketplace using its GitHub URL,
`https://github.com/Askinator/sap-b1-plugin`, then install the `sap-b1` plugin.

**2. Connect your company's server**

In **Claude Desktop**, go to **Settings → Connectors → Add custom connector**, give it a name
(e.g. `sap-b1`), and paste your server's MCP endpoint. Sign in when the connector prompts —
authentication is whatever your server uses (typically OAuth), handled by Claude's normal connector
flow.

Then ask Claude *"how do I get started with SAP B1?"* — the `sap-b1-getting-started` skill checks the
connection and walks you through the rest.

## How it works

- **Discovery-first.** Every company database has its own chart of accounts, VAT groups, items, and
  payment accounts. The skills never hardcode these — they look them up live in the connected
  database before using them.
- **Confirm before posting.** For invoices, credit memos, payments, and journal entries, Claude
  shows a summary of the document (partner, lines, totals, tax) and posts only after you confirm.
  It can also leave a draft in SAP for you to review there.
- **English and Danish.** Skills trigger on Danish requests too (*faktura*, *kassekladde*,
  *kreditnota*, …); Claude answers in the language you write in.

## Skills

Claude picks these up automatically for relevant requests:

- `sap-b1-getting-started` — first-run onboarding: verify the connection, tour the skills, work in Cowork, set up a scheduled digest.
- `sap-b1-overview` — orientation, tool map, and the discovery-first rule (+ `reference.md`).
- `sap-b1-lookups` — read-only balances, aging, and order/quotation/PO status.
- `sap-b1-invoices` — AR/AP invoices (item and service lines).
- `sap-b1-credit-memos` — AR/AP credit memos and reversing posted documents.
- `sap-b1-payments` — apply incoming/outgoing payments to open invoices.
- `sap-b1-sales-process` — quotation → order → delivery → invoice (copy-from-base).
- `sap-b1-purchasing` — purchase order → goods receipt → AP invoice (copy-from-base).
- `sap-b1-journal-entries` — manual G/L postings, debits = credits.
- `sap-b1-service-calls` — support tickets and activity logging.
- `sap-b1-master-data` — create/maintain business partners and items.
- `sap-b1-messages` — send internal SAP B1 messages/alerts to users, named recipients, or a department.
- `sap-b1-live-artifacts` — build a persisted, refreshable Cowork dashboard backed by live SAP B1 data.

## Use with care

These skills can create and post real documents in your ERP. Try them against a **test or demo
company database** first, read every summary before confirming it, and give the server's SAP user
only the permissions you are comfortable with Claude using. The software is provided as-is, without
warranty; you remain responsible for what gets posted.

## License and trademarks

Copyright © 2026 Aske Paustian. All rights reserved. You may install and use the plugin; copying,
modifying, or redistributing it requires permission — see [LICENSE](LICENSE).

This is an independent project, not affiliated with or endorsed by SAP SE. SAP and
SAP Business One are trademarks or registered trademarks of SAP SE.
