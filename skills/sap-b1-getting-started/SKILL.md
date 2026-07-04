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

## 1. Confirm the connection first

Before anything else, prove the MCP link is live with a lightweight, read-only call:

- `sap_b1_discover` with `action: "list_entity_sets"`. If it returns entity sets, you're connected —
  tell the user which company database responded if that's visible.

If it fails or the `sap_b1_*` tools aren't present, the server URL almost certainly isn't set:

- The endpoint comes from the `mcp_url` config, injected into `.mcp.json` as `${user_config.mcp_url}`.
- **In Claude Code (CLI):** you're prompted for the URL when the plugin is enabled.
- **In the Claude desktop "Plugins" UI:** the `${user_config.mcp_url}` substitution does *not* run —
  add the server under **Settings → Connectors → Add custom connector** and paste the real
  `https://…/mcp` endpoint by hand, then the skills can call the tools.

Don't guess a URL or fabricate data — if there's no connection, help the user set it up and stop.

## 2. What you can do here

| I want to… | Skill |
| --- | --- |
| Understand the tools + the discovery-first rule | `sap-b1-overview` |
| Check balances, aging, or a document's status (read-only) | `sap-b1-lookups` |
| Create/post an AR or AP invoice | `sap-b1-invoices` |
| Post a manual journal entry to the G/L | `sap-b1-journal-entries` |
| Open or manage a support/service ticket | `sap-b1-service-calls` |

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

Steer the first hands-on task to something **read-only** — e.g. "what does customer X owe?" or "show
me overdue invoices" via `sap-b1-lookups`. It proves the whole path end to end with zero risk. Save
writes for after the user is comfortable, and when you do write, follow the **draft-first** pattern:
`sap_b1_create_draft` → show a compact receipt → post only after the user confirms.

## Guardrails to mention once, up front

- **Discovery-first:** never guess an account, tax code, or item code — resolve it live (see
  `sap-b1-overview`). If a required code can't be resolved, stop and ask.
- **Tool availability varies:** a restricted deployment may expose only reads, and SQL tools exist
  only when the server has a SQL dialect configured. Degrade gracefully and tell the user what to
  enable.
- **Draft-first for anything financial:** confirm before posting to the ledger.
