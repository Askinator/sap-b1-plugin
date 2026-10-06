---
name: sap-b1-payments
description: "Applies payments in SAP Business One via the Service Layer MCP — incoming payments from customers (IncomingPayments) and outgoing payments to vendors (VendorPayments), matched against open invoices and settled to a bank, cash, or card account. Use whenever the user wants to register a payment, mark an invoice as paid, record that a customer paid, pay a vendor bill, or reconcile a payment against open invoices. Also triggers on Danish requests: registrer betaling, indbetaling, kunde har betalt, betal leverandør, udbetaling, match betaling mod faktura, afstem betaling, marker faktura som betalt. Resolves the business partner, the open invoices, and the bank/cash/card G/L account live for the connected company database."
---

# SAP B1 — payments

Register **incoming payments** from customers (`IncomingPayments`) and **outgoing payments** to
vendors (`VendorPayments`), matched to open invoices. Resolve the business partner, the open
invoices, and the settlement account **live** for the connected DB.

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

1. **Who is paying whom?** Customer pays us → `IncomingPayments` (`oIncomingPayments`). We pay a
   vendor → `VendorPayments` (`oVendorPayments`).
2. **How is it settled?** Choose one payment means and set the matching header fields:
   - **Bank transfer** → `TransferAccount` (a G/L/bank account), `TransferSum`, `TransferDate`.
   - **Cash** → `CashAccount`, `CashSum`.
   - **Check / card** → the `PaymentChecks` / `PaymentCreditCards` collection.
   Resolve the bank/cash G/L account live from `ChartOfAccounts`.

## Steps

1. **Resolve the partner** (`BusinessPartners` → `CardCode`). If ambiguous, list matches and ask.
2. **Find the open invoices to settle.** Query `Invoices` (or `PurchaseInvoices`) for the partner
   with `DocumentStatus eq 'bost_Open'`; get each invoice's `DocEntry` (the key — not `DocNum`)
   and the outstanding amount. If the user named a `DocNum`, resolve it to `DocEntry` first.
3. **Match payment to invoices.** Each settled invoice goes in the `PaymentInvoices` collection:
   `DocEntry` (the invoice), `InvoiceType`, and `SumApplied`. `InvoiceType` is an enum **name**,
   not the object-type number: `"it_Invoice"` for an AR invoice, `"it_PurchaseInvoice"` for an AP
   invoice. For any other kind (credit memo, journal entry), read the `PaymentInvoices` of an
   existing payment that settled one to get the exact name rather than guessing.
4. **Confirm the settlement account** with `describe` only if unsure of the field name for this
   DB and you haven't already described the entity this session.
5. **Show a receipt and confirm**, then post with `sap_b1_sl_write`
   (`POST IncomingPayments` / `POST VendorPayments`). Payments post immediately — there is no
   separate "approve" step — so confirm the amounts and account before sending. If a bank advice
   or receipt is in the conversation, settle attachment intent in this same turn.

## Payload shape (incoming payment, bank transfer)

```
sap_b1_sl_write
  method: "POST"
  path: "IncomingPayments"
  body: {
    "CardCode": "<resolved>",
    "DocDate": "<today, YYYY-MM-DD>",
    "TransferAccount": "<resolved bank G/L>",
    "TransferSum": 1250.00,
    "TransferDate": "<today, YYYY-MM-DD>",
    "PaymentInvoices": [
      { "DocEntry": <invoice DocEntry>, "InvoiceType": "it_Invoice", "SumApplied": 1250.00 }
    ]
  }
```

For an outgoing/vendor payment, use `path: "VendorPayments"` and `"InvoiceType": "it_PurchaseInvoice"`.

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

- **`SumApplied` per line must total the settlement sum.** A payment can settle several invoices
  (partial payments are fine); make the applied amounts add up to `TransferSum`/`CashSum`.
- A payment with no `PaymentInvoices` posts as an unallocated payment on account — only do that if
  the user asks for it; otherwise always match to specific invoices.
- Dates are `YYYY-MM-DD`. Resolve every G/L account live; never reuse a bank account number from
  another company.
- If write tools aren't exposed, you can still read payments and open invoices with
  `sap_b1_sl_query`; tell the user posting needs a write-capable capability set.
