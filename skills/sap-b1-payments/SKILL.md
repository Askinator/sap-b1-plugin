---
name: sap-b1-payments
description: "Apply payments in SAP Business One via the Service Layer MCP — incoming payments from customers (IncomingPayments) and outgoing payments to vendors (VendorPayments), matched against open invoices and settled to a bank, cash, or card account. Use whenever the user wants to register a payment, mark an invoice as paid, record that a customer paid, pay a vendor bill, or reconcile a payment against open invoices. Also triggers on Danish requests: registrer betaling, indbetaling, kunde har betalt, betal leverandør, udbetaling, match betaling mod faktura, afstem betaling, marker faktura som betalt. Resolves the business partner, the open invoices, and the bank/cash/card G/L account live for the connected company database."
---

# SAP B1 — payments

Register **incoming payments** from customers (`IncomingPayments`) and **outgoing payments** to
vendors (`VendorPayments`), matched to open invoices. Follow the discovery-first rule: resolve the
business partner, the open invoices, and the settlement account **live** (see `sap-b1-overview`).

When the visualize tools are available (see `sap-b1-overview` → Rendering output), render the draft
receipt shown for pre-posting confirmation as a data-record card.

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
   `DocEntry` (the invoice), `InvoiceType` (its object type — `13` AR invoice, `18` AP invoice —
   see the object-type map in `sap-b1-overview/reference.md`), and `SumApplied`.
4. **Confirm the settlement account** with `describe` only if unsure of the field name for this
   DB and you haven't already described the entity this session.
5. **Show a receipt and confirm**, then post with `sap_b1_sl_write`
   (`POST IncomingPayments` / `POST VendorPayments`). Payments post immediately — there is no
   separate "approve" step — so confirm the amounts and account before sending.

## Payload shape (incoming payment, bank transfer)

```
sap_b1_sl_write
  method: "POST"
  path: "IncomingPayments"
  body: {
    "CardCode": "<resolved>",
    "DocDate": "2026-07-08",
    "TransferAccount": "<resolved bank G/L>",
    "TransferSum": 1250.00,
    "TransferDate": "2026-07-08",
    "PaymentInvoices": [
      { "DocEntry": <invoice DocEntry>, "InvoiceType": 13, "SumApplied": 1250.00 }
    ]
  }
```

For an outgoing/vendor payment, use `path: "VendorPayments"` and `InvoiceType: 18`.

## Notes

- **`SumApplied` per line must total the settlement sum.** A payment can settle several invoices
  (partial payments are fine); make the applied amounts add up to `TransferSum`/`CashSum`.
- A payment with no `PaymentInvoices` posts as an unallocated payment on account — only do that if
  the user asks for it; otherwise always match to specific invoices.
- Dates are `YYYY-MM-DD`. Resolve every G/L account live; never reuse a bank account number from
  another company.
- If write tools aren't exposed, you can still read payments and open invoices with
  `sap_b1_sl_query`; tell the user posting needs a write-capable capability set.
