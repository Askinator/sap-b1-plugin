---
name: sap-b1-overview
description: "Orientation for working with SAP Business One over the hosted Service Layer MCP server (sap_b1_* tools). Use at the start of any SAP B1 task — reading or creating documents, business partners, items, invoices, journal entries, service calls — to pick the right tool and to resolve account numbers, VAT groups, and payment accounts correctly. Also triggers on Danish SAP B1 requests (e.g. bogføring, kontoplan, debitor/kreditor, moms, forespørgsel i SAP) to route to the right task skill. Explains the discovery-first rule that keeps work correct across different company databases."
---

# SAP Business One — orientation

This plugin connects to a **hosted SAP B1 Service Layer MCP server** (one URL per company
database). The tools are named `sap_b1_*`. Before doing SAP work, read this skill to choose the
right tool and to follow the discovery-first rule below.

## The discovery-first rule (read this first)

Every company database has a **different chart of accounts, VAT/tax groups, item catalog, and
payment accounts**. Never hardcode or guess an account number, tax code, item code, or G/L
account from memory or from another company. **Resolve them live** against the connected DB:

- **Entities and fields** → `sap_b1_discover` (`action: "list_entity_sets" | "describe" | "search"`).
  Describe an entity before querying or writing to it to confirm field names for *this* DB.
- **G/L accounts** → query the `ChartOfAccounts` entity via `sap_b1_sl_query`
  (filter on `Name`/`AcctName`), or `sap_b1_sql_query` against table `OACT` if SQL is enabled.
- **VAT / tax groups** → query the tax-code entity (search discover for `Tax`/`Vat`), or table
  `OVTG` via SQL.
- **Table/column meanings** → `sap_b1_sql_reference` (e.g. `table: "OINV"`) before composing SQL.

If you cannot resolve a required code, **stop and ask the user** rather than inventing one.

### Resolve once, and in one round trip

Discovery-first means *never guess* — it does not mean *re-discover*. Within a conversation
against the same company DB:

- **Reuse what you already resolved.** An entity you described, or a `CardCode`, account, item, or
  VAT code you resolved earlier in this session, is still valid — don't describe or look it up
  again just because a different skill was invoked for the next task.
- **Describe on uncertainty, not ritual.** Run `describe` when you're unsure of a field name or a
  call failed — not as a mandatory step before every operation.
- **Batch independent lookups.** Resolving a partner and an item (or several accounts) are
  independent reads — issue them as parallel tool calls in a single turn, or fold them into one
  `sap_b1_sql_query` call when SQL is enabled, instead of paying sequential round trips.

## Which tool for which job

| Need | Tool |
| --- | --- |
| Explore schema / confirm fields | `sap_b1_discover` |
| Read a document (Orders, Invoices, Quotations, DeliveryNotes, PurchaseOrders) | `sap_b1_get_document` |
| Generic OData read of any entity set | `sap_b1_sl_query` |
| Create / update / delete via Service Layer | `sap_b1_sl_write` (POST / PATCH / DELETE) |
| Create a draft document | `sap_b1_create_draft` (needs `DocObjectCode`) |
| Get an upload token for a chat file | `sap_b1_prepare_upload` (then curl upload) |
| Attach a host/Base64 file to a record | `sap_b1_attach_file` |
| Raw read-only SQL (when enabled) | `sap_b1_sql_query` |
| Look up SAP table/field docs | `sap_b1_sql_reference` |

## Tool availability varies

The server gates tools with JSON capabilities. A restricted deployment may expose only
`sap_b1_get_document`; SQL tools exist only when the server has a SQL dialect configured. If a
tool you expected is missing, fall back: use `sap_b1_sl_query` when `sap_b1_sql_query` is
unavailable, and read documents you cannot write. Do not assume a tool is present — if a needed
capability is missing, tell the user what to enable.

## Working style

- Read before you write. Confirm the entity shape with `sap_b1_discover`, then act.
- Prefer **drafts** for anything financial: create with `sap_b1_create_draft`, show the user the
  compact receipt, and only add/post the real document after they confirm.
- **Settle attachment intent up front.** If a file is in the conversation (PDF, receipt, email,
  image) and you're about to create or find a record, ask with `AskUserQuestion` whether it should
  be attached **before** writing — not after the record exists. See the attachment section in
  `reference.md`.
- Use raw Service Layer names (entity sets, field names, OData options) — this MCP intentionally
  mirrors Service Layer rather than inventing a friendlier vocabulary.

## Rendering output

Render structural output through the `mcp__visualize__show_widget` tool, not markdown prose. These
tools ship in normal chat and Cowork sessions — reach for them by default; don't wait to confirm
they're available. Call `mcp__visualize__read_me` once before your first `show_widget` call, then
match the widget to the output:

- Capability tour or list of options → card grid.
- A single balance, aging summary, or document status → data-record card or metric cards.
- A draft document awaiting confirmation (invoice, credit memo, payment, journal entry) →
  data-record card styled as a receipt.
- Multi-row lists (open invoices, service call queue, PO lines) → keep as markdown tables, never
  widgets; the design system reserves tables for text.

This applies whether the turn is a live chat reply, a scheduled task, or an internal
verification/test pass — don't downgrade to prose because the turn feels programmatic rather
than conversational.

Only if `show_widget` is genuinely absent (a restricted deployment) fall back to plain prose, and
don't mention the widget system.

See `reference.md` in this skill for entity/DocObjectCode maps, the object-type / copy-from-base
recipe, the draft-first finalize rule, and file-attachment steps. The task skills cover specific
workflows:

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
