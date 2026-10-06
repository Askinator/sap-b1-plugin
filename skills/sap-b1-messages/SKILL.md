---
name: sap-b1-messages
description: "Sends internal SAP Business One messages/alerts (Messages entity) via the Service Layer MCP — to one user, several named users, or every user in a department, optionally with clickable links to B1 documents (orders, invoices, etc.) in the body. Use whenever the user wants to send a SAP message, notify or ping a colleague inside SAP, broadcast to a department or team, or test SAP message delivery. Also triggers on Danish requests: send en besked, sap besked, notificer afdelingen, informer teamet. Resolves the recipient(s) live for the connected company database — never guess a UserCode."
---

# SAP B1 — internal messages

Send `Messages` (the internal system message a user sees as an alert/mailbox icon inside the SAP
B1 client — not email or SMS, unless the user explicitly asks for those channels too). Resolve
every recipient **live** against the connected DB; never guess a `UserCode` or department code.

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

## Steps

1. **Work out who the message is for** — one user, several named users, or a department/team. See
   *Resolving recipients* below.
2. **Build `RecipientCollection`** — one entry per resolved user.
3. **Optional: attach document links** — see *Linking documents*.
4. **Confirm the recipients when you chose them.** If you expanded a department/team or picked
   between similar names, show the resolved members and the text, and send only after the user
   says yes — a typo in the filter can silently grab the wrong group, and a sent message can't be
   recalled. Skip this when the user named one unambiguous recipient and gave the text, or when the
   send comes from a standing instruction the user wrote (e.g. a scheduled task's prompt): that
   instruction is the confirmation.
5. **Send it** with `sap_b1_sl_write method="POST" path="Messages"`.
6. **Report back** the created message's `Code` and exactly who it went to.

## Resolving recipients

### A single or a few named users

Query `Users`, filtering on `UserCode` or `UserName`:

```
sap_b1_sl_query
  entity: "Users"
  select: "UserCode,UserName,eMail"
  filter: "contains(UserName,'Bob')"
```

Take the `UserCode` from the result — that's what goes in the recipient entry. If more than one
user plausibly matches (common names), show the matches and ask which one before sending.

### A department / team broadcast

SAP B1's org-structure grouping for this is `Departments`. Resolve the department, then expand its
`Users` navigation to get every member in one call:

```
sap_b1_sl_query
  entity: "Departments"
  filter: "contains(Name,'Sales')"
  expand: "Users($select=UserCode,UserName)"
  select: "Code,Name"
```

Build one recipient entry per member returned. If the department has no members, or the name
doesn't resolve, say so rather than sending to nobody.

**A note on `UserGroups`:** some DBs also have `UserGroups` (e.g. Finance, Sales, Purchase,
Inventory) — but these are *authorization* groups, not distribution lists, and membership
(`Users.UserGroupByUser`) is frequently empty even when the group exists. Only treat a `UserGroup`
as a "team" if you've confirmed live that it actually has members. Don't populate group membership
yourself to make a send work — assigning users to an authorization group is a permissions change,
not a messaging one, and belongs in SAP B1's User Management, not this skill. Tell the user if
that's what they actually need.

## Recipient shape

Each entry in `RecipientCollection`:

```json
{ "UserCode": "<resolved code>", "SendInternal": "tYES" }
```

Internal (`SendInternal`) is the default and always what "send a SAP message" means. Only add
`"SendEmail": "tYES"` if the user explicitly asks for email fan-out too, and only for recipients
that actually have an `eMail` on their `Users` record — check first, don't assume it's set.

## Payload (create)

```
sap_b1_sl_write
  method: "POST"
  path: "Messages"
  body: {
    "Subject": "<short subject>",
    "Text": "<body text>",
    "Priority": "pr_Normal",
    "RecipientCollection": [
      { "UserCode": "<code>", "SendInternal": "tYES" }
    ]
  }
```

`Priority` is `pr_Low` / `pr_Normal` / `pr_High` — confirmed live via `sap_b1_discover` if unsure;
default to `pr_Normal` unless the user asks for urgent.

## Linking documents (optional)

To make a row of the message open a document when clicked, add a `MessageDataColumns` entry with
`Link: "tYES"` and one `MessageDataLine` per document:

```json
{
  "MessageDataColumns": [
    {
      "ColumnName": "Linked Document",
      "Link": "tYES",
      "MessageDataLines": [
        { "Object": "17", "ObjectKey": "<DocEntry>", "Value": "<display text>" }
      ]
    }
  ]
}
```

- `Object` is SAP's fixed system object-type code for the document (not DB-specific).
- `ObjectKey` is the document's `DocEntry` (as a string).
- `Value` is the text shown for that row.

Common codes: `23` sales quotation, `17` sales order, `15` delivery, `13` AR invoice, `14` AR
credit memo, `22` purchase order, `20` goods receipt PO, `18` AP invoice, `19` AP credit memo, `30`
journal entry, `24` incoming payment, `46` vendor payment, `191` service call. Verify anything else
(UDOs, less common doc types) rather than guessing.

Resolve the actual `DocEntry` for whatever document the user means (e.g. via `sap_b1_get_document`
or `sap_b1_sl_query`) before building the line — never invent one.

## Notes

- Show the created message's `Code` back to the user every time.
- There's no read-receipt or delivery confirmation via Service Layer — the recipient sees it next
  time they're active in the B1 client. Say so if the user asks "did they get it".
- If `sap_b1_sl_write` isn't exposed, you can still read message history with
  `sap_b1_sl_query entity="Messages"`; explain that sending needs a write-capable capability set.
