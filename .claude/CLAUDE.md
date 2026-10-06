# CLAUDE.md

See [AGENTS.md](../AGENTS.md) for the full guidance. In short:

- This is a **Claude plugin** (manifest + markdown skills) shipped to Claude Desktop, **not** an
  application — no build, test, lint, or runtime. The SAP B1 MCP **server is a separate, hosted
  project not in this repo**.
- The core invariant is **discovery-first**: skills never hardcode account numbers, tax codes, or
  item codes — everything tenant-specific is resolved live per company database. Only
  tenant-invariant facts (object types, entity names) are written down.
- **Skills are self-contained**: none relies on another being loaded. Rules every skill needs sit
  in a marked shared block (`<!-- core-rules -->`, `<!-- attach-files -->`) copied verbatim into
  each `SKILL.md`; `scripts/check.sh` fails on drift between copies.
- **This repo is public.** Debugging happens against live company databases, so keep tenant data
  out of skills, commits, and PR/issue bodies alike: no company or customer names, `CardCode`s,
  G/L accounts, tax or item codes, server URLs, or credentials — and avoid real document numbers
  and amounts. Use invented placeholders, and describe the behaviour a session exposed rather than
  the record it came from.
- **Multi-tenant**: one hosted server per company DB. The plugin ships **skills only** — no bundled
  MCP server; each company adds its server URL as a custom connector (Settings → Connectors). Don't
  reintroduce a bundled `.mcp.json`/`userConfig.mcp_url` — it can't work in the Claude Desktop UI
  users target.
- Skill **triggering keys off the `description` frontmatter**; Danish support lives as Danish
  trigger terms in those descriptions, not as translated skill files.
- This file lives in `.claude/`, not the repo root: the repo root *is* the plugin root, and the
  directory submission flags a root `CLAUDE.md` (it isn't loaded for plugin users anyway).
- Skills must not contain literal download/upload shell commands (e.g. `curl ...`) — the directory
  scanner flags them as download-and-run. Describe HTTP requests in prose instead.
- Run `scripts/check.sh` before opening a PR **and before bumping the version** — it covers
  skill-index drift (also enforced in CI) and manifest validation (local only; CI has no `claude`
  CLI). Ship updates by bumping `version` in `.claude-plugin/plugin.json`.
