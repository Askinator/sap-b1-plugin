---
name: sap-b1-credit-memos
description: "Creates credit memos in SAP Business One via the Service Layer MCP — AR credit memos (CreditNotes) to a customer and AP credit memos (PurchaseCreditNotes) from a vendor, either standalone or copied from the original invoice — and reverses or corrects a posted document the right way. Use whenever the user wants to credit a customer, issue a refund or return, cancel or reverse a posted invoice, book a vendor credit, or undo a wrong posting. Also triggers on Danish requests: kreditnota, kreditér kunde, tilbageførsel, modpostering, annuller faktura, returnering, varer retur, leverandørkreditnota. Resolves the business partner, items, G/L accounts, and VAT group live for the connected company database."
---

# SAP B1 — credit memos and reversals

Issue **AR credit memos** (`CreditNotes`) to customers and **AP credit memos**
(`PurchaseCreditNotes`) from vendors, and correct posted documents. Resolve the partner, items,
G/L accounts, and VAT/tax codes **live** for the connected DB.

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

## In SAP B1 you reverse by crediting, not deleting

A **posted** invoice or journal entry is **not** deleted — it's offset by a reversing document. To
undo a posted AR invoice, raise a `CreditNotes` (ideally copied from that invoice so amounts, tax,
and stock reverse exactly); for a posted AP invoice, a `PurchaseCreditNotes`; for a posted journal
entry, a reversing entry (see `sap-b1-journal-entries`). Only an unposted **draft** can be deleted
outright. Never attempt a raw `DELETE` on a posted document.

## Decide the shape

1. **AR or AP?** Crediting a customer → `CreditNotes` (`oCreditNotes`). Vendor credit →
   `PurchaseCreditNotes` (`oPurchaseCreditNotes`).
2. **From an invoice, or standalone?**
   - **Reverse/return against a specific invoice (preferred)** → copy from the base invoice so
     quantities, pricing, tax, and stock reverse cleanly.
   - **Standalone** → build item lines (`ItemCode`) or service lines (`AccountCode` +
     `DocType: "dDocument_Service"`), same shapes as an invoice.

## Steps

1. **Resolve the partner** (`BusinessPartners` → `CardCode`).
2. **Locate the source invoice** if crediting one: query `Invoices`/`PurchaseInvoices` filtered on
   the `DocNum` the user quotes to get its `DocEntry` (the key — `DocNum` is not) and the lines to
   reverse. Batch this with the partner lookup.
3. **Build lines.** For a copy, reference the invoice on each line with `BaseType`
   (`13` AR invoice / `18` AP invoice), `BaseEntry` (invoice `DocEntry`), `BaseLine` (its
   `LineNum`, 0-based). Credit only the lines/quantities being returned; partial credits are
   normal.
4. **Show a receipt and confirm**, then post with `sap_b1_sl_write` (`POST CreditNotes` /
   `POST PurchaseCreditNotes`). If a file is in the conversation, settle attachment intent in this
   same turn. Use `sap_b1_create_draft` first only if the user wants a reviewable SAP draft, and
   finalize it per the draft rule in Core rules.

## Payload shape (AR credit memo, copied from an invoice)

```
sap_b1_sl_write
  method: "POST"
  path: "CreditNotes"
  body: {
    "CardCode": "<resolved>",
    "DocDate": "<today, YYYY-MM-DD>",
    "DocumentLines": [
      { "BaseType": 13, "BaseEntry": <invoice DocEntry>, "BaseLine": 0, "Quantity": 1 }
    ]
  }
```

Standalone item line: `{ "ItemCode": "<resolved>", "Quantity": 1 }`.
Standalone service line: header `DocType: "dDocument_Service"`, line
`{ "AccountCode": "<resolved G/L>", "LineTotal": 500.00 }`.

<!-- attach-files: identical in every SAP B1 skill that attaches files; scripts/check.sh enforces it -->
## Attaching a file

When the user said to attach, do it right after the record exists:

1. `sap_b1_prepare_upload` with `targetEntity` (the entity set, e.g. `PurchaseInvoices`) and
   `targetKey` (the record's key — a number for `DocEntry`-style keys, a string for `CardCode`)
   → `{ token, uploadUrl }`. The target is bound into the token.
2. Upload the file as an HTTP `POST` to `uploadUrl` with `multipart/form-data`: header
   `x-upload-token: <token>` and **only** the form field `file` (the file, with its MIME type).
   Any other field (`entity`, `key`, `fileName`, …) is rejected with 400. The token is single-use
   and spent by any attempt, so every retry starts again at step 1.
3. A 200 returns `attachmentEntry`; the file joins the record's existing attachment entry, if it
   has one. If `renamedFrom` is present, the name was taken in SAP's attachment folder and the
   file was stored as `uploadedFile.fileName` — tell the user the stored name.

Errors answer `{ error, detail }`: 400 bad input, 401 token missing/used/expired, 409 name clash
(rename the file, new token), 422 SAP rejected it, 503 SAP unreachable. Show `detail` to the user;
never report a failed upload as attached. If a response has `attachmentEntry` with
`"attached": false`, don't re-upload — link it:
`sap_b1_sl_write method="PATCH" path="<EntitySet>(<key>)" body={ "AttachmentEntry": <n> }`.

`sap_b1_attach_file` (same `targetEntity`/`targetKey`) takes a file without the upload step:
`mode="base64"` with `base64Content` + `fileNameWithExtension`, or `mode="server_path"` with
`sourcePath` (a folder the SAP server reads), `fileName` (no extension), `fileExtension` (no dot).
Its `multipart` mode reads a path on the MCP host, which can't see chat uploads. If the file already
sits in such a folder — e.g. an earlier attempt stored it in SAP's attachment folder — attach it
with `server_path` instead of uploading again (from that folder, the records share one physical
file). Report the record and the attachment together ("invoice posted, `bilag.pdf` attached").
<!-- /attach-files -->

## Notes

- Copying from the invoice is safest — it reverses the exact tax and inventory postings. Prefer it
  over hand-built lines whenever a source invoice exists.
- Dates are `YYYY-MM-DD`. Omit `VatGroup` by default — SAP derives it via tax determination
  (and a copy-from-base reverses the invoice's tax exactly). Set it, resolved live, only when the
  user asks for a specific tax treatment, the post fails with a missing/invalid tax code, or this
  DB has no default for the line (more common on service lines).
- If the user actually wants a *payment refund* rather than a credit, see `sap-b1-payments`.
- If write tools aren't exposed, you can still read credit memos with `sap_b1_sl_query`; tell the
  user creating needs a write-capable capability set.
