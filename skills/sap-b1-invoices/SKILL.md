---
name: sap-b1-invoices
description: "Create AR invoices (Invoices) and AP invoices (PurchaseInvoices) in SAP Business One via the Service Layer MCP — both item-type invoices bound to ItemCodes and service-type invoices posted to a G/L account. Use whenever the user wants to create, post, or draft an invoice, faktura, salgsfaktura, indkøbsfaktura, kreditorfaktura, or debitorfaktura, or bill a customer or record a bill from a vendor. Resolves the customer/vendor, item, G/L account, and VAT group live for the connected company database."
---

# SAP B1 — invoices

Create AR invoices (`Invoices`) and AP invoices (`PurchaseInvoices`). Follow the discovery-first
rule: resolve the business partner, items, G/L accounts, and VAT/tax codes **live** for the
connected DB (see `sap-b1-overview`). Never reuse codes from another company.

When the visualize tools are available (see `sap-b1-overview` → Rendering output), render the draft
receipt shown for pre-posting confirmation as a data-record card.

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
   lines, resolve each `AccountCode` from `ChartOfAccounts`. Resolve the tax/VAT code from the tax
   entity — do not assume a rate.
3. **Confirm fields for this DB.** `sap_b1_discover action="describe" name="Invoices"` (or
   `PurchaseInvoices`) if unsure of a field name.
4. **Show a receipt and confirm.** Summarize the partner, lines, totals, and tax in chat before
   posting. If the user wants a reviewable SAP draft, create one with `sap_b1_create_draft` and
   capture its `DraftEntry`.
5. **Finalize after confirmation.** Post the real invoice with `sap_b1_sl_write`
   (`POST Invoices` / `POST PurchaseInvoices`). If you created a draft, either have the user
   approve it in SAP **or** delete it after posting — see the draft-first finalize rule in
   `sap-b1-overview/reference.md` so you don't leave an orphan draft.

## Payload shapes

**Item AR invoice (draft):**
```
sap_b1_create_draft
  DocObjectCode: "oInvoices"
  CardCode: "<resolved>"
  DocDate: "2026-07-01"
  DocDueDate: "2026-07-15"
  DocumentLines: [
    { "ItemCode": "<resolved>", "Quantity": 2, "VatGroup": "<resolved>" }
  ]
```

**Service AR invoice (draft):**
```
sap_b1_create_draft
  DocObjectCode: "oInvoices"
  CardCode: "<resolved>"
  DocType: "dDocument_Service"
  DocDate: "2026-07-01"
  DocumentLines: [
    { "AccountCode": "<resolved G/L>", "LineTotal": 1000.00, "VatGroup": "<resolved>" }
  ]
```

**Post the real document (after confirmation):** same body, but
`sap_b1_sl_write method="POST" path="Invoices"` (omit `DocObjectCode`, which is a Drafts-only
field). For AP, use `path="PurchaseInvoices"`.

## Notes

- Dates are `YYYY-MM-DD`. Use the user's date or today.
- `VatGroup` is the standard Service Layer line VAT field; some localizations use `TaxCode`.
  Confirm the field name via `describe` and resolve the code value live.
- **AP invoices:** set `NumAtCard` to the vendor's own invoice number when the user gives it —
  it's how AP invoices are matched and found later.
- To bill from an existing sales order or delivery, copy from the base document instead of
  retyping lines (`BaseType`/`BaseEntry`/`BaseLine`) — see `sap-b1-sales-process` and the
  copy-from-base recipe in `sap-b1-overview/reference.md`.
- Only pass fields you can justify. Let SAP default the rest.
- If `sap_b1_create_draft` or `sap_b1_sl_write` is not exposed on this deployment, you can still
  read invoices with `sap_b1_get_document entity="Invoices"`; tell the user that creating requires
  a write-capable capability set.
