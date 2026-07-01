# SAP B1 Service Layer reference (tenant-invariant)

This file holds knowledge that is the same across every company database: entity names,
document object codes, and how to look values up live. It contains **no** company-specific
account numbers, tax codes, or item codes — resolve those against the connected DB.

## Common entity sets

| Purpose | Entity set |
| --- | --- |
| Business partners (customers/vendors) | `BusinessPartners` |
| Items | `Items` |
| Chart of accounts (G/L) | `ChartOfAccounts` |
| Sales order | `Orders` |
| AR invoice | `Invoices` |
| AR credit memo | `CreditNotes` |
| Delivery | `DeliveryNotes` |
| Sales quotation | `Quotations` |
| Purchase order | `PurchaseOrders` |
| AP invoice | `PurchaseInvoices` |
| Journal entry | `JournalEntries` |
| Service call | `ServiceCalls` |
| Activity | `Activities` |
| Incoming payment | `IncomingPayments` |
| Drafts (all draft docs) | `Drafts` |

Confirm exact field names per DB with `sap_b1_discover action="describe" name="<EntitySet>"`.

## DocObjectCodes (for `sap_b1_create_draft`)

| Document | DocObjectCode |
| --- | --- |
| Sales order | `oOrders` |
| AR invoice | `oInvoices` |
| AR credit memo | `oCreditNotes` |
| Delivery | `oDeliveryNotes` |
| Sales quotation | `oQuotations` |
| Purchase order | `oPurchaseOrders` |
| AP invoice | `oPurchaseInvoices` |
| Journal entry | `oJournalEntries` |

## Line types on documents

Marketing documents (`Invoices`, `Orders`, `PurchaseInvoices`, …) carry a `DocumentLines`
collection. Two shapes:

- **Item lines** — set `ItemCode` (+ `Quantity`, optional `UnitPrice`). G/L accounts derive from
  item/warehouse determination. Resolve `ItemCode` live from `Items`.
- **Service lines** — no item; set `AccountCode` (a G/L account) and `LineTotal`. The document
  must be in service mode (`DocType: "dDocument_Service"`). Resolve `AccountCode` live from
  `ChartOfAccounts`.

Tax per line uses a tax/VAT code field (commonly `TaxCode`/`VatGroup`). Resolve the valid code
live — do not assume a rate or code name.

## Live-lookup recipes

**Find a G/L account by name (Service Layer):**
```
sap_b1_sl_query
  entity: "ChartOfAccounts"
  select: "Code,Name,AcctName"
  filter: "contains(Name,'Sales')"
```

**Find a G/L account by name (SQL, if enabled):**
```
sap_b1_sql_query
  query: "SELECT AcctCode, AcctName FROM OACT WHERE AcctName LIKE :n"
  params: { "n": "%Bank%" }
```

**List tax/VAT groups:** first `sap_b1_discover action="search" query="Tax"` (or `"Vat"`) to find
the entity set, then `sap_b1_sl_query` it. Via SQL, table `OVTG` holds tax groups and rates.

**Understand a table before SQL:** `sap_b1_sql_reference table="OINV"` (or any table) returns the
official SDK field descriptions.

## Cardinality and safety

- Do not collapse ambiguous lookups. If a name matches several accounts/partners, show the
  candidates and ask which one.
- Keyed writes (`PATCH`/`DELETE`) must target a keyed resource, e.g. `Invoices(123)`.
- For financial postings, prefer a draft first, then finalize after user confirmation.
