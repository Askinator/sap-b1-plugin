---
name: sap-b1-invoices
description: "Creates AR invoices (Invoices) and AP invoices (PurchaseInvoices) in SAP Business One via the Service Layer MCP — both item-type invoices bound to ItemCodes and service-type invoices posted to a G/L account. Use whenever the user wants to create, post, or draft an invoice, faktura, salgsfaktura, indkøbsfaktura, kreditorfaktura, or debitorfaktura, or bill a customer or record a bill from a vendor. Resolves the customer/vendor, item, G/L account, and VAT group live for the connected company database."
---

# SAP B1 — invoices

Create AR invoices (`Invoices`) and AP invoices (`PurchaseInvoices`). Resolve the business
partner, items, G/L accounts, and VAT/tax codes **live** for the connected DB.

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
  user says yes. Other writes follow this skill's own steps. Use
  `sap_b1_create_draft` only when the user wants a draft left in SAP; then either they approve it
  in SAP, or you post the real document and remove the draft with
  `sap_b1_sl_write method="DELETE" path="Drafts(<DraftEntry>)"` — never leave a draft beside the
  posted document. A draft skips mandatory-field checks, so give it every field the real document
  needs.
- **Settle attachment intent up front.** If a file (PDF, receipt, email, image) is in the
  conversation and you will create or find a record, ask with `AskUserQuestion` whether to attach
  it — in the same turn as the receipt, not after the record exists. If the user already said,
  don't ask again.
- **Render chat output as widgets** — in scheduled and test runs too. Call
  `mcp__visualize__read_me` once, then `mcp__visualize__show_widget`: a confirmation receipt or a
  single balance/status as a data-record card, a set of options as a card grid. Multi-row lists
  stay markdown tables. Only if `show_widget` is absent, fall back to prose without mentioning it.
- **Every amount carries its currency code.** Balances are in the company's local currency —
  resolve its code live (`OADM.MainCurncy` via `sap_b1_sql_query`); without SQL, say the amount
  is in local currency rather than guess a code. On a foreign-currency document, show the lines in
  the document currency, the local total with its code, and the exchange rate — as SAP returned
  them, not computed.
<!-- /core-rules -->

## Decide the shape

1. **AR or AP?** Customer bill → `Invoices` (`oInvoices`). Vendor bill → `PurchaseInvoices`
   (`oPurchaseInvoices`).
2. **Item or service line?**
   - Item invoice → lines carry `ItemCode` (+ `Quantity`, optional `UnitPrice`).
   - Service invoice → header `DocType: "dDocument_Service"`, lines carry `AccountCode` (a G/L
     account) and `LineTotal`, no `ItemCode`.

## Steps

1. **Resolve the partner.** Query `BusinessPartners` for the `CardCode` (filter on `CardName`).
   If ambiguous, list matches and ask.
2. **Resolve line codes live.** For item lines, confirm each `ItemCode` from `Items`. For service
   lines, resolve each `AccountCode` from `ChartOfAccounts`. Steps 1–2 are independent reads —
   batch them in one round trip (parallel calls, or one SQL query if enabled). Leave the VAT group
   to SAP's tax determination (see Notes).
3. **Confirm fields for this DB** — only if unsure of a field name and you haven't already
   described this entity in this session: `sap_b1_discover action="describe" name="Invoices"` (or
   `PurchaseInvoices`).
4. **Show a receipt and confirm.** Summarize the partner, lines, totals, and tax before posting.
   If a file is in the conversation, settle attachment intent in this same turn. If the user wants
   a reviewable SAP draft, create one with `sap_b1_create_draft` and capture its `DraftEntry`.
5. **Finalize after confirmation.** Post the real invoice with `sap_b1_sl_write`
   (`POST Invoices` / `POST PurchaseInvoices`). If you created a draft, either have the user
   approve it in SAP **or** delete it after posting, so no orphan draft remains. Attach the file
   if the user said to (see *Attaching a file*).

## Payload shapes

**Item AR invoice (after confirmation):**
```
sap_b1_sl_write
  method: "POST"
  path: "Invoices"
  body: {
    "CardCode": "<resolved>",
    "DocDate": "<today, YYYY-MM-DD>",
    "DocumentLines": [
      { "ItemCode": "<resolved>", "Quantity": 2 }
    ]
  }
```

**Service AR invoice (after confirmation):**
```
sap_b1_sl_write
  method: "POST"
  path: "Invoices"
  body: {
    "CardCode": "<resolved>",
    "DocType": "dDocument_Service",
    "DocDate": "<today, YYYY-MM-DD>",
    "DocumentLines": [
      { "AccountCode": "<resolved G/L>", "LineTotal": 1000.00, "VatGroup": "<resolved, if this DB has no service-line default>" }
    ]
  }
```

For AP, use `path: "PurchaseInvoices"`. **SAP draft instead (only if the user wants one):** pass the
same fields to `sap_b1_create_draft` plus `DocObjectCode: "oInvoices"` (or `"oPurchaseInvoices"`).

**Billing from an order or delivery** — copy from the base document instead of retyping lines. On
each line set `BaseType` (`17` sales order, `15` delivery; `22` purchase order, `20` goods receipt
PO for AP), `BaseEntry` (the base document's `DocEntry` — resolve it from the `DocNum` the user
quotes), and `BaseLine` (its `LineNum`, 0-based):
```
{ "BaseType": 15, "BaseEntry": <Delivery DocEntry>, "BaseLine": 0 }
```
Copy only the lines/quantities being billed; partial invoicing is normal.

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

- Dates are `YYYY-MM-DD`. Use the user's date or today.
- **Omit `DocDueDate`** unless the user names a due date. SAP derives it from the partner's payment
  terms (AR and AP, standalone or copied from a base document — a base order's delivery date does
  not carry over). A date you pass silently replaces the terms-derived one, installments included.
- **Omit `VatGroup` by default** — SAP's tax determination derives it from the item master and the
  partner. Set it, resolved live, only when the user asks for a specific tax treatment, the post
  fails with a missing/invalid tax code, or this DB has no default for the line (more common on
  service lines). Some localizations use `TaxCode` instead of `VatGroup`.
- **Reading an invoice:** check the header `DocType` first. On a service document every line has
  `ItemCode: null` and `Quantity: 0` by design — the amount is in `LineTotal`, the G/L in
  `AccountCode`.
- **AP invoices:** set `NumAtCard` to the vendor's own invoice number when the user gives it —
  it's how AP invoices are matched and found later.
- Only pass fields you can justify. Let SAP default the rest.
- If `sap_b1_create_draft` or `sap_b1_sl_write` is not exposed on this deployment, you can still
  read invoices with `sap_b1_get_document entity="Invoices"`; tell the user that creating requires
  a write-capable capability set.
