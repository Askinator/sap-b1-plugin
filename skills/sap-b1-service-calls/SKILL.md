---
name: sap-b1-service-calls
description: "Creates and manages Service Calls (ServiceCalls) in SAP Business One via the Service Layer MCP — support tickets logged against a customer, with the activity → service call → hours → invoice workflow. Use whenever the user wants to create a service call, open or update a support ticket, log an issue for a customer, or ask about the IT support-to-invoice flow. Also triggers on Danish requests: opret en servicesag, support sag, sagsnummer, fejlmelding, reklamation, kundehenvendelse. Resolves the customer, contact, and any item/account references live for the connected company database."
---

# SAP B1 — service calls

Manage `ServiceCalls` (support tickets tied to a customer). Resolve the customer, contact, and any
referenced item/account **live** for the connected DB.

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

## Support-to-invoice workflow

1. **Service call** (`ServiceCalls`) — the ticket: subject, customer, description, status.
2. **Activities / work** — log actions against the call as `Activities` rows (see below).
3. **Invoice** — bill the accumulated work (see `sap-b1-invoices`).

## Steps

1. **Resolve the customer.** Query `BusinessPartners` for `CardCode` (filter on `CardName`). Get
   the `ContactCode` from the partner's contacts if the user names a contact person.
2. **Confirm fields for this DB** (skip if already described this session).
   `sap_b1_discover action="describe" name="ServiceCalls"` — field names for subject, status,
   origin, and problem type vary by configuration, so confirm before writing. Status/priority/type
   codes are configurable per DB; resolve valid values live rather than assuming numbers.
3. **Ask only if something is ambiguous** — several matching customers, or a status/type you'd
   have to guess. A service call isn't a financial posting, so an unambiguous request can go
   straight to creating it. Tickets often start from a customer email, screenshot, or PDF — if one
   is in the conversation, settle attachment intent before creating.
4. **Create the call** with `sap_b1_sl_write method="POST" path="ServiceCalls"`, then attach the
   file if the user said to (see *Attaching a file*).
5. **Update** an existing call with `sap_b1_sl_write method="PATCH" path="ServiceCalls(<id>)"`.
6. **Read** calls with `sap_b1_sl_query entity="ServiceCalls"` (filter by `CustomerCode`, status,
   or date).

## Payload shape (create)

```
sap_b1_sl_write
  method: "POST"
  path: "ServiceCalls"
  body: {
    "Subject": "<short summary>",
    "CustomerCode": "<resolved CardCode>",
    "ContactCode": <resolved, optional>,
    "Description": "<details>"
  }
```

Confirm the exact field names against `describe` first — `CustomerCode`/`Subject` are common but
verify for this DB, and only set status/priority/type with codes you resolved live.

## Log work against a call (activities)

Record what was done as an `Activities` row, then **link it to the call from the call side** — an
`Activity` has **no** service-call field. The link lives on the service call's `ServiceCallActivities`
collection, whose entries reference the activity by its `ActivityCode` (the activity's own key).
Describe both entities first if unsure (`sap_b1_discover action="describe" name="Activities"` and
`name="ServiceCall"`); note text goes in `Notes` (a `Details` field also exists).

Two steps:

1. **Create the activity** and capture the returned `ActivityCode`.
   ```
   sap_b1_sl_write
     method: "POST"
     path: "Activities"
     body: {
       "CardCode": "<resolved customer>",
       "Notes": "<what was done>",
       "ActivityDate": "<today, YYYY-MM-DD>"
     }
   ```
2. **Attach it to the call** by PATCHing the call and adding the activity to its
   `ServiceCallActivities` collection:
   ```
   sap_b1_sl_write
     method: "PATCH"
     path: "ServiceCalls(<ServiceCallID>)"
     body: { "ServiceCallActivities": [ { "ActivityCode": <the new ActivityCode> } ] }
   ```
   (A PATCH replaces the collection, so include every activity that should remain on the call, or
   set them all when you create/update the call.)

Resolve any activity type/subject codes live before writing. To review work already logged, read
the call's `ServiceCallActivities` to get the `ActivityCode`s, then read those `Activities` — you
can't filter `Activities` by service call directly. When it's time to bill the accumulated work,
hand off to `sap-b1-invoices` — resolve the service item or G/L account and VAT group live there.

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

- Show the created call's key (`ServiceCallID`) back to the user.
- If write tools are not exposed, you can still read calls with `sap_b1_sl_query`; explain that
  creating/updating needs a write-capable capability set.
