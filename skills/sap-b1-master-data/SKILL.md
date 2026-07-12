---
name: sap-b1-master-data
description: "Create and maintain SAP Business One master data via the Service Layer MCP — business partners (BusinessPartners: customers and vendors) and items (Items) — so later documents have something to reference. Use whenever the user wants to create a new customer or vendor, add a business partner, set up a new item or product, update a partner's or item's details, or says a partner/item isn't in SAP yet. Also triggers on Danish requests: opret kunde, ny debitor, opret leverandør, ny kreditor, opret vare, nyt varenummer, stamdata, kundekartotek, varekartotek, ret kundeoplysninger. Resolves account groups, price lists, VAT groups, and G/L determinations live for the connected company database."
---

# SAP B1 — master data (business partners & items)

Create and update the records that documents reference: `BusinessPartners` (customers/vendors) and
`Items`. Follow the discovery-first rule — resolve groups, price lists, VAT groups, and any G/L
determination **live** for the connected DB (see `sap-b1-overview`).

When the visualize tools are available (see `sap-b1-overview` → Rendering output), render the new
customer/vendor/item confirmation as a data-record card before creating.

## Check it doesn't already exist first

Before creating, search for a duplicate: query `BusinessPartners` (by `CardName`) or `Items` (by
`ItemName`). If a close match exists, show it and ask whether to use or update it rather than
creating a second record. Duplicate partners/items are hard to untangle later.

## Business partners

1. **Pick the type.** `CardType` = `cCustomer` (customer), `cSupplier` (vendor), or `cLid` (lead).
2. **Resolve config codes live.** The account/partner **group** (`GroupCode`) and any default
   `PriceListNum` are DB-specific — resolve valid values via `describe`/lookup, don't invent them.
3. **Always supply a `CardCode`.** Most SAP B1 databases do **not** auto-assign it on create —
   unlike document `DocNum`, `CardCode` auto-numbering (General Settings → BP → "BP Code
   Generation") is opt-in and rarely enabled. Omitting it typically fails with
   `Code undefined [OCRD.CardCode]`. Query a couple of existing `BusinessPartners` of the same
   `CardType` first (e.g. `$filter=CardType eq 'cSupplier'&$top=3&$select=CardCode`) to infer this
   DB's coding convention (`S00001`, `S-ACME`, etc.), then generate a matching, unused code — don't
   invent a convention from scratch. Only omit `CardCode` if discovery confirms auto-numbering is
   on for this DB.
4. **Create** with `sap_b1_sl_write method="POST" path="BusinessPartners"`.

```
sap_b1_sl_write
  method: "POST"
  path: "BusinessPartners"
  body: {
    "CardCode": "<generated to match this DB's convention>",
    "CardName": "<name>",
    "CardType": "cCustomer",
    "GroupCode": <resolved>,
    "FederalTaxID": "<VAT/CVR no. if given>"
  }
```

Add addresses (`BPAddresses`) and contacts (`ContactEmployees`) only when the user provides them;
confirm those collection field names via `describe` first. Update with
`PATCH BusinessPartners('<CardCode>')`.

## Items

1. **Resolve config codes live.** `ItemsGroupCode` (item group) and, for stock items, warehouse and
   G/L determination are DB-specific — resolve them, don't guess.
2. **Set the item's nature** with the flags this DB uses (commonly `InventoryItem`, `SalesItem`,
   `PurchaseItem` as `tYES`/`tNO`) — confirm names via `describe`.
3. **Create** with `sap_b1_sl_write method="POST" path="Items"`.

```
sap_b1_sl_write
  method: "POST"
  path: "Items"
  body: {
    "ItemCode": "<code>",
    "ItemName": "<description>",
    "ItemsGroupCode": <resolved>,
    "InventoryItem": "tYES",
    "SalesItem": "tYES",
    "PurchaseItem": "tYES"
  }
```

Update with `PATCH Items('<ItemCode>')`.

## Notes

- **Confirm fields for this DB.** `sap_b1_discover action="describe" name="BusinessPartners"` (or
  `Items`) — group codes, price lists, and determination fields vary widely by configuration.
- Master data is not financial, so there's no draft step — but still show the user what you're
  about to create and confirm the resolved group/price-list/VAT values before posting.
- If write tools aren't exposed, you can still read master data with `sap_b1_sl_query`; tell the
  user creating/updating needs a write-capable capability set.
