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

## Which tool for which job

| Need | Tool |
| --- | --- |
| Explore schema / confirm fields | `sap_b1_discover` |
| Read a document (Orders, Invoices, Quotations, DeliveryNotes, PurchaseOrders) | `sap_b1_get_document` |
| Generic OData read of any entity set | `sap_b1_sl_query` |
| Create / update / delete via Service Layer | `sap_b1_sl_write` (POST / PATCH / DELETE) |
| Create a draft document | `sap_b1_create_draft` (needs `DocObjectCode`) |
| Attach a file to a record | `sap_b1_attach_file` |
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
- Use raw Service Layer names (entity sets, field names, OData options) — this MCP intentionally
  mirrors Service Layer rather than inventing a friendlier vocabulary.

See `reference.md` in this skill for entity/DocObjectCode maps and live-lookup recipes. The task
skills — `sap-b1-invoices`, `sap-b1-journal-entries`, `sap-b1-service-calls` — cover specific
workflows.
