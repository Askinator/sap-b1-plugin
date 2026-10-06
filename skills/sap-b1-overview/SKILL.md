---
name: sap-b1-overview
description: "Orientation for SAP Business One over the hosted Service Layer MCP server (sap_b1_* tools): the tool map, which task skill handles what, and a tenant-invariant reference of entity sets, DocObjectCodes, and object types. Use for SAP B1 requests that no task skill covers — ad-hoc queries on other entities, exploring the schema or a table, choosing the right sap_b1_* tool, or questions about how the Service Layer works — and when unsure which SAP B1 skill fits. Also triggers on general Danish SAP B1 questions (e.g. kontoplan, forespørgsel i SAP, hvilken tabel, hvilket felt). Resolves every tenant-specific code live for the connected company database."
---

# SAP Business One — orientation

This plugin connects to a **hosted SAP B1 Service Layer MCP server** (one URL per company
database), whose tools are named `sap_b1_*`. Each task skill below carries the rules it needs; this
skill covers what falls between them — ad-hoc reads, schema questions, and picking a tool.

<!-- core-rules: identical in every SAP B1 skill; scripts/check.sh enforces it -->
## Core rules

- **Load the tools before judging what's there.** If the `sap_b1_*` tools are listed by name only,
  load them all with one `ToolSearch` (`query: "sap_b1"`) before telling the user a capability is
  missing. Once loaded, a missing tool is real gating: fall back (`sap_b1_sl_query` when
  `sap_b1_sql_query` is absent; read what you can't write) and tell the user what to enable.
- **Resolve every tenant code live.** Each company DB has its own chart of accounts, VAT groups,
  items, partners, and users. Look codes up against the connected DB — G/L accounts in
  `ChartOfAccounts` (field `Name`; SQL table `OACT`), tax groups via
  `sap_b1_discover action="search" query="Tax"` — never from memory or another company. If a code
  won't resolve, stop and ask; if a name matches several records, show them and ask which one.
- **Resolve once, in one round trip.** Reuse codes and entity descriptions already resolved this
  session. Run `describe` only when unsure of a field or after a call failed. Issue independent
  lookups as parallel calls, or as one `sap_b1_sql_query` when SQL is enabled.
- **Confirm before anything financial posts.** For invoices, credit memos, payments, journal
  entries, and sales/purchasing documents, show a confirmation receipt and post only after the
  user says yes. The receipt shows the amounts that will post — each line's quantity, unit price,
  and total (from the base document, the user, or the partner's price list: `ITM1.Price` where
  `PriceList` is the partner's `OCRD.ListNum`) and the document total; for a journal entry or
  payment, each account or invoice with its amount — not "set by SAP". Other writes follow this
  skill's own steps. Use `sap_b1_create_draft` only when the user wants a draft left in SAP;
  then either they approve it in SAP, or you post the real document and remove the draft with
  `sap_b1_sl_write method="DELETE" path="Drafts(<DraftEntry>)"` — never leave a draft beside the
  posted document. A draft skips mandatory-field checks, so give it every field the real document
  needs.
- **Settle attachment intent up front.** If a file (PDF, receipt, email, image) is in the
  conversation and you will create or find a record, ask with `AskUserQuestion` whether to attach
  it — in the same turn as the receipt, not after the record exists. If the user already said,
  don't ask again. With no file in the conversation, don't raise attachments at all.
- **Render chat output as widgets** — in scheduled and test runs too. Call
  `mcp__visualize__read_me` once, then `mcp__visualize__show_widget`: a confirmation receipt or a
  single balance/status as a data-record card, a set of options as a card grid. Multi-row lists
  stay markdown tables. Only if `show_widget` is absent, fall back to prose without mentioning it.
- **Every amount carries its currency code.** Balances are in the company's local currency —
  resolve its code live (`OADM.MainCurncy` via `sap_b1_sql_query`); without SQL, say the amount
  is in local currency rather than guess a code. Read the partner's `Currency` before the receipt
  (`##` means any currency: use the local one unless the user names another). When it is foreign,
  the receipt shows the lines in that currency, SAP's rate for the document date (`ORTT` via
  `sap_b1_sql_query`; without SQL, say SAP applies its rate on posting), and the local total with
  its code, marked as an estimate at that rate. After posting, report the totals SAP returned.
<!-- /core-rules -->

## Which tool for which job

| Need | Tool |
| --- | --- |
| Explore schema / confirm fields | `sap_b1_discover` (`action: "list_entity_sets" \| "describe" \| "search"`) |
| Read a document (Orders, Invoices, Quotations, DeliveryNotes, PurchaseOrders) | `sap_b1_get_document` |
| Generic OData read of any entity set | `sap_b1_sl_query` |
| Create / update / delete via Service Layer | `sap_b1_sl_write` (POST / PATCH / DELETE) |
| Create a draft document | `sap_b1_create_draft` (needs `DocObjectCode`) |
| Get an upload token for a chat file | `sap_b1_prepare_upload` |
| Attach a host/Base64 file to a record | `sap_b1_attach_file` |
| Raw read-only SQL (when enabled) | `sap_b1_sql_query` |
| Look up SAP table/field docs before composing SQL | `sap_b1_sql_reference` (e.g. `table: "OINV"`) |

The server gates tools per deployment: a restricted one may expose only `sap_b1_get_document`, and
the SQL tools exist only when a SQL dialect is configured. Use raw Service Layer names (entity sets,
field names, OData options) — this MCP mirrors the Service Layer rather than inventing its own
vocabulary.

## Task skills

Hand off to the matching skill when the request is one of these:

- `sap-b1-lookups` — read-only balances, aging, and document status.
- `sap-b1-invoices` — AR/AP invoices (item and service lines).
- `sap-b1-credit-memos` — AR/AP credit memos and reversing posted documents.
- `sap-b1-payments` — apply incoming (customer) and outgoing (vendor) payments to invoices.
- `sap-b1-sales-process` — quotation → order → delivery → invoice (copy-from-base).
- `sap-b1-purchasing` — purchase order → goods receipt → AP invoice (copy-from-base).
- `sap-b1-journal-entries` — manual G/L postings, debits = credits.
- `sap-b1-service-calls` — support tickets and activity logging.
- `sap-b1-master-data` — create/maintain business partners and items.
- `sap-b1-messages` — send internal SAP B1 messages/alerts to users, named recipients, or a department.
- `sap-b1-live-artifacts` — build a persisted, refreshable Cowork dashboard backed by live SAP B1 data.

## Reference

[reference.md](reference.md) holds the tenant-invariant tables and recipes: entity sets,
DocObjectCodes, item vs service line shapes and reading `DocType`, the VAT note, object types,
copy-from-base, draft finalize, the file-upload flow, live-lookup recipes for G/L accounts and tax
groups, and cardinality/safety rules. Read the section you need when a request goes beyond the task
skills.
