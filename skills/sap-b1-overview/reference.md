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
| Sales quotation | `Quotations` |
| Sales order | `Orders` |
| Delivery | `DeliveryNotes` |
| AR invoice | `Invoices` |
| AR credit memo | `CreditNotes` |
| Purchase order | `PurchaseOrders` |
| Goods receipt PO | `PurchaseDeliveryNotes` |
| AP invoice | `PurchaseInvoices` |
| AP credit memo | `PurchaseCreditNotes` |
| Journal entry | `JournalEntries` |
| Service call | `ServiceCalls` |
| Activity | `Activities` |
| Incoming payment (from customers) | `IncomingPayments` |
| Outgoing / vendor payment | `VendorPayments` |
| Drafts (all draft docs) | `Drafts` |

Confirm exact field names per DB with `sap_b1_discover action="describe" name="<EntitySet>"`.

## DocObjectCodes (for `sap_b1_create_draft`)

| Document | DocObjectCode |
| --- | --- |
| Sales quotation | `oQuotations` |
| Sales order | `oOrders` |
| Delivery | `oDeliveryNotes` |
| AR invoice | `oInvoices` |
| AR credit memo | `oCreditNotes` |
| Purchase order | `oPurchaseOrders` |
| Goods receipt PO | `oPurchaseDeliveryNotes` |
| AP invoice | `oPurchaseInvoices` |
| AP credit memo | `oPurchaseCreditNotes` |
| Journal entry | `oJournalEntries` |
| Incoming payment | `oIncomingPayments` |
| Outgoing / vendor payment | `oVendorPayments` |

## Line types on documents

Marketing documents (`Invoices`, `Orders`, `PurchaseInvoices`, …) carry a `DocumentLines`
collection. Two shapes:

- **Item lines** — set `ItemCode` (+ `Quantity`, optional `UnitPrice`). G/L accounts derive from
  item/warehouse determination. Resolve `ItemCode` live from `Items`.
- **Service lines** — no item; set `AccountCode` (a G/L account) and `LineTotal`. The document
  must be in service mode (`DocType: "dDocument_Service"`). Resolve `AccountCode` live from
  `ChartOfAccounts`.

Tax per line uses a VAT-group field — on standard Service Layer marketing documents this is
`VatGroup` (some localizations expose `TaxCode` instead).

**You usually don't need to set it.** When the field is omitted, SAP runs its normal tax
determination as the line is added: item lines default from the item master's sales/purchase VAT
group and the partner's tax status; service lines fall back to G/L-account or partner defaults,
which are configured less often. So **omit it by default and let SAP derive it.** Resolve and set
the code explicitly only when (a) the user asks for a specific tax treatment, (b) the post fails
with a missing/invalid tax code error, or (c) you already know this DB has no default for the
line (more common on service lines). When you do set it, resolve the valid code live — never
assume a rate or code name.

## Object types (for copy-from-base and `BaseType`)

SAP object-type numbers are **constant across every DB** (they identify the document *kind*, not
tenant data). Use them for the `BaseType` on a target document line when copying from a base
document, and when reading `sql_reference`.

| Document | Object type | Entity set |
| --- | --- | --- |
| Sales quotation | 23 | `Quotations` |
| Sales order | 17 | `Orders` |
| Delivery | 15 | `DeliveryNotes` |
| AR invoice | 13 | `Invoices` |
| AR credit memo | 14 | `CreditNotes` |
| Purchase order | 22 | `PurchaseOrders` |
| Goods receipt PO | 20 | `PurchaseDeliveryNotes` |
| AP invoice | 18 | `PurchaseInvoices` |
| AP credit memo | 19 | `PurchaseCreditNotes` |
| Journal entry | 30 | `JournalEntries` |
| Incoming payment | 24 | `IncomingPayments` |
| Outgoing / vendor payment | 46 | `VendorPayments` |

## Copy from base document

To pull a document forward in a lifecycle (quotation → order → delivery → invoice, or
PO → goods receipt → AP invoice), don't retype the lines — reference the base document so SAP
carries pricing, quantities, and links, and keeps the base document's status in sync.

On each **target** `DocumentLines` entry set:

- `BaseType` — the **object type** of the source document (see table above).
- `BaseEntry` — the source document's `DocEntry` (its internal key, not `DocNum`).
- `BaseLine` — the source line's `LineNum` (0-based).

```
sap_b1_create_draft
  DocObjectCode: "oInvoices"          # target: AR invoice from a sales order
  CardCode: "<same as base>"
  DocumentLines: [
    { "BaseType": 17, "BaseEntry": <Order DocEntry>, "BaseLine": 0 }
  ]
```

Copy only the lines/quantities the user wants (partial deliveries and invoices are normal); omit
`BaseLine` to copy a whole document only if the user confirmed every line. Resolve the base
document's `DocEntry` first with `sap_b1_sl_query` (filter on `DocNum`) — users usually quote the
`DocNum`, which is not the key.

## Draft-first: create, then finalize cleanly

`sap_b1_create_draft` writes a row to `Drafts` and **does nothing else** — it does not post, add,
close, or convert. So there are two clean ways to run the safety gate; pick one and don't leave a
stray draft behind:

- **Chat-receipt gate (default, no residue).** Build the payload, show the user a compact receipt
  in chat, and on confirmation `POST` the real document with `sap_b1_sl_write`. No `Drafts` row is
  created, so there is nothing to clean up.
- **Persisted draft (when the user wants one in SAP).** Use `sap_b1_create_draft` so a colleague
  can review/approve it in the SAP client. Capture the returned `DraftEntry`. To finalize:
  - preferred — the user **adds/approves the draft inside SAP**, which converts it in place; or
  - if finalizing over MCP, `POST` the real document **and then delete the draft** with
    `sap_b1_sl_write method="DELETE" path="Drafts(<DraftEntry>)"`.

Never both `create_draft` and `POST` the real document without deleting the draft — that leaves an
orphan draft duplicating a posted document.

## Attaching files (receipts, PDFs)

Two-step, because the MCP host usually can't see Claude's upload sandbox:

1. `sap_b1_prepare_upload` (no args) → returns `{ token, uploadUrl }`.
2. Upload the local file with curl:
   `curl -s -X POST "<uploadUrl>" -H "x-upload-token: <token>" -F "file=@<path>;type=<mime>" -F "entity=<EntitySet>" -F "key=<keyValue>"`.
3. If the response has `"attached": false`, link it manually:
   `sap_b1_sl_write method="PATCH" path="<EntitySet>(<key>)" body={ "AttachmentEntry": <n> }`.

For a file already readable by the SAP/MCP host (or in-memory Base64), `sap_b1_attach_file` handles
it directly with `mode` `server_path` / `multipart` / `base64` and an optional `target` to link it.

## Live-lookup recipes

**Find a G/L account by name (Service Layer):**
```
sap_b1_sl_query
  entity: "ChartOfAccounts"
  select: "Code,Name"
  filter: "contains(Name,'Sales')"
```
The Service Layer field is `Name` — there is no `AcctName` property on `ChartOfAccount` (that
column name belongs to the SQL table `OACT`, below). `Code` is the account key you pass as an
`AccountCode` on document/journal lines.

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
