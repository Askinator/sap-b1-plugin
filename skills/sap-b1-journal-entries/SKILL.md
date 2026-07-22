---
name: sap-b1-journal-entries
description: "Post manual journal entries (JournalEntries) directly to the SAP Business One general ledger via the Service Layer MCP — expense bookings paid by card/bank/cash, receipt-based bilag, corrections, and reclassifications between G/L accounts where there is no vendor invoice and no item flow. Use whenever the user wants to post a journal entry, manuel postering, kassekladde, bogføringsbilag, or bilag, or book an expense, receipt, kvittering, or udlæg with no invoice. Resolves every G/L account live for the connected company database and keeps debits equal to credits."
---

# SAP B1 — manual journal entries

Post to `JournalEntries` when there is **no vendor relationship and no item flow** — a receipt
paid by card, a correction, or a reclassification. For a bill from a vendor, use
`sap-b1-invoices` (AP invoice) instead.

Per `sap-b1-overview` → Rendering output, render the draft receipt shown for pre-posting
confirmation as a data-record card — every time, not conditionally.

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
3. **Show a receipt and confirm.** Present the lines and the debit/credit totals in chat. If the
   user wants a reviewable SAP draft, create one with `sap_b1_create_draft`
   (`DocObjectCode: "oJournalEntries"`) and capture its `DraftEntry`.
4. **Post after confirmation** with `sap_b1_sl_write method="POST" path="JournalEntries"`. If you
   created a draft, approve it in SAP or delete it after posting so no orphan draft remains — see
   the draft-first finalize rule in `sap-b1-overview/reference.md`.

## Payload shape

```
sap_b1_create_draft
  DocObjectCode: "oJournalEntries"
  ReferenceDate: "2026-07-01"
  DueDate: "2026-07-01"
  TaxDate: "2026-07-01"
  Memo: "<short description>"
  JournalEntryLines: [
    { "AccountCode": "<expense G/L, resolved>", "Debit": 500.00, "LineMemo": "…" },
    { "AccountCode": "<payment G/L, resolved>", "Credit": 500.00, "LineMemo": "…" }
  ]
```

To post the real entry (after confirmation), send the same `JournalEntryLines`/header via
`sap_b1_sl_write method="POST" path="JournalEntries"` (drop `DocObjectCode`).

## Notes

- **File in the conversation?** Receipts and bilag usually arrive as a PDF or image — ask with
  `AskUserQuestion` whether to attach it to the journal entry **before** posting, alongside the
  confirmation, not after the entry exists. See the attachment section in
  `sap-b1-overview/reference.md`.
- Include VAT only when the user provides it and you can resolve the tax account/code live;
  otherwise post net and say so.
- Dates are `YYYY-MM-DD`.
- If write tools are not exposed on this deployment, explain that posting needs a write-capable
  capability set; you can still read existing entries with `sap_b1_sl_query entity="JournalEntries"`.
