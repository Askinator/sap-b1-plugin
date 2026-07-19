---
name: sap-b1-sales-process
description: "Drive the SAP Business One sales lifecycle via the Service Layer MCP — sales quotations (Quotations), sales orders (Orders), deliveries (DeliveryNotes), and their conversion forward into the next document by copying from the base document. Use whenever the user wants to create a quotation, raise a sales order, ship a delivery, convert a quotation into an order or an order into a delivery/invoice, or check where an order sits in the flow. Also triggers on Danish requests: tilbud, opret tilbud, salgsordre, opret ordre, levering, følgeseddel, konverter tilbud til ordre, lav ordre til levering, salgsproces. Resolves the customer, items, and VAT group live for the connected company database."
---

# SAP B1 — sales process (quotation → order → delivery → invoice)

Create and advance sales documents. Follow the discovery-first rule: resolve the customer, items,
and VAT/tax codes **live** for the connected DB (see `sap-b1-overview`).

Per `sap-b1-overview` → Rendering output, render the document-chain status
(quote → order → delivery → invoice) as a data-record card — every time, not conditionally.

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
   determination) — see the VAT note in `sap-b1-overview/reference.md`.
3. **Advance by copying from the base.** To make the next document, resolve the base document's
   `DocEntry` (query the entity, filter on `DocNum` — the `DocNum` the user quotes is not the key),
   then set `BaseType`/`BaseEntry`/`BaseLine` on each target line. See the copy-from-base recipe in
   `sap-b1-overview/reference.md`. Copy only the lines/quantities being fulfilled — partial
   deliveries and partial invoicing are normal and leave the base document partially open.
4. **Show a receipt and confirm** before posting each document with `sap_b1_sl_write`
   (`POST Orders`, `POST DeliveryNotes`, …). Use `sap_b1_create_draft` first only when the user
   wants a reviewable SAP draft; finalize per the draft-first rule in `reference.md`.

## Payload shapes

**New sales order (item lines):**
```
sap_b1_sl_write
  method: "POST"
  path: "Orders"
  body: {
    "CardCode": "<resolved>",
    "DocDate": "2026-07-08",
    "DocDueDate": "2026-07-22",
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

## Notes

- Reading status only? Use `sap-b1-lookups` — no writes.
- `DocDueDate` on an order is the delivery/valid-until date; use the user's date or a sensible
  default and say which.
- Dates are `YYYY-MM-DD`. Resolve items and accounts live — never reuse codes from another
  company. Set `VatGroup` only when needed, per the VAT note in `sap-b1-overview/reference.md`.
- If write tools aren't exposed, you can still read these documents with `sap_b1_get_document` /
  `sap_b1_sl_query`; tell the user creating needs a write-capable capability set.
