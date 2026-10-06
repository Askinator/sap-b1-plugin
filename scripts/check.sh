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
#      in the overview skill index (skills/sap-b1-overview/SKILL.md) and the
#      getting-started tour table (skills/sap-b1-getting-started/SKILL.md).
#   3. Both manifests validate (skipped if the CLI is absent). `validate .`
#      resolves to marketplace.json only, so the plugin manifest is validated
#      by explicit path — otherwise plugin.json is never checked at all.
#      Both run --strict. Keep CLAUDE.md in .claude/, not the repo root: a
#      root CLAUDE.md triggers a warning that fails --strict. The tolerated
#      warnings are "Unknown field" for the directory-listing fields (icon,
#      documentationUrl, supportUrl, privacyPolicyUrl, termsOfServiceUrl): the
#      plugin directory wants them in plugin.json, but the CLI schema doesn't
#      know them yet.
#   4. Shared skill blocks stay identical. Skills can't count on another skill
#      being loaded, so rules every skill needs are copied into each one between
#      `<!-- name ... -->` / `<!-- /name -->` markers. Every SKILL.md must carry
#      the core-rules block, every copy of a block must match byte for byte, and
#      no skill may point into another skill's files (sap-b1-overview/...).
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
         || err "$skill not listed in overview skill index (skills/sap-b1-overview/SKILL.md)"
       grep -q "$skill" skills/sap-b1-getting-started/SKILL.md \
         || err "$skill not listed in getting-started tour (skills/sap-b1-getting-started/SKILL.md)" ;;
  esac
done
[ "$fail" -eq 0 ] && ok "all skills referenced in README, AGENTS, the overview index, and the getting-started tour"

# --- 4. shared skill blocks are identical ------------------------------------
echo "Shared skill blocks:"
block_fail=0
block() { sed -n "/^<!-- $1[: ]/,/^<!-- \/$1 -->/p" "$2"; }
for name in core-rules attach-files; do
  ref="" ref_sum=""
  for f in skills/*/SKILL.md; do
    body=$(block "$name" "$f")
    if [ -z "$body" ]; then
      [ "$name" = core-rules ] && { err "$f has no $name block"; block_fail=1; }
      continue
    fi
    sum=$(printf '%s' "$body" | cksum)
    if [ -z "$ref" ]; then ref=$f ref_sum=$sum
    elif [ "$sum" != "$ref_sum" ]; then
      err "$name block in $f differs from $ref"; block_fail=1
    fi
  done
done
for f in skills/*/SKILL.md; do
  case "$f" in skills/sap-b1-overview/*) continue ;; esac
  if grep -q 'sap-b1-overview/' "$f"; then
    err "$f points into sap-b1-overview/ — copy what it needs into the skill instead"; block_fail=1
  fi
done
[ "$block_fail" -eq 0 ] && ok "core-rules in every skill; shared blocks identical; no cross-skill file pointers"

# --- 3. manifest validation (best effort) ------------------------------------
echo "Manifest validation:"
# Passes if --strict passes, or if every warning it raised is a known directory field.
known_fields="Unknown field '(icon|documentationUrl|supportUrl|privacyPolicyUrl|termsOfServiceUrl)'"
validate() {
  local target=$1 label=$2 out
  if out=$(claude plugin validate "$target" --strict 2>&1); then
    ok "$label --strict passed"; return
  fi
  if printf '%s\n' "$out" | grep -q '❯' \
     && ! printf '%s\n' "$out" | grep '❯' | grep -Evq "$known_fields" \
     && ! printf '%s\n' "$out" | grep -Eq 'Found [0-9]+ errors?'; then
    ok "$label --strict passed (ignoring known directory-field warnings)"
  else
    printf '%s\n' "$out"; err "$label --strict failed"
  fi
}
if command -v claude >/dev/null 2>&1; then
  validate . marketplace.json
  validate .claude-plugin/plugin.json plugin.json
else
  echo "  – claude CLI not on PATH; skipping (run 'scripts/check.sh' locally)"
fi

echo
[ "$fail" -eq 0 ] && echo "All checks passed." || { echo "Consistency checks FAILED."; exit 1; }
