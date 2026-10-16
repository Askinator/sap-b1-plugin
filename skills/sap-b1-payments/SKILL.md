---
name: sap-b1-payments
description: "Applies payments in SAP Business One via the Service Layer MCP — incoming payments from customers (IncomingPayments) and outgoing payments to vendors (VendorPayments), matched against open invoices and settled to a bank, cash, or card account — full, partial, or on account. Use whenever the user wants to register a payment, mark an invoice as paid, record that a customer paid, record a partial payment or a payment on account, pay a vendor bill, or reconcile a payment against open invoices. Also triggers on Danish requests: betaling, registrer betaling, indbetaling, kunde har betalt, betal leverandør, udbetaling, bankoverførsel, delbetaling, betaling på konto, a conto, match betaling mod faktura, afstem betaling, marker faktura som betalt. Resolves the business partner, the open invoices, and the bank/cash/card G/L account live for the connected company database."
---

# SAP B1 — payments

Register **incoming payments** from customers (`IncomingPayments`) and **outgoing payments** to
vendors (`VendorPayments`), matched to open invoices. Resolve the business partner, the open
invoices, and the settlement account **live** for the connected DB.

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

## Decide the shape

1. **Who is paying whom?** Customer pays us → `IncomingPayments` (`oIncomingPayments`). We pay a
   vendor → `VendorPayments` (`oVendorPayments`).
2. **How is it settled?** Choose one payment means and set the matching header fields:
   - **Bank transfer** → `TransferAccount` (a G/L/bank account), `TransferSum`, `TransferDate`,
     and `TransferReference` when the user gives a bank reference.
   - **Cash** → `CashAccount`, `CashSum`.
   - **Card** → one `PaymentCreditCards` line: `CreditCard` (a `CreditCardCode` from
     `CreditCards`), `CreditAcct` (that card's `GLAccount`), `PaymentMethodCode` (from
     `CreditPaymentMethods` where `AssignedtoCreditCard` is that card), `CreditSum`,
     `CardValidUntil` (ask the user for the expiry month), `VoucherNum` (the terminal or voucher
     reference), and `CreditCardNumber` — the **last four digits only**. Never ask for or send a
     full card number or security code; if the user pastes one, keep only its last four digits and
     don't repeat the rest. If `CreditCards` is empty, card payments aren't set up in this DB — say
     so and stop. If an earlier payment in this DB has `PaymentCreditCards`, copy its shape.
   - **Check** → the `PaymentChecks` collection: read an existing check payment's lines for the
     shape, or `describe` `PaymentCheck`; never guess bank or account codes.

   Resolve the bank/cash G/L account live from `ChartOfAccounts`. When several bank accounts fit,
   propose the `TransferAccount` this partner's recent payments used, and ask if unsure.
3. **How much goes where?** An invoice's open amount is `DocTotal − PaidToDate`
   (`DocTotalFc − PaidToDateFC` in its own currency). The settlement sum is what the user says was
   paid; the default is the full open amount of the invoice(s) they named.
   - **Full payment** → `SumApplied` = the open amount.
   - **Partial payment** → the applied amounts add up to the amount paid, each at most its
     invoice's open amount; the receipt shows what stays open on each invoice afterwards. With one
     invoice, its `SumApplied` is the amount paid. With several, propose settling the oldest due
     date first and say so on the receipt.
   - **Overpayment** → SAP posts the settlement sum minus the applied total on account (it shows as
     `NoDocSum` on the payment). Never let that happen silently: the receipt shows the remainder as
     "on account" and the user either confirms it or names more open invoices to apply it to.
   - **Payment on account** (the user says so, or names no invoice and doesn't want one matched)
     → omit `PaymentInvoices`; the whole sum posts unallocated on the partner's account.

## Steps

1. **Resolve the partner** (`BusinessPartners` → `CardCode`). If ambiguous, list matches and ask.
2. **Find the open invoices to settle.** Query `Invoices` (or `PurchaseInvoices`) for the partner
   with `DocumentStatus eq 'bost_Open'`; select `DocEntry` (the key — not `DocNum`), `DocNum`,
   `DocDueDate`, `DocCurrency`, `DocTotal`, `PaidToDate`, and — for a foreign-currency invoice —
   `DocTotalFc`, `PaidToDateFC`. If the user named a `DocNum`, resolve it to `DocEntry` first.
3. **Match payment to invoices.** Each settled invoice goes in the `PaymentInvoices` collection:
   `DocEntry` (the invoice), `InvoiceType`, and `SumApplied` (local currency — in a
   foreign-currency payment set `AppliedFC` instead; see below). `InvoiceType` is an enum **name**,
   not the object-type number: `"it_Invoice"` for an AR invoice, `"it_PurchaseInvoice"` for an AP
   invoice. For any other kind (credit memo, journal entry), read the `PaymentInvoices` of an
   existing payment that settled one to get the exact name rather than guessing.
4. **Confirm the settlement account** with `describe` only if unsure of the field name for this
   DB and you haven't already described the entity this session.
5. **Show a receipt and confirm**, then post with `sap_b1_sl_write`
   (`POST IncomingPayments` / `POST VendorPayments`). The receipt lists each invoice with its open
   amount, the amount applied, and what stays open; the settlement account; and any remainder
   on account. Payments post immediately — there is no separate "approve" step — so confirm the
   amounts and account before sending. If a bank advice or receipt is in the conversation, settle
   attachment intent in this same turn.
6. **Report what is still open.** After posting, re-read the settled invoices' `PaidToDate` and
   `DocumentStatus` and tell the user which are now closed and what is still owed.

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

## Foreign-currency payments

When the partner pays in a currency other than the local one (or the invoice is in one):

- Set `DocCurrency` to the payment currency and leave `DocRate` to SAP — it uses its rate for
  `DocDate` (`ORTT`). If no rate exists for that date, stop and tell the user to enter it in SAP;
  don't invent one.
- Per invoice, set `AppliedFC` to the amount applied in the invoice's currency (the open amount
  is `DocTotalFc − PaidToDateFC`) and leave `SumApplied` to SAP — it converts at the invoice's
  rate and books any exchange-rate difference itself.
- Give the settlement sum (`TransferSum` / `CashSum`) in the payment currency, and compare it with
  the applied total in that currency too — an overpayment remainder goes on account as above.
  Don't learn amounts from earlier FX payments: read back, the Service Layer shows `TransferSum`
  and `SumApplied` in **local** currency. In SQL, `ORCT`/`OVPM.TrsfrSumFC` holds the foreign amount
  and `TrsfrSum` the local one.
- The receipt shows the foreign amounts, the rate, and the local equivalent (see core rules).
  Always check an FX payment after posting: read back `TrsfrSumFC` or `CashSumFC` via
  `sap_b1_sql_query` (or each line's `AppliedFC`) and compare with the receipt. If it doesn't
  match, tell the user at once — the payment can be cancelled with
  `sap_b1_sl_write method="POST" path="IncomingPayments(<DocEntry>)/Cancel"` (or
  `VendorPayments(...)/Cancel`), but only if they confirm.

<!-- attach-files: identical in every SAP B1 skill that attaches files; scripts/check.sh enforces it -->
## Attaching a file

When the user said to attach, do it right after the record exists:

1. `sap_b1_prepare_upload` with `targetEntity` (the entity set, e.g. `PurchaseInvoices`) and
   `targetKey` (the record's key — a number for `DocEntry`-style keys, a string for `CardCode`)
   → `{ token, uploadUrl }`. The target is bound into the token.
2. Upload the file as an HTTP `POST` to `uploadUrl` with `multipart/form-data`: header
   `x-upload-token: <token>` and **only** the form field `file` (the file, with its MIME type).
   Any other field (`entity`, `key`, `fileName`, …) is rejected with 400. The token is single-use
   and spent by any attempt, so every retry starts again at step 1.
3. A 200 returns `attachmentEntry`; the file joins the record's existing attachment entry, if it
   has one. If `renamedFrom` is present, the name was taken in SAP's attachment folder and the
   file was stored as `uploadedFile.fileName` — tell the user the stored name.

Errors answer `{ error, detail }`: 400 bad input, 401 token missing/used/expired, 409 name clash
(rename the file, new token), 422 SAP rejected it, 503 SAP unreachable. Show `detail` to the user;
never report a failed upload as attached. If a response has `attachmentEntry` with
`"attached": false`, don't re-upload — link it:
`sap_b1_sl_write method="PATCH" path="<EntitySet>(<key>)" body={ "AttachmentEntry": <n> }`.

`sap_b1_attach_file` (same `targetEntity`/`targetKey`) takes a file without the upload step:
`mode="base64"` with `base64Content` + `fileNameWithExtension`, or `mode="server_path"` with
`sourcePath` (a folder the SAP server reads), `fileName` (no extension), `fileExtension` (no dot).
Its `multipart` mode reads a path on the MCP host, which can't see chat uploads. If the file already
sits in such a folder — e.g. an earlier attempt stored it in SAP's attachment folder — attach it
with `server_path` instead of uploading again (from that folder, the records share one physical
file). Report the record and the attachment together ("invoice posted, `bilag.pdf` attached").
<!-- /attach-files -->

## Notes

- **Applied amounts never exceed the settlement sum**, and no line exceeds that invoice's open
  amount (compare in the same currency). Any difference between the settlement sum and the applied
  total is the on-account remainder (see "How much goes where?").
- Dates are `YYYY-MM-DD`. Resolve every G/L account live; never reuse a bank account number from
  another company.
- If write tools aren't exposed, you can still read payments and open invoices with
  `sap_b1_sl_query`; tell the user posting needs a write-capable capability set.
