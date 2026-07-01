---
name: sap-b1-service-calls
description: Create and manage Service Calls (ServiceCalls) in SAP Business One via the Service Layer MCP — support tickets logged against a customer, with the activity → service call → hours → invoice workflow. Use whenever the user wants to create a service call, open or update a support ticket, log an issue for a customer, or ask about the IT support-to-invoice flow. Resolves the customer, contact, and any item/account references live for the connected company database.
---

# SAP B1 — service calls

Manage `ServiceCalls` (support tickets tied to a customer). Follow the discovery-first rule:
resolve the customer, contact, and any referenced item/account **live** for the connected DB.

## Support-to-invoice workflow

1. **Service call** (`ServiceCalls`) — the ticket: subject, customer, description, status.
2. **Activities / work** — log time and actions against the call (see `sap-b1-work-logging` for
   the draft-invoice time-logging approach).
3. **Invoice** — bill the accumulated work (see `sap-b1-invoices`).

## Steps

1. **Resolve the customer.** Query `BusinessPartners` for `CardCode` (filter on `CardName`). Get
   the `ContactCode` from the partner's contacts if the user names a contact person.
2. **Confirm fields for this DB.** `sap_b1_discover action="describe" name="ServiceCalls"` — field
   names for subject, status, origin, and problem type vary by configuration, so confirm before
   writing. Status/priority/type codes are configurable per DB; resolve valid values live rather
   than assuming numbers.
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

## Notes

- Show the created call's key (`ServiceCallID`) back to the user.
- If write tools are not exposed, you can still read calls with `sap_b1_sl_query`; explain that
  creating/updating needs a write-capable capability set.
