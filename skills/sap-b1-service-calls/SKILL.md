---
name: sap-b1-service-calls
description: "Create and manage Service Calls (ServiceCalls) in SAP Business One via the Service Layer MCP — support tickets logged against a customer, with the activity → service call → hours → invoice workflow. Use whenever the user wants to create a service call, open or update a support ticket, log an issue for a customer, or ask about the IT support-to-invoice flow. Also triggers on Danish requests: opret en servicesag, support sag, sagsnummer, fejlmelding, reklamation, kundehenvendelse. Resolves the customer, contact, and any item/account references live for the connected company database."
---

# SAP B1 — service calls

Manage `ServiceCalls` (support tickets tied to a customer). Follow the discovery-first rule:
resolve the customer, contact, and any referenced item/account **live** for the connected DB.

Per `sap-b1-overview` → Rendering output, render a single service call as a data-record card —
every time, not conditionally.

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
3. **Create the call** with `sap_b1_sl_write method="POST" path="ServiceCalls"`.
4. **Update** an existing call with `sap_b1_sl_write method="PATCH" path="ServiceCalls(<id>)"`.
5. **Read** calls with `sap_b1_sl_query entity="ServiceCalls"` (filter by `CustomerCode`, status,
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
       "ActivityDate": "2026-07-08"
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

## Notes

- Show the created call's key (`ServiceCallID`) back to the user.
- If write tools are not exposed, you can still read calls with `sap_b1_sl_query`; explain that
  creating/updating needs a write-capable capability set.
