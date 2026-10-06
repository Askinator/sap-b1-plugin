---
name: sap-b1-invoices
description: "Creates AR invoices (Invoices) and AP invoices (PurchaseInvoices) in SAP Business One via the Service Layer MCP — both item-type invoices bound to ItemCodes and service-type invoices posted to a G/L account. Use whenever the user wants to create, post, or draft an invoice, faktura, salgsfaktura, indkøbsfaktura, kreditorfaktura, or debitorfaktura, or bill a customer or record a bill from a vendor. Resolves the customer/vendor, item, G/L account, and VAT group live for the connected company database."
---

# SAP B1 — invoices

Create AR invoices (`Invoices`) and AP invoices (`PurchaseInvoices`). **Read `sap-b1-overview`
before your first tool call** — it carries the output-rendering policy and the tool-availability
fallbacks that apply here.

Follow the discovery-first rule: resolve the business partner, items, G/L accounts, and VAT/tax
codes **live** for the connected DB. Never reuse codes from another company.

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
   to SAP's tax determination unless a specific treatment is needed — see the VAT note in
   `sap-b1-overview/reference.md`.
3. **Confirm fields for this DB** — only if unsure of a field name and you haven't already
   described this entity in this session: `sap_b1_discover action="describe" name="Invoices"` (or
   `PurchaseInvoices`).
4. **Show a receipt and confirm.** Summarize the partner, lines, totals, and tax before posting.
   If a file is in the conversation, settle attachment intent in this same turn — see the
   attachment section in `sap-b1-overview/reference.md`. If the user wants a reviewable SAP draft,
   create one with `sap_b1_create_draft` and capture its `DraftEntry`.
5. **Finalize after confirmation.** Post the real invoice with `sap_b1_sl_write`
   (`POST Invoices` / `POST PurchaseInvoices`). If you created a draft, either have the user
   approve it in SAP **or** delete it after posting — see the draft-first finalize rule in
   `sap-b1-overview/reference.md` so you don't leave an orphan draft.

## Payload shapes

**Item AR invoice (after confirmation):**
```
sap_b1_sl_write
  method: "POST"
  path: "Invoices"
  body: {
    "CardCode": "<resolved>",
    "DocDate": "<today, YYYY-MM-DD>",
    "DocDueDate": "<per payment terms, YYYY-MM-DD>",
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

## Notes

- Dates are `YYYY-MM-DD`. Use the user's date or today.
- Omit `VatGroup` — SAP derives it. The VAT note in `sap-b1-overview/reference.md` covers the
  exceptions and the `TaxCode` localization.
- **AP invoices:** set `NumAtCard` to the vendor's own invoice number when the user gives it —
  it's how AP invoices are matched and found later.
- To bill from an existing sales order or delivery, copy from the base document instead of
  retyping lines (`BaseType`/`BaseEntry`/`BaseLine`) — see `sap-b1-sales-process` and the
  copy-from-base recipe in `sap-b1-overview/reference.md`.
- Only pass fields you can justify. Let SAP default the rest.
- If `sap_b1_create_draft` or `sap_b1_sl_write` is not exposed on this deployment, you can still
  read invoices with `sap_b1_get_document entity="Invoices"`; tell the user that creating requires
  a write-capable capability set.
