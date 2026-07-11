---
name: sap-b1-live-artifacts
description: "Build a persisted, refreshable Cowork artifact (a live dashboard page) backed by live SAP Business One data via the Service Layer MCP, for views that don't exist as a single native SAP B1 screen — cross-entity joins (e.g. a customer health board combining AR aging, open service calls, and last order date), aggregate or trend visuals that SAP's grid-based reports don't show at a glance, or any report the user wants to check again later instead of re-asking in chat. Use whenever the user asks for a \"dashboard\", \"board\", \"tracker\", \"live view\", \"page I can check every morning\", says something \"isn't available in SAP\" and wants it visualized, or wants to turn a recurring report into something refreshable. Also triggers on Danish requests like \"et dashboard for mine sager\" or \"en oversigt jeg kan tjekke hver dag\". Requires the mcp__cowork__create_artifact tool. Not for one-off answers that belong in chat — those stay with sap-b1-lookups."
---

# SAP B1 — live artifacts

Build a persisted, refreshable dashboard page backed by live SAP Business One data, using
`mcp__cowork__create_artifact`. This sits on top of the other SAP B1 skills rather than replacing
them — it's for when the value comes from turning a read into something the user reopens later,
or from joining data that SAP keeps on separate screens.

## Is an artifact actually the right tool here?

SAP B1's native client shows one entity per screen — a customer's balance, their open orders,
their service tickets — each behind its own window or report. An artifact earns its keep when it
**joins** those screens into one glanceable view, or replaces a grid-of-numbers report with
something visual and interactive. If a single SAP B1 window, or a plain `sap-b1-lookups` query,
already answers the question, that's simpler and doesn't need a persistent page — don't reach for
this skill by default. Ask what native screen(s) this would replace or combine; if the honest
answer is "just the AR aging report, no join, no visual", suggest a scheduled digest (`schedule`
skill) or a chat lookup instead.

## Before building anything

Call `mcp__cowork__list_artifacts` first. If something close already exists, read its HTML (the
tool returns a `path`) instead of starting from scratch — extend it, match its visual style, or
point the user to it rather than duplicating. One wrinkle worth knowing: an artifact's HTML lives
as a file on the user's machine, so artifacts built on a different computer or before a reinstall
may be listed but no longer resolve. If an existing one looks stale or broken, say so rather than
assuming it works.

## Resolve the data live — two tools, two field-naming schemes

Discovery-first applies here like everywhere else in this plugin, with one extra wrinkle: you'll
usually choose between two different read tools, and their field names don't match each other.

- **`sap_b1_sl_query`** (OData / Service Layer) — self-describing via `sap_b1_discover`, safe,
  good for straightforward per-entity reads and simple filters.
- **`sap_b1_sql_query`** (raw read-only SQL against the underlying database) — much more efficient
  when the view needs to **join or aggregate across entities**. A per-row join done as several
  separate Service Layer calls, fanned out across N rows, turns into N-times-as-many round trips;
  the same join is often one SQL query. It's read-only — destructive statements are rejected before
  they reach the database — so reach for it freely whenever a join or aggregate is the actual point
  of the view.

The catch: raw SQL table and column names are **not** the same as the OData property names (for
example, a field reachable as `CustomerCode` over Service Layer sits on a differently-named column
on the matching raw table). Before writing a SQL query, confirm real column names with
`sap_b1_sql_reference` if it's configured (needs `SAP_B1_REFDB_PATH` set), or, if that's not
available, run a small trial query first — `SELECT TOP 1 * FROM <table>` or a query against
`INFORMATION_SCHEMA.COLUMNS` — rather than assuming a column mirrors the Service Layer name.

Whichever tool you use, **run the query for real in chat and look at the actual response shape
before writing it into the artifact's HTML.** Inside the artifact, `window.cowork.callMcpTool`
wraps the response in `{content, structuredContent, isError}`, but you see the unwrapped payload
in chat — build the parser around what you actually saw, not what you assume the shape is.

## Design for a flaky network, not a reliable one

The Service Layer session is often slower or more concurrency-limited than a handful of calls in
chat would suggest. A dashboard that fans out N parallel calls per row (say, joining 3 entities
across 8 rows — 24 concurrent requests) can silently hang with no error surfaced; the UI just sits
on "Loading…" forever, because a network stall inside `window.cowork.callMcpTool` won't reject on
its own. Build for that:

- **Cap concurrency.** Don't fire every row's calls at once — process rows in small batches (2-3
  concurrent) with a simple worker-pool pattern.
- **Timeout every call.** Wrap each `callMcpTool` call in a race against a ~15s timeout so a hang
  becomes a visible error instead of an infinite spinner.
- **Isolate errors per row.** One row's join failing shouldn't blank the whole board — catch
  per-row and render that row's card with an error state while the rest continue.
- **Render incrementally.** Paint skeleton rows immediately after the top-level list loads, then
  fill each one in as its data resolves, instead of waiting on one big `Promise.all` before
  painting anything.

This pattern (timeout wrapper + bounded worker pool + per-row try/catch) comes up on essentially
every artifact that fans out per-row calls — reuse it rather than reinventing it each time:

```js
function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(label + " timed out after " + Math.round(ms/1000) + "s")), ms)
    )
  ]);
}

async function runPool(items, limit, worker) {
  let idx = 0;
  const lanes = new Array(Math.min(limit, items.length)).fill(0).map(async () => {
    while (idx < items.length) {
      const i = idx++;
      await worker(items[i], i);
    }
  });
  await Promise.all(lanes);
}

// usage: render skeleton rows for `items` first, then —
await runPool(items, 2, async (item) => {
  const cardEl = document.getElementById("card-" + item.id);
  try {
    const data = await withTimeout(loadRow(item), 15000, "row " + item.id);
    cardEl.innerHTML = renderRow(data);
  } catch (err) {
    cardEl.innerHTML = `<p class="err-text">Couldn't load: ${err.message}</p>`;
  }
});
```

## Build the artifact

Follow `mcp__cowork__create_artifact`'s constraints exactly: self-contained HTML (inline all
CSS/JS), light mode only (`:root { color-scheme: light }`, light background, dark text — the
artifact renders in Cowork's light-mode UI regardless of the user's chat theme), only the
allow-listed CDN libraries (Chart.js, Grid.js, Mermaid) if charts or sortable tables are needed,
and pass `mcp_tools` as the exact fully-qualified names (`mcp__<server>__<tool>`) actually called
and verified this session — nothing untested.

Keep writes out of the artifact itself. An unattended dashboard that can silently post or modify
SAP records is a bad pattern — if the view surfaces something actionable ("this invoice needs a
reminder"), let the user come back to chat and act on it there with the normal draft-first flow
from the other SAP B1 skills, rather than embedding a write button in the artifact.

## Test before handing off

Claude can't see the rendered artifact — `list_artifacts` and reading the written HTML confirm it
was built as intended, but not that it renders correctly. After creating or updating, ask the user
to open it and check the render, and treat their answer as the real test. If something's off, the
status line and per-row error states from the resilience pattern above should say exactly where it
broke — use that instead of guessing blind.

Once the artifact exists, use `mcp__cowork__update_artifact` for fixes rather than
`create_artifact` again, and write a clear `update_summary` — it's shown to the user as an approval
prompt.
