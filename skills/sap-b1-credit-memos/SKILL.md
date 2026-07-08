---
name: sap-b1-credit-memos
description: "Create credit memos in SAP Business One via the Service Layer MCP — AR credit memos (CreditNotes) to a customer and AP credit memos (PurchaseCreditNotes) from a vendor, either standalone or copied from the original invoice — and reverse or correct a posted document the right way. Use whenever the user wants to credit a customer, issue a refund or return, cancel or reverse a posted invoice, book a vendor credit, or undo a wrong posting. Also triggers on Danish requests: kreditnota, kreditér kunde, tilbageførsel, modpostering, annuller faktura, returnering, varer retur, leverandørkreditnota. Resolves the business partner, items, G/L accounts, and VAT group live for the connected company database."
---

# SAP B1 — credit memos and reversals

Issue **AR credit memos** (`CreditNotes`) to customers and **AP credit memos**
(`PurchaseCreditNotes`) from vendors, and correct posted documents. Follow the discovery-first
rule: resolve the partner, items, G/L accounts, and VAT/tax codes **live** (see `sap-b1-overview`).

## In SAP B1 you reverse by crediting, not deleting

A **posted** invoice or journal entry is **not** deleted — it's offset by a reversing document. To
undo a posted AR invoice, raise a `CreditNotes` (ideally copied from that invoice so amounts, tax,
and stock reverse exactly); for a posted AP invoice, a `PurchaseCreditNotes`; for a posted journal
entry, a reversing entry (see `sap-b1-journal-entries`). Only an unposted **draft** can be deleted
outright. Never attempt a raw `DELETE` on a posted document.

## Decide the shape

1. **AR or AP?** Crediting a customer → `CreditNotes` (`oCreditNotes`). Vendor credit →
   `PurchaseCreditNotes` (`oPurchaseCreditNotes`).
2. **From an invoice, or standalone?**
   - **Reverse/return against a specific invoice (preferred)** → copy from the base invoice so
     quantities, pricing, tax, and stock reverse cleanly.
   - **Standalone** → build item lines (`ItemCode`) or service lines (`AccountCode` +
     `DocType: "dDocument_Service"`), same shapes as an invoice.

## Steps

1. **Resolve the partner** (`BusinessPartners` → `CardCode`).
2. **Locate the source invoice** if crediting one: query `Invoices`/`PurchaseInvoices` for its
   `DocEntry` (the key, not `DocNum`) and the lines to reverse.
3. **Build lines.** For a copy, reference the invoice on each line with `BaseType`
   (`13` AR invoice / `18` AP invoice), `BaseEntry` (invoice `DocEntry`), `BaseLine` (`LineNum`) —
   see the copy-from-base recipe in `sap-b1-overview/reference.md`. Credit only the lines/quantities
   being returned; partial credits are normal.
4. **Show a receipt and confirm**, then post with `sap_b1_sl_write` (`POST CreditNotes` /
   `POST PurchaseCreditNotes`). Use `sap_b1_create_draft` first only if the user wants a reviewable
   SAP draft — then finalize per the draft-first rule in `sap-b1-overview/reference.md`.

## Payload shape (AR credit memo, copied from an invoice)

```
sap_b1_sl_write
  method: "POST"
  path: "CreditNotes"
  body: {
    "CardCode": "<resolved>",
    "DocDate": "2026-07-08",
    "DocumentLines": [
      { "BaseType": 13, "BaseEntry": <invoice DocEntry>, "BaseLine": 0, "Quantity": 1 }
    ]
  }
```

Standalone item line: `{ "ItemCode": "<resolved>", "Quantity": 1, "VatGroup": "<resolved>" }`.
Standalone service line: header `DocType: "dDocument_Service"`, line
`{ "AccountCode": "<resolved G/L>", "LineTotal": 500.00, "VatGroup": "<resolved>" }`.

## Notes

- Copying from the invoice is safest — it reverses the exact tax and inventory postings. Prefer it
  over hand-built lines whenever a source invoice exists.
- Dates are `YYYY-MM-DD`. `VatGroup` is the standard line VAT field (some localizations use
  `TaxCode`); confirm via `describe` and resolve the code live.
- If the user actually wants a *payment refund* rather than a credit, see `sap-b1-payments`.
- If write tools aren't exposed, you can still read credit memos with `sap_b1_sl_query`; tell the
  user creating needs a write-capable capability set.
