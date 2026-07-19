---
name: sap-b1-getting-started
description: "First-run onboarding for someone new to the SAP Business One plugin (skills + hosted Service Layer MCP). Use when a user just installed or connected the plugin, asks how to get started, what this plugin or what Claude can do with SAP B1, how to use it, how to set it up, or wants a tour of the available skills and tools. Walks through verifying the MCP connection, what each skill does, why to work in Cowork, and setting up a recurring scheduled task (e.g. a daily overdue-invoice / AR-aging digest). Also triggers on Danish requests: kom godt i gang, hvordan bruger jeg det, hvad kan du, kom i gang, hvordan sætter jeg op, ny bruger. Routes to the right task skill; it does not perform SAP writes itself."
---

# SAP Business One — getting started

Welcome the user and orient them. This plugin is two things working together:

- a connection to a **hosted SAP B1 Service Layer MCP server** (one URL per company database), and
- a set of **skills** that teach Claude the common SAP B1 workflows.

Your job in a first session is to confirm the connection works, show what's possible, and set the
user up to get recurring value — not to rush into posting documents. Keep the tone practical and
follow the discovery-first rule from `sap-b1-overview` throughout.

Per `sap-b1-overview` → Rendering output, render the skill tour in section 2 as a card grid rather
than a markdown table — every time, not conditionally.

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
| Understand the tools + the discovery-first rule | `sap-b1-overview` |
| Check balances, aging, or a document's status (read-only) | `sap-b1-lookups` |
| Create/post an AR or AP invoice | `sap-b1-invoices` |
| Credit a customer/vendor or reverse a posted document | `sap-b1-credit-memos` |
| Register a customer/vendor payment against invoices | `sap-b1-payments` |
| Quote → order → deliver → invoice (sales) | `sap-b1-sales-process` |
| Purchase order → goods receipt → AP invoice | `sap-b1-purchasing` |
| Post a manual journal entry to the G/L | `sap-b1-journal-entries` |
| Open or manage a support/service ticket | `sap-b1-service-calls` |
| Create a new customer, vendor, or item | `sap-b1-master-data` |

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

Save writes for after the user is comfortable, and when you do write, follow the **draft-first**
pattern: `sap_b1_create_draft` → show a compact receipt → post only after the user confirms.

## 6. When something goes wrong

Set expectations about correcting mistakes so nobody panics:

- **Drafts are safe.** A draft (`sap_b1_create_draft`) posts nothing to the ledger — it can be edited
  or deleted freely. Do all the shaping there.
- **Posted documents are not simply deleted.** In SAP B1 a posted invoice or journal entry is
  corrected by a **reversing document** (credit memo, reversing journal entry), not a delete. If the
  user wants to undo a posted document, route to the relevant task skill and resolve the reversal
  accounts live — don't fabricate a fix or attempt a raw delete.

## Keep the plugin up to date

Skills improve over time. To pull the latest, the user runs `/plugin marketplace update` in Claude
Code (or updates the plugin from the desktop **Plugins** panel). Mention this once so they know new
skills and fixes arrive without reinstalling.

## Guardrails to mention once, up front

- **Discovery-first:** never guess an account, tax code, or item code — resolve it live (see
  `sap-b1-overview`). If a required code can't be resolved, stop and ask.
- **Tool availability varies:** a restricted deployment may expose only reads, and SQL tools exist
  only when the server has a SQL dialect configured. Degrade gracefully and tell the user what to
  enable.
- **Draft-first for anything financial:** confirm before posting to the ledger.
- **This is real business data:** balances, partners, and postings come from a live company
  database. Share results only with the intended user, and don't export or send them anywhere the
  user hasn't asked for.
