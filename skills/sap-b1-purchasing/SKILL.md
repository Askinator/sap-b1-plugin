---
name: sap-b1-purchasing
description: "Drive the SAP Business One purchasing lifecycle via the Service Layer MCP — purchase orders (PurchaseOrders), goods receipt POs (PurchaseDeliveryNotes), and their conversion forward into an AP invoice by copying from the base document. Use whenever the user wants to raise a purchase order, order from a vendor, receive goods against a PO, book a goods receipt, or turn a PO/receipt into a vendor bill. Also triggers on Danish requests: indkøbsordre, købsordre, bestil hos leverandør, opret indkøbsordre, varemodtagelse, godsmodtagelse, modtag varer, indkøbsproces. Resolves the vendor, items, and VAT group live for the connected company database."
---

# SAP B1 — purchasing (PO → goods receipt → AP invoice)

Create and advance purchasing documents. Follow the discovery-first rule: resolve the vendor,
items, and VAT/tax codes **live** for the connected DB (see `sap-b1-overview`).

When the visualize tools are available (see `sap-b1-overview` → Rendering output), render the
document-chain status (PO → goods receipt → AP invoice) as a data-record card.

## The flow

`PurchaseOrders` → `PurchaseDeliveryNotes` (goods receipt PO) → `PurchaseInvoices` (AP invoice).
Each stage **copies from the previous document** rather than retyping lines, so SAP carries pricing
and keeps the base document's status in sync. You can skip stages (e.g. PO straight to AP invoice).

| Stage | Entity set | DocObjectCode | Object type |
| --- | --- | --- | --- |
| Purchase order | `PurchaseOrders` | `oPurchaseOrders` | 22 |
| Goods receipt PO | `PurchaseDeliveryNotes` | `oPurchaseDeliveryNotes` | 20 |
| AP invoice | `PurchaseInvoices` | `oPurchaseInvoices` | 18 → see `sap-b1-invoices` |

## Steps

1. **Resolve the vendor** (`BusinessPartners` → `CardCode`, a supplier). If ambiguous, ask.
2. **Create the purchase order** with item lines (`ItemCode` + `Quantity`, optional `UnitPrice`)
   or service lines (`AccountCode` + `DocType: "dDocument_Service"`). Resolve every code and the
   `VatGroup` live.
3. **Receive goods by copying from the PO.** Resolve the PO's `DocEntry` (query `PurchaseOrders`,
   filter on `DocNum`), then set `BaseType: 22`/`BaseEntry`/`BaseLine` on each `PurchaseDeliveryNotes`
   line — copy only the quantities actually received (partial receipts leave the PO partially open).
   See the copy-from-base recipe in `sap-b1-overview/reference.md`.
4. **Book the AP invoice** by copying from the goods receipt (`BaseType: 20`) or the PO
   (`BaseType: 22`) — hand off to `sap-b1-invoices`, and set `NumAtCard` to the vendor's invoice
   number.
5. **Show a receipt and confirm** before posting each document with `sap_b1_sl_write`. Use
   `sap_b1_create_draft` first only when the user wants a reviewable SAP draft; finalize per the
   draft-first rule in `reference.md`.

## Payload shapes

**New purchase order (item lines):**
```
sap_b1_sl_write
  method: "POST"
  path: "PurchaseOrders"
  body: {
    "CardCode": "<resolved vendor>",
    "DocDate": "2026-07-08",
    "DocDueDate": "2026-07-22",
    "DocumentLines": [
      { "ItemCode": "<resolved>", "Quantity": 10, "UnitPrice": 42.00, "VatGroup": "<resolved>" }
    ]
  }
```

**Goods receipt copied from that PO:**
```
sap_b1_sl_write
  method: "POST"
  path: "PurchaseDeliveryNotes"
  body: {
    "CardCode": "<same as PO>",
    "DocumentLines": [
      { "BaseType": 22, "BaseEntry": <PO DocEntry>, "BaseLine": 0, "Quantity": 10 }
    ]
  }
```

## Notes

- On a PO, `DocDueDate` is the required-by/delivery date. Use the user's date or a sensible default
  and say which.
- Dates are `YYYY-MM-DD`. Resolve items, accounts, and VAT codes live — never reuse codes from
  another company.
- Reading status only (open POs, what's not yet received)? Use `sap-b1-lookups`.
- If write tools aren't exposed, you can still read these documents with `sap_b1_get_document` /
  `sap_b1_sl_query`; tell the user creating needs a write-capable capability set.
