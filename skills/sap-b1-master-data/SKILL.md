---
name: sap-b1-master-data
description: "Creates and maintains SAP Business One master data via the Service Layer MCP — business partners (BusinessPartners: customers and vendors) and items (Items) — so later documents have something to reference. Use whenever the user wants to create a new customer or vendor, add a business partner, set up a new item or product, update a partner's or item's details, or says a partner/item isn't in SAP yet. Also triggers on Danish requests: opret kunde, ny debitor, opret leverandør, ny kreditor, opret vare, nyt varenummer, stamdata, kundekartotek, varekartotek, ret kundeoplysninger. Resolves account groups, price lists, VAT groups, and G/L determinations live for the connected company database."
---

# SAP B1 — master data (business partners & items)

Create and update the records that documents reference: `BusinessPartners` (customers/vendors) and
`Items`. Resolve groups, price lists, VAT groups, and any G/L determination **live** for the
connected DB.

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
4. **Show it and wait for a yes.** List what you'll create — `CardCode`, name, type, and the
   group (and any price list or VAT values) you resolved — and create only after the user
   confirms. When several groups fit, ask which rather than picking one. A `CardCode` can't be
   renamed once it exists.
5. **Create** with `sap_b1_sl_write method="POST" path="BusinessPartners"`.

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
3. **Show it and wait for a yes.** List the `ItemCode`, name, item group, and flags you'll set,
   and create only after the user confirms.
4. **Create** with `sap_b1_sl_write method="POST" path="Items"`.

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

- **Confirm fields for this DB** (skip if already described this session).
  `sap_b1_discover action="describe" name="BusinessPartners"` (or `Items`) — group codes, price
  lists, and determination fields vary widely by configuration.
- Master data is not financial, so there's no draft step — the confirm step above is the check.
- If write tools aren't exposed, you can still read master data with `sap_b1_sl_query`; tell the
  user creating/updating needs a write-capable capability set.
