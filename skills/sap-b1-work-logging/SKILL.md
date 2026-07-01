---
name: sap-b1-work-logging
description: Log technician work sessions against a SAP Business One service call or ticket using a draft AR invoice, then finalize into a real invoice when the job is done. Use whenever a technician says they are working on a ticket, service call, or SC number, wants to log time or hours, records what they did, asks for a summary of work on a ticket, or is ready to invoice a service call. Resolves the customer, service item/G-L account, and VAT group live for the connected company database.
---

# SAP B1 — work logging (draft invoice as a timesheet)

Accumulate a technician's work as lines on a **draft AR invoice**, then post it when the job is
done. This keeps a running, editable record tied to the customer without posting to the ledger
until finalize. Follow the discovery-first rule: resolve the customer, service item or G/L
account, and VAT code **live** for the connected DB.

## Model

- One **draft `Invoices`** document per job/ticket acts as the timesheet.
- Each work session is a **line** on that draft (a service line with `AccountCode` + `LineTotal`,
  or an item line with a labour `ItemCode` + `Quantity` in hours). Resolve the code live.
- **Finalize** = post the draft as a real AR invoice (see `sap-b1-invoices`).

## Steps

1. **Find or create the draft.** If a draft already exists for this ticket, read it with
   `sap_b1_sl_query entity="Drafts"` (filter on the customer / a reference field) or
   `sap_b1_get_document`. Otherwise create one with `sap_b1_create_draft`
   (`DocObjectCode: "oInvoices"`), resolving the `CardCode` from `BusinessPartners` first.
2. **Log a session** by adding a line. PATCH the draft with the full `DocumentLines` array
   including the new line (Service Layer replaces the collection):
   `sap_b1_sl_write method="PATCH" path="Drafts(<DocEntry>)"`.
   Put the work description in the line's free-text/`ItemDescription` field and hours in
   `Quantity` (item line) or the amount in `LineTotal` (service line).
3. **Summarize** on request by reading the draft's lines back and totalling hours/amounts.
4. **Finalize** after the user confirms: post a real `Invoices` document from the draft's contents
   with `sap_b1_sl_write method="POST" path="Invoices"`, then optionally delete the draft.

## Draft line (service) example

```
sap_b1_sl_write
  method: "PATCH"
  path: "Drafts(<DocEntry>)"
  body: {
    "DocumentLines": [
      { "AccountCode": "<labour G/L, resolved>", "LineTotal": 750.00,
        "ItemDescription": "2h on-site — replaced switch", "TaxCode": "<resolved>" }
    ]
  }
```

Include existing lines plus the new one in the array so none are lost.

## Notes

- Confirm the customer and the labour item/account once, at the start, then reuse for that draft.
- Show the running total after each logged session.
- If write tools are not exposed on this deployment, you can read/summarize existing drafts but
  cannot log or finalize — say so and point to the capability set.
