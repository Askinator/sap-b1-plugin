---
name: sap-b1-journal-entries
description: "Posts manual journal entries (JournalEntries) directly to the SAP Business One general ledger via the Service Layer MCP — expense bookings paid by card/bank/cash, receipt-based bilag, corrections, and reclassifications between G/L accounts where there is no vendor invoice and no item flow. Use whenever the user wants to post a journal entry, manuel postering, kassekladde, bogføringsbilag, or bilag, or book an expense, receipt, kvittering, or udlæg with no invoice. Resolves every G/L account live for the connected company database and keeps debits equal to credits."
---

# SAP B1 — manual journal entries

Post to `JournalEntries` when there is **no vendor relationship and no item flow** — a receipt
paid by card, a correction, or a reclassification. For a bill from a vendor, use
`sap-b1-invoices` (AP invoice) instead.

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

## Hard rules

- **Debits must equal credits.** Sum `Debit` across lines = sum `Credit`. Verify before posting.
- **Resolve every account live.** Look up each `AccountCode` in `ChartOfAccounts` (or `OACT` via
  SQL) for the connected DB. Never reuse an account number from another company or from memory.
  If you can't resolve an account, stop and ask.

## Steps

1. **Identify the accounts.** For an expense paid by card: one debit line to the expense account,
   one credit line to the payment account (card/bank/cash). Resolve both from `ChartOfAccounts` by
   name (e.g. filter `contains(Name,'…')`); if several match, show them and ask.
2. **Confirm line fields for this DB — only if unsure** (and not already described this session):
   `sap_b1_discover action="describe" name="JournalEntries"`, and describe the line type (search
   for `JournalEntryLines`). The payload shape below is standard — trust it until a call fails.
3. **Show a confirmation receipt and confirm.** Present the lines and the debit/credit totals.
   Expense receipts and bilag usually arrive as a PDF or image — if a file is in the conversation,
   settle attachment intent in this same turn. If the user wants a reviewable SAP draft, create one
   with `sap_b1_create_draft` (`DocObjectCode: "oJournalEntries"`) and capture its `DraftEntry`.
4. **Post after confirmation** with `sap_b1_sl_write method="POST" path="JournalEntries"`. If you
   created a draft, approve it in SAP or delete it after posting so no orphan draft remains. Attach
   the file if the user said to (see *Attaching a file*).

## Payload shape

```
sap_b1_sl_write
  method: "POST"
  path: "JournalEntries"
  body: {
    "ReferenceDate": "<today, YYYY-MM-DD>",
    "DueDate": "<today, YYYY-MM-DD>",
    "TaxDate": "<today, YYYY-MM-DD>",
    "Memo": "<short description>",
    "JournalEntryLines": [
      { "AccountCode": "<expense G/L, resolved>", "Debit": 500.00, "LineMemo": "…" },
      { "AccountCode": "<payment G/L, resolved>", "Credit": 500.00, "LineMemo": "…" }
    ]
  }
```

**SAP draft instead (only if the user wants one):** pass the same fields to `sap_b1_create_draft`
plus `DocObjectCode: "oJournalEntries"`.

<!-- attach-files: identical in every SAP B1 skill that attaches files; scripts/check.sh enforces it -->
## Attaching a file

When the user said to attach, do it right after the record exists:

1. `sap_b1_prepare_upload` (no args) → `{ token, uploadUrl }`.
2. Upload the file as an HTTP `POST` to `uploadUrl` with `multipart/form-data`: header
   `x-upload-token: <token>`, form fields `file` (the file, with its MIME type), `entity` (the
   entity set, e.g. `PurchaseInvoices`), and `key` (the record's key).
3. If the response has `"attached": false`, link it yourself:
   `sap_b1_sl_write method="PATCH" path="<EntitySet>(<key>)" body={ "AttachmentEntry": <n> }`.

For a file the SAP/MCP host can already read, or Base64 in memory, `sap_b1_attach_file` does it in
one call (`mode` `server_path` / `multipart` / `base64`, optional `target`). Report the record and
the attachment together ("invoice posted, `bilag.pdf` attached").
<!-- /attach-files -->

## Notes

- Include VAT only when the user provides it and you can resolve the tax account/code live;
  otherwise post net and say so.
- Dates are `YYYY-MM-DD`.
- If write tools are not exposed on this deployment, explain that posting needs a write-capable
  capability set; you can still read existing entries with `sap_b1_sl_query entity="JournalEntries"`.
