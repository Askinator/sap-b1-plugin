---
name: sap-b1-getting-started
description: "First-run onboarding for someone new to the SAP Business One plugin (skills + hosted Service Layer MCP). Use when a user just installed or connected the plugin, asks how to get started, what this plugin or what Claude can do with SAP B1, how to use it, how to set it up, or wants a tour of the available skills and tools. Walks through verifying the MCP connection, what each skill does, why to work in Cowork, and setting up a recurring scheduled task (e.g. a daily overdue-invoice / AR-aging digest). Also triggers on Danish requests: kom godt i gang, hvordan bruger jeg det, hvad kan du, kom i gang, hvordan sætter jeg op, ny bruger. Routes to the right task skill; it does not perform SAP writes itself."
---

# SAP Business One — getting started

Welcome the user and orient them. This plugin is two things working together:

- a connection to a **hosted SAP B1 Service Layer MCP server** (one URL per company database), and
- a set of **skills** that teach Claude the common SAP B1 workflows.

Your job in a first session is to confirm the connection works, show what's possible, and set the
user up to get recurring value — not to rush into posting documents. Keep the tone practical.

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

## 1. Confirm the connection first

Before anything else, prove the MCP link is live with a lightweight, read-only call:

- `sap_b1_discover` with `action: "list_entity_sets"`. If it returns entity sets, you're connected —
  tell the user which company database responded if that's visible.

If it fails or the `sap_b1_*` tools aren't present, the connector isn't set up yet. This plugin
ships **skills only** — it does not bundle the server connection, because every company database
has its own URL. Each user adds their company's server as a custom connector:

- In **Claude Desktop / claude.ai**: **Settings → Connectors → Add custom connector** (or
  **Customize → Connectors** on claude.ai), give it a name (e.g. `sap-b1`), and paste the real
  `https://…/mcp` endpoint. The skills then call the `sap_b1_*` tools it exposes.
- Authenticate the connector if it prompts for OAuth / Cloudflare Access.

Don't guess a URL or fabricate data — if there's no connection, help the user set it up and stop.

### Know which company and environment you're on

This is a **live ERP**. Before any write, establish two things and say them back to the user:

- **Which company database** answered (each has its own URL, chart of accounts, and data).
- **Whether it's production or a test/sandbox** company. If it's unclear from the connection, ask —
  never assume you're on test. Real invoices and journal entries have real accounting consequences.

### Check what this deployment lets you do

The server gates tools by capability, so confirm early whether this connection is **read-only** or
allows writes. A quick `sap_b1_discover` tells you which `sap_b1_*` tools exist. If only reads are
exposed, say so up front — the user can look up and summarize, but creating or posting documents
needs the write tools enabled server-side.

## 2. What you can do here

| I want to… | Skill |
| --- | --- |
| Ask something no other skill covers, or explore the schema | `sap-b1-overview` |
| Check balances, aging, or a document's status (read-only) | `sap-b1-lookups` |
| Create/post an AR or AP invoice | `sap-b1-invoices` |
| Credit a customer/vendor or reverse a posted document | `sap-b1-credit-memos` |
| Register a customer/vendor payment against invoices | `sap-b1-payments` |
| Quote → order → deliver → invoice (sales) | `sap-b1-sales-process` |
| Purchase order → goods receipt → AP invoice | `sap-b1-purchasing` |
| Post a manual journal entry to the G/L | `sap-b1-journal-entries` |
| Open or manage a support/service ticket | `sap-b1-service-calls` |
| Create a new customer, vendor, or item | `sap-b1-master-data` |
| Send an internal SAP message to a user or department | `sap-b1-messages` |
| Build a refreshable dashboard over live SAP data (Cowork) | `sap-b1-live-artifacts` |

Everything tenant-specific (accounts, VAT groups, item codes) is resolved **live** against the
connected database — nothing is hardcoded, so the same skills work for any company.

## 3. Work in Cowork (recommended)

Suggest the user run SAP B1 work in **Cowork**. It gives a persistent workspace where the plugin and
its connector stay attached across a session, which suits ERP work that spans several steps —
building up a draft, reviewing an aging report, then acting on it — without re-connecting each time.
If they haven't set it up, point them at the `setup-cowork` skill.

## 4. Set up a recurring scheduled task (recommended)

The best first "aha" is automation. Offer to create a **scheduled task** that delivers value on a
cadence. A strong, safe default:

> **Every weekday at 08:00 — an overdue-invoice / AR-aging digest.** Uses `sap-b1-lookups` to pull
> open and overdue AR invoices and the top balances, then summarizes them.

Why this one: it's **read-only**, so it's safe to run unattended, and it surfaces money owed every
morning without anyone remembering to check. Once the user sees it, offer variants (a weekly service-
call backlog summary, a month-end open-items check).

Set it up via the scheduling capability available on the surface they're using (the `schedule` skill
for a recurring cloud routine, or a scheduled task in the desktop app). **Only schedule read-only
digests unattended.** Anything that writes — creating drafts, posting invoices or journal entries —
must keep a human in the loop; never automate a posting step.

## 5. A safe first task

Steer the first hands-on task to something **read-only** — it proves the whole path end to end with
zero risk. Offer the user a couple of concrete prompts to try, adapted to their words:

- "What does customer **&lt;name&gt;** owe, and is anything overdue?"
- "Show me the open AR invoices, oldest first."
- "What's the status of order / quotation **&lt;number&gt;**?"
- "List the open service calls for **&lt;customer&gt;**."

Save writes for after the user is comfortable. When you do write, show a compact confirmation
receipt in chat and post only after the user confirms; leave a `sap_b1_create_draft` draft in SAP
only if they want one to review there (see the draft rule in Core rules).

## 6. When something goes wrong

Tell the user how mistakes get corrected:

- **Nothing posts without a yes.** Every financial document is shown as a receipt first, and a SAP
  draft (`sap_b1_create_draft`, when the user asks for one) posts nothing to the ledger — it can be
  edited or deleted freely.
- **Posted documents are not simply deleted.** In SAP B1 a posted invoice or journal entry is
  corrected by a **reversing document** (credit memo, reversing journal entry), not a delete. If the
  user wants to undo a posted document, route to the relevant task skill and resolve the reversal
  accounts live — don't fabricate a fix or attempt a raw delete.

## Keep the plugin up to date

Skills improve over time. To pull the latest, the user runs `/plugin marketplace update` in Claude
Code (or updates the plugin from the desktop **Plugins** panel). Mention this once so they know new
skills and fixes arrive without reinstalling.

## Guardrails to mention once, up front

- **Discovery-first:** never guess an account, tax code, or item code — resolve it live. If a
  required code can't be resolved, stop and ask.
- **Tool availability varies:** a restricted deployment may expose only reads, and SQL tools exist
  only when the server has a SQL dialect configured. Degrade gracefully and tell the user what to
  enable.
- **Confirm before anything financial posts:** show the receipt, post only on the user's yes.
- **This is real business data:** balances, partners, and postings come from a live company
  database. Share results only with the intended user, and don't export or send them anywhere the
  user hasn't asked for.
