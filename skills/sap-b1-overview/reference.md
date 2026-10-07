# SAP B1 Service Layer reference (tenant-invariant)

This file holds knowledge that is the same across every company database: entity names,
document object codes, and how to look values up live. It contains **no** company-specific
account numbers, tax codes, or item codes — resolve those against the connected DB.

## Contents

- Common entity sets
- DocObjectCodes (for `sap_b1_create_draft`)
- Line types on documents — item vs service lines, reading `DocType`, the VAT note
- Object types (for copy-from-base and `BaseType`)
- Copy from base document
- Draft-first: create, then finalize cleanly
- Attaching files — settle intent before creating; the upload flow
- Live-lookup recipes — G/L accounts, tax groups, SQL table docs
- Cardinality and safety

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

**Reading a document: check `DocType` before judging the lines.** On a service document every line
has `ItemCode: null` and `Quantity: 0` **by design** — the amount lives in `LineTotal` and the G/L
in `AccountCode`. That is not a truncated response or a failed read, so don't re-query with
different field selections trying to "fix" it. Read the header `DocType` first
(`dDocument_Items` / `dDocument_Service`; `I` / `S` in the SQL tables) and interpret the lines
accordingly.

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
  in chat (the *confirmation receipt*), and on confirmation `POST` the real document with
  `sap_b1_sl_write`. No `Drafts` row is created, so there is nothing to clean up.
- **Persisted draft (when the user wants one in SAP).** Use `sap_b1_create_draft` so a colleague
  can review/approve it in the SAP client. Capture the returned `DraftEntry`. To finalize:
  - preferred — the user **adds/approves the draft inside SAP**, which converts it in place; or
  - if finalizing over MCP, `POST` the real document **and then delete the draft** with
    `sap_b1_sl_write method="DELETE" path="Drafts(<DraftEntry>)"`.

Never both `create_draft` and `POST` the real document without deleting the draft — that leaves an
orphan draft duplicating a posted document.

Drafts skip mandatory-field checks that a real `POST` enforces (e.g. a sales order's `DocDueDate`),
so a draft that saved fine can still fail to post or convert. Build the draft with every field the
real document needs.

## Attaching files (receipts, PDFs)

### Settle attachment intent *before* creating the record

Whenever a file is present in the conversation (a PDF, receipt, email, image the user attached or
pointed at) and the task will create or find a SAP record, ask **up front — before any write** —
whether that file should end up on the record. Ask it with `AskUserQuestion` as part of the same
turn where you confirm the document details, not as a follow-up after the record exists. Asking
afterwards makes the attachment feel like an afterthought and forces a second round trip.

Typical question — header `Attachment`, one question, options:

- **Attach to the record** — upload `<filename>` to the invoice/journal entry/service call once
  it's created.
- **Don't attach** — create the record only; the file stays in chat.

Then carry the answer through: create/locate the record, and if they said yes, run the upload
immediately after and report both in one summary ("Invoice 1042 posted, `bilag.pdf` attached").
If the user already said something like "book this receipt and attach the PDF", that's the answer —
don't re-ask.

### The upload flow

Two-step, because the MCP host usually can't see Claude's upload sandbox:

1. `sap_b1_prepare_upload` with top-level `targetEntity` and `targetKey` (both or neither):
   - `targetEntity` — the entity set (e.g. `PurchaseInvoices`, `Drafts`)
   - `targetKey` — a number for numeric keys (`DocEntry`), a string for keys like `CardCode`

   Returns `{ token, expiresInSeconds, uploadUrl, targetEntity, targetKey }`. The target is bound
   into the token — this is the only place to set it. The token lives 300 seconds.
2. Upload the local file as an HTTP `POST` to `uploadUrl` with `multipart/form-data`:
   - header `x-upload-token: <token>`
   - form field `file` — the local file, with its MIME type — and **no other field**. `entity`,
     `key`, `targetEntity`, `targetKey`, `fileName`, `fileExtension` are rejected with 400.

   The token is single-use and consumed by any attempt, success or failure; every retry needs a
   fresh `sap_b1_prepare_upload`.
3. A 200 returns `{ attachmentEntry, attached, targetPath?, renamedFrom?, uploadedFile }`. If the
   target already has an `AttachmentEntry`, the file is appended to that `Attachments2` entry;
   otherwise a new entry is created and linked.

**Renames.** If the name is already taken in SAP's attachment folder, the server stores the file
under a suffixed name (`bilag.pdf` → `bilag_1.pdf`, `bilag_2.pdf`, …) and returns `renamedFrom`
with the original. When it is present, tell the user the stored name (`uploadedFile.fileName`).

**Errors** answer `{ error, detail }` with SAP's message in `detail` — always show it, and never
report a failed upload as attached:

| Status | Meaning |
| --- | --- |
| 400 | Invalid input (e.g. an extra form field) |
| 401 | Token missing, already used, or expired |
| 409 | Name still taken after 10 suffixes — rename the file and retry with a new token |
| 422 | SAP rejected the request |
| 503 | SAP unreachable |

If the attachment was created but linking failed, the 422 body also carries `attachmentEntry` and
`"attached": false`; the same holds for a 200 from an upload without a target. Don't re-upload —
link it: `sap_b1_sl_write method="PATCH" path="<EntitySet>(<key>)" body={ "AttachmentEntry": <n> }`.

### `sap_b1_attach_file`

One call, for a file that needs no upload step. Inputs: `mode`, plus the same optional top-level
`targetEntity` + `targetKey` (together).

| `mode` | Needs |
| --- | --- |
| `server_path` | `sourcePath` (a folder the SAP server can read), `fileName` (no extension), `fileExtension` (no dot); `override` (default `true`, honored only in this mode) |
| `base64` | `base64Content`, `fileNameWithExtension` |
| `multipart` | `localFilePath` on the MCP host — which usually can't see Claude's sandbox paths (e.g. `/mnt/user-data/uploads`), so use the upload flow for chat files |

`base64` and `multipart` rename on a name clash like the upload (`renamedFrom`).

**Recovery without re-uploading.** When the file already sits in a folder the SAP server reads —
including SAP's own attachment folder, because an earlier attempt stored it there, or a share the
user put it on — attach it with `mode="server_path"`, its folder as `sourcePath`, and the target.
If that folder is SAP's attachment folder itself, the new record references the same physical file
as any record already linked to it.

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
- For financial postings, confirm before posting — see *Draft-first* above for the chat-receipt
  default and when to leave a draft in SAP instead.
