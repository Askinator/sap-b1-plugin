---
name: sap-b1-lookups
description: "Read-only lookups in SAP Business One via the Service Layer MCP — business partner balances and aging, open/outstanding invoices, and the status of sales orders, quotations, deliveries, and purchase orders. Use whenever the user asks what a customer owes, which customers owe the most (top debtors, largest balances), whether an invoice is overdue, the status of an order or quotation, or wants a balance/statement/aging summary — without creating or changing anything. Also triggers on Danish requests: hvad skylder kunden, hvem skylder mest, største debitorer, saldo, restance, forfaldne fakturaer, kontoudtog, ordrestatus, tilbudsstatus. Resolves the business partner and any codes live for the connected company database."
---

# SAP B1 — balances, aging, and document status lookups

Answer "where do things stand" questions with **read-only** queries — no drafts, no writes. For
creating or changing documents, use the relevant task skill (`sap-b1-invoices`,
`sap-b1-journal-entries`, `sap-b1-service-calls`) instead.

<!-- core-rules: identical in every SAP B1 skill; scripts/check.sh enforces it -->
## Core rules

- **Load the tools before judging what's there.** If the `sap_b1_*` tools are listed by name only,
  load them all with one `ToolSearch` (`query: "sap_b1"`) before telling the user a capability is
  missing. Once loaded, a missing tool is real gating: fall back (`sap_b1_sl_query` when
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
4. **Present a compact summary**: partner name, the number(s) asked for with their currency code,
   and — for lists — a short table, not a raw dump of every field. Resolve the local currency code
   in the same round trip as the data (see Core rules) rather than leaving it unstated.

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
