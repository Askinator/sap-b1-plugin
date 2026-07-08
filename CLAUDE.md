# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See [AGENTS.md](AGENTS.md) for the full guidance. In short:

- This is a **Claude Code plugin** (config + markdown skills), **not** an application — no build,
  test, lint, or runtime. The SAP B1 MCP **server is a separate, hosted project not in this repo**.
- The core invariant is **discovery-first**: skills never hardcode account numbers, tax codes, or
  item codes — everything tenant-specific is resolved live per company database. Only
  `skills/sap-b1-overview/reference.md` holds tenant-invariant facts.
- **Multi-tenant**: one hosted server per company DB. The plugin ships **skills only** — no bundled
  MCP server; each company adds its server URL as a custom connector (Settings → Connectors). Don't
  reintroduce a bundled `.mcp.json`/`userConfig.mcp_url` — it can't work in the Desktop/claude.ai UI
  users target.
- Skill **triggering keys off the `description` frontmatter**; Danish support lives as Danish
  trigger terms in those descriptions, not as translated skill files.
- Validate with `claude plugin validate . --strict`; ship updates by bumping `version` in
  `.claude-plugin/plugin.json`.
