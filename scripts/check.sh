#!/usr/bin/env bash
#
# Consistency check for the SAP B1 plugin repo.
#
# There is no build/test here — this guards the invariants that silently drift
# when a skill is added or a release is cut. Run from the repo root:
#
#   scripts/check.sh
#
# Checks:
#   1. plugin.json declares a version (the single source of truth; marketplace.json
#      carries none, so there is nothing to cross-check).
#   2. Every skills/*/ dir is referenced in README.md and AGENTS.md, and every
#      task skill (all but sap-b1-getting-started / sap-b1-overview) is listed
#      in the overview skill index (skills/sap-b1-overview/SKILL.md).
#   3. `claude plugin validate . --strict` passes (skipped if the CLI is absent).
#
# Exits non-zero on any failure so CI / a pre-commit hook can block the drift.

set -euo pipefail
cd "$(dirname "$0")/.."

fail=0
err() { printf '  ✗ %s\n' "$1"; fail=1; }
ok()  { printf '  ✓ %s\n' "$1"; }

# --- 1. plugin version present ----------------------------------------------
echo "Version:"
plugin_ver=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' .claude-plugin/plugin.json | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
if [ -n "$plugin_ver" ]; then ok "plugin.json version = $plugin_ver"
else err "plugin.json has no version field"; fi

# --- 2. every skill is listed in the hub docs --------------------------------
echo "Skill index coverage:"
for dir in skills/*/; do
  skill=$(basename "$dir")
  for hub in README.md AGENTS.md; do
    grep -q "$skill" "$hub" || err "$skill not referenced in $hub"
  done
  case "$skill" in
    sap-b1-getting-started|sap-b1-overview) ;;  # not part of the task-skill index
    *) grep -q "$skill" skills/sap-b1-overview/SKILL.md \
         || err "$skill not listed in overview skill index (skills/sap-b1-overview/SKILL.md)" ;;
  esac
done
[ "$fail" -eq 0 ] && ok "all skills referenced in README, AGENTS, and the overview index"

# --- 3. manifest validation (best effort) ------------------------------------
echo "Manifest validation:"
if command -v claude >/dev/null 2>&1; then
  if claude plugin validate . --strict; then ok "claude plugin validate --strict passed"
  else err "claude plugin validate --strict failed"; fi
else
  echo "  – claude CLI not on PATH; skipping (run 'claude plugin validate . --strict' locally)"
fi

echo
[ "$fail" -eq 0 ] && echo "All checks passed." || { echo "Consistency checks FAILED."; exit 1; }
