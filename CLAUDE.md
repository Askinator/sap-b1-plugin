# CLAUDE.md

See [AGENTS.md](AGENTS.md) for the full guidance. In short:

- This is a **Claude plugin** (manifest + markdown skills) shipped to Claude Desktop, **not** an
  application — no build, test, lint, or runtime. The SAP B1 MCP **server is a separate, hosted
  project not in this repo**.
- The core invariant is **discovery-first**: skills never hardcode account numbers, tax codes, or
  item codes — everything tenant-specific is resolved live per company database. Only
  `skills/sap-b1-overview/reference.md` holds tenant-invariant facts.
- **Multi-tenant**: one hosted server per company DB. The plugin ships **skills only** — no bundled
  MCP server; each company adds its server URL as a custom connector (Settings → Connectors). Don't
  reintroduce a bundled `.mcp.json`/`userConfig.mcp_url` — it can't work in the Claude Desktop UI
  users target.
- Skill **triggering keys off the `description` frontmatter**; Danish support lives as Danish
  trigger terms in those descriptions, not as translated skill files.
- Run `scripts/check.sh` before opening a PR **and before bumping the version** — it covers
  skill-index drift (also enforced in CI) and manifest validation (local only; CI has no `claude`
  CLI). Ship updates by bumping `version` in `.claude-plugin/plugin.json`.
