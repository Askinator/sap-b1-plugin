---
name: sap-b1-lookups
description: "Read-only lookups in SAP Business One via the Service Layer MCP — business partner balances and aging, open/outstanding invoices, and the status of sales orders, quotations, deliveries, and purchase orders. Use whenever the user asks what a customer owes, whether an invoice is overdue, the status of an order or quotation, or wants a balance/statement/aging summary — without creating or changing anything. Also triggers on Danish requests: hvad skylder kunden, saldo, restance, forfaldne fakturaer, kontoudtog, ordrestatus, tilbudsstatus. Resolves the business partner and any codes live for the connected company database."
---

# SAP B1 — balances, aging, and document status lookups

Answer "where do things stand" questions with **read-only** queries — no drafts, no writes. For
creating or changing documents, use the relevant task skill (`sap-b1-invoices`,
`sap-b1-journal-entries`, `sap-b1-service-calls`) instead.

Per `sap-b1-overview` → Rendering output, render a single balance, aging summary, or document
status as a data-record card — every time, not conditionally; keep multi-invoice lists as markdown
tables.

## Decide the shape

1. **Balance / aging for a partner?** → query `BusinessPartners`, filtered fields for balance.
2. **Which invoices are open/overdue?** → query `Invoices` (or `PurchaseInvoices`) filtered on
   payment status and due date.
3. **Status of an order, quotation, delivery, or PO?** → query the relevant entity set filtered on
   `DocumentStatus` and/or the partner/date.

## Steps

1. **Resolve the partner.** Query `BusinessPartners` for `CardCode` (filter on `CardName`). If
   ambiguous, list matches and ask which one.
2. **Confirm fields for this DB — only if unsure.** Try the common fields first
   (`CurrentAccountBalance` for open balance; aging buckets are usually a separate report, not a
   plain field — see Notes). Run `sap_b1_discover action="describe" name="BusinessPartners"` only
   when a field errors or comes back empty, and skip it entirely if you already described the
   entity this session.
3. **Query, don't write.** Use `sap_b1_sl_query` (or `sap_b1_sql_query` if enabled) — never
   `sap_b1_sl_write` or `sap_b1_create_draft` for a lookup task.
4. **Present a compact summary**: partner name, the number(s) asked for, and — for lists — a short
   table, not a raw dump of every field.

## Recipes

**Partner balance:**
```
sap_b1_sl_query
  entity: "BusinessPartners"
  select: "CardCode,CardName,CurrentAccountBalance"
  filter: "CardCode eq '<resolved>'"
```

**Open (unpaid) AR invoices for a customer:**
```
sap_b1_sl_query
  entity: "Invoices"
  select: "DocNum,DocDate,DocDueDate,DocTotal,PaidToDate"
  filter: "CardCode eq '<resolved>' and DocumentStatus eq 'bost_Open'"
```
Overdue = `DocumentStatus eq 'bost_Open'` and `DocDueDate lt <today, YYYY-MM-DDT00:00:00Z>`.

**Order / quotation / PO status:**
```
sap_b1_sl_query
  entity: "Orders"          # or "Quotations", "PurchaseOrders", "DeliveryNotes"
  select: "DocNum,DocDate,DocumentStatus,DocTotal"
  filter: "CardCode eq '<resolved>'"
```

**Aging via SQL (if enabled), e.g. AR aging by invoice:**
```
sap_b1_sql_query
  query: "SELECT DocNum, DocDueDate, DocTotal, PaidToDate FROM OINV
           WHERE CardCode = :cc AND DocStatus = 'O' ORDER BY DocDueDate"
  params: { "cc": "<resolved CardCode>" }
```
Confirm columns with `sap_b1_sql_reference table="OINV"` first if unsure.

## Notes

- This is a **read-only** skill. If the user's next ask is to act on what you found (pay, post,
  create), hand off to the matching task skill rather than writing from here.
- SAP B1 does not always expose a single "aging bucket" field — computing aging buckets (0-30,
  31-60, …) usually means pulling open invoices with due dates and bucketing them yourself against
  today's date.
- If `sap_b1_sql_query` is not exposed on this deployment, do the same lookups via
  `sap_b1_sl_query` with OData filters — slower for large aging reports but functionally
  equivalent.
- Don't assume `DocumentStatus`/`DocStatus` value spellings — confirm via `describe` or
  `sql_reference` if a filter returns nothing unexpected.
