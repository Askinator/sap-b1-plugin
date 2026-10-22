---
name: sap-b1-attachments
description: "Attaches files to SAP Business One records that already exist, and lists what a record has attached, via the Service Layer MCP — a PDF, receipt, signed delivery note, contract, or photo added to a posted invoice, order, purchase document, journal entry, payment, service call, business partner, or item. Use whenever the user wants to attach, upload, or add a file to an existing SAP document or master record, or asks which files are attached to one. Also triggers on Danish requests: vedhæft, vedhæft fil, vedhæft til fakturaen, tilføj vedhæftning, upload fil til SAP, hvad er vedhæftet, vedhæftede filer. Not for booking a document and attaching its file in one go (\"book this receipt and attach it\") — the skill that creates the record attaches it. Resolves the target record live for the connected company database."
---

# SAP B1 — attach files to existing records, list attachments

Two jobs: **attach** a file to a record that already exists, and **list** what a record has
attached. Creating the record itself belongs to its task skill (`sap-b1-invoices`,
`sap-b1-journal-entries`, …), which attaches the file as part of that flow.

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

## Resolve the target record

The upload needs the record's **entity set and key** — not the number the user sees.

| Record | Entity set | Key (`targetKey`) |
|---|---|---|
| Sales/purchase documents (invoice, credit memo, order, quotation, delivery, PO, goods receipt, …) | `Invoices`, `CreditNotes`, `Orders`, `PurchaseInvoices`, … | `DocEntry` (number) |
| Incoming / outgoing payment | `IncomingPayments`, `VendorPayments` | `DocEntry` (number) |
| Journal entry | `JournalEntries` | `JdtNum` (number) |
| Service call | `ServiceCalls` | `ServiceCallID` (number) |
| Activity | `Activities` | `ActivityCode` (number) |
| Business partner | `BusinessPartners` | `CardCode` (string) |
| Item | `Items` | `ItemCode` (string) |

- A document number the user quotes is a `DocNum`. Query it to get the `DocEntry` (filter on
  `DocNum`, select `DocEntry,DocNum,CardCode,DocDate,DocTotal,AttachmentEntry`) — never pass a
  `DocNum` as the key; numbering series make the two differ.
- Found by partner, amount, or date instead of a number? Show the candidates and let the user
  pick; attach only to the record they confirm.
- For an entity not in the table, check it has the field first:
  `sap_b1_discover action="describe" name="<EntitySet>" propertyFilterRegex="AttachmentEntry"`.
  No field → SAP can't attach to it; say so.

Select `AttachmentEntry` in the same query: it tells you whether the record already has files.

## Attach

The user asked to attach, so once the target is unambiguous, upload — no confirmation receipt
(nothing financial posts). Posted documents accept attachments too; there is no need to cancel or
copy a closed document to add a file. A new file joins the record's existing attachment entry
rather than replacing it, so a second upload never removes the first.

Several files to one record: one token and one upload per file. Several files to several records:
pair each file with its record, show the pairing as a table, and upload after the user confirms it.

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

## List what's attached

1. Read the record's `AttachmentEntry` (resolve the record as above). `null` → nothing attached.
2. Query the entry:
   ```
   sap_b1_sl_query
     entity: "Attachments2"
     filter: "AbsoluteEntry eq <AttachmentEntry>"
   ```
   The lines come back inline in `Attachments2_Lines` — no `expand` needed.
3. Show a short table: `FileName` + `.` + `FileExtension`, `AttachmentDate`, and `FreeText` if set.
   Leave out `SourcePath`/`TargetPath`: they are server folders, not something the user can open.

File **contents** can't be fetched through these tools (`sap_b1_sl_query` has no `$value` read).
If the user wants to open a file, tell them to open it from the record's Attachments tab in the
SAP B1 client.

## Notes

- Removing or replacing an attached file isn't covered: the upload tools only add. If the user
  wants one gone, point them to the Attachments tab in the SAP B1 client.
