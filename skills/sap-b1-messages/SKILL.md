---
name: sap-b1-messages
description: "Send internal SAP Business One messages/alerts (Messages entity) via the Service Layer MCP — to one user, several named users, or every user in a department, optionally with clickable links to B1 documents (orders, invoices, etc.) in the body. Use whenever the user wants to send a SAP message, notify or ping a colleague inside SAP, broadcast to a department or team, or test SAP message delivery. Also triggers on Danish requests: send en besked, sap besked, notificer afdelingen, informer teamet. Resolves the recipient(s) live for the connected company database — never guess a UserCode."
---

# SAP B1 — internal messages

Send `Messages` (the internal system message a user sees as an alert/mailbox icon inside the SAP
B1 client — not email or SMS, unless the user explicitly asks for those channels too). Follow the
discovery-first rule: resolve every recipient **live** against the connected DB, never guess a
`UserCode` or department code.

## Steps

1. **Work out who the message is for** — one user, several named users, or a department/team. See
   *Resolving recipients* below.
2. **Build `RecipientCollection`** — one entry per resolved user.
3. **Optional: attach document links** — see *Linking documents*.
4. **Create it** with `sap_b1_sl_write method="POST" path="Messages"`.
5. **Report back** the created message's `Code` and exactly who it went to. For a department/team
   broadcast, list the resolved members before sending — the user should see the fan-out, not just
   the department name, since a typo in the filter can silently grab the wrong group.

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

Common, well-known object-type codes — safe defaults, but verify anything unusual (UDOs, less
common doc types) rather than guessing:

| Document | Code |
| --- | --- |
| Sales Quotation | 23 |
| Sales Order | 17 |
| Delivery | 15 |
| A/R Invoice | 13 |
| A/R Credit Memo | 14 |
| Purchase Order | 22 |
| Goods Receipt PO | 20 |
| A/P Invoice | 18 |

Resolve the actual `DocEntry` for whatever document the user means (e.g. via `sap_b1_get_document`
or `sap_b1_sl_query`) before building the line — never invent one.

## Notes

- Show the created message's `Code` back to the user every time.
- There's no read-receipt or delivery confirmation via Service Layer — the recipient sees it next
  time they're active in the B1 client. Say so if the user asks "did they get it".
- If `sap_b1_sl_write` isn't exposed, you can still read message history with
  `sap_b1_sl_query entity="Messages"`; explain that sending needs a write-capable capability set.
