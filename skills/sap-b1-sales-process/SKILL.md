---
name: sap-b1-sales-process
description: "Drives the SAP Business One sales lifecycle via the Service Layer MCP — sales quotations (Quotations), sales orders (Orders), deliveries (DeliveryNotes), and their conversion forward into the next document by copying from the base document. Use whenever the user wants to create a quotation, raise a sales order, ship a delivery, convert a quotation into an order or an order into a delivery/invoice, or check where an order sits in the flow. Also triggers on Danish requests: tilbud, opret tilbud, salgsordre, opret ordre, levering, følgeseddel, konverter tilbud til ordre, lav ordre til levering, salgsproces. Resolves the customer, items, and VAT group live for the connected company database."
---

# SAP B1 — sales process (quotation → order → delivery → invoice)

Create and advance sales documents. Resolve the customer, items, and VAT/tax codes **live** for
the connected DB.

<!-- core-rules: identical in every SAP B1 skill; scripts/check.sh enforces it -->
## Core rules

- **Load the tools before judging what's there.** If the `sap_b1_*` tools are listed by name only,
  load them all with one `ToolSearch` (`query: "sap_b1"`, not a `select:` list of the ones you
  expect to need) — never tell the user a capability is missing before that. Once loaded, a missing tool is real gating: fall back (`sap_b1_sl_query` when
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

## The flow

`Quotations` → `Orders` → `DeliveryNotes` → `Invoices`. Each stage **copies from the previous
document** rather than retyping lines, so SAP carries pricing and keeps the base document's status
(open → closed) in sync. You can start at any stage and skip stages (e.g. order straight to invoice).

| Stage | Entity set | DocObjectCode | Object type |
| --- | --- | --- | --- |
| Quotation | `Quotations` | `oQuotations` | 23 |
| Order | `Orders` | `oOrders` | 17 |
| Delivery | `DeliveryNotes` | `oDeliveryNotes` | 15 |
| Invoice | `Invoices` | `oInvoices` | 13 → see `sap-b1-invoices` |

## Steps

1. **Resolve the customer** (`BusinessPartners` → `CardCode`). If ambiguous, list matches and ask.
2. **Create the first document** (usually a quotation or order) with item lines
   (`ItemCode` + `Quantity`, optional `UnitPrice`) or service lines (`AccountCode` +
   `DocType: "dDocument_Service"`). Resolve every `ItemCode`/`AccountCode` live — batch these
   with the customer lookup in one round trip. Omit `VatGroup` by default (SAP derives it via tax
   determination — see Notes).
3. **Advance by copying from the base.** To make the next document, resolve the base document's
   `DocEntry` (query the entity, filter on `DocNum` — the `DocNum` the user quotes is not the key),
   then on each target line set `BaseType` (the base's object type from the table above),
   `BaseEntry` (its `DocEntry`), and `BaseLine` (its `LineNum`, 0-based). SAP then carries
   pricing and links. Copy only the lines/quantities being fulfilled — partial deliveries and
   partial invoicing are normal and leave the base document partially open.
4. **Show a receipt and confirm** before posting each document with `sap_b1_sl_write`
   (`POST Orders`, `POST DeliveryNotes`, …). If a customer PO or email is in the conversation,
   settle attachment intent in this same turn. Use `sap_b1_create_draft` first only when the user
   wants a reviewable SAP draft, and finalize it per the draft rule in Core rules.

## Payload shapes

**New sales order (item lines):**
```
sap_b1_sl_write
  method: "POST"
  path: "Orders"
  body: {
    "CardCode": "<resolved>",
    "DocDate": "<today, YYYY-MM-DD>",
    "DocDueDate": "<delivery date, YYYY-MM-DD>",
    "DocumentLines": [
      { "ItemCode": "<resolved>", "Quantity": 5 }
    ]
  }
```

**Delivery copied from that order:**
```
sap_b1_sl_write
  method: "POST"
  path: "DeliveryNotes"
  body: {
    "CardCode": "<same as order>",
    "DocumentLines": [
      { "BaseType": 17, "BaseEntry": <Order DocEntry>, "BaseLine": 0, "Quantity": 5 }
    ]
  }
```

To make the final invoice, hand off to `sap-b1-invoices` and copy from the delivery
(`BaseType: 15`) or the order (`BaseType: 17`).

<!-- attach-files: identical in every SAP B1 skill that attaches files; scripts/check.sh enforces it -->
## Attaching a file

When the user said to attach, do it right after the record exists:

1. `sap_b1_prepare_upload` (no args) → `{ token, uploadUrl }`.
2. Upload the file as an HTTP `POST` to `uploadUrl` with `multipart/form-data`: header
   `x-upload-token: <token>`, form fields `file` (the file, with its MIME type), `entity` (the
   entity set, e.g. `PurchaseInvoices`), and `key` (the record's key).
3. If the response has `"attached": false`, link it yourself:
   `sap_b1_sl_write method="PATCH" path="<EntitySet>(<key>)" body={ "AttachmentEntry": <n> }`.

For a file the SAP/MCP host can already read, or Base64 in memory, `sap_b1_attach_file` does it in
one call (`mode` `server_path` / `multipart` / `base64`, optional `target`). Report the record and
the attachment together ("invoice posted, `bilag.pdf` attached").
<!-- /attach-files -->

## Notes

- Reading status only? Use `sap-b1-lookups` — no writes.
- **Orders — `DocDueDate` (delivery date) is required.** SAP rejects an order without it
  ("Enter due date"), and does not derive it from payment terms. Use the user's date; if they gave
  none, ask, or propose one and call it out on the receipt. SAP accepts a date before `DocDate`
  without complaint, so check that yourself. Set it on drafts too — a draft saves fine without it,
  but the real order it becomes still needs it.
- **Quotations — omit `DocDueDate`** (valid-until) unless the user names one; SAP fills in a
  default valid-until date.
- Dates are `YYYY-MM-DD`. Resolve items and accounts live — never reuse codes from another
  company. Set `VatGroup`, resolved live, only when the user asks for a specific tax treatment,
  the post fails with a missing/invalid tax code, or this DB has no default for the line.
- If write tools aren't exposed, you can still read these documents with `sap_b1_get_document` /
  `sap_b1_sl_query`; tell the user creating needs a write-capable capability set.
