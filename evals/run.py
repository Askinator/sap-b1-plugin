#!/usr/bin/env python3
"""Run the SAP B1 skill evals with headless Claude Code.

Each case in evals/cases/*.json is sent as a single prompt to `claude -p` with
this repo loaded as a plugin. The stream-json trace is checked for:

  - triggering: which sap-b1 skills were invoked (Skill tool calls)
  - tool use:   which sap_b1_* tools were called, and that no write was attempted
  - behaviour:  a rubric (`expected_behavior`) graded by a small judge model

Writes are never possible: a PreToolUse hook (hooks/block_writes.py) blocks
every SAP write tool while leaving it visible to the model, so the skills run
their normal confirm-before-posting path. An attempted write fails the case.

Usage (from anywhere):
  python3 evals/run.py --probe                  # check plugin, connector, hook
  python3 evals/run.py                          # all cases, 3 runs each
  python3 evals/run.py --case 'lookups-*' --runs 1
  python3 evals/run.py --baseline               # also run without the plugin

The SAP connection comes from evals/local.mcp.json (gitignored; see
evals/README.md). Without it, cases marked `needs_sap` are skipped. Results
land in evals/results/<timestamp>/ (gitignored: traces contain live data).
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
HOOK = EVALS / "hooks" / "block_writes.py"
WRITE_TOOLS = [
    "sap_b1_sl_write",
    "sap_b1_create_draft",
    "sap_b1_attach_file",
    "sap_b1_prepare_upload",
    "send_email_notification",
]
READ_TOOLS = [
    "sap_b1_discover",
    "sap_b1_get_document",
    "sap_b1_sl_query",
    "sap_b1_sql_query",
    "sap_b1_sql_reference",
]
# A whole case — including skill loading and several lookups — should finish well inside this.
RUN_TIMEOUT_S = 900


def mcp_server_names(mcp_config):
    if not mcp_config:
        return []
    servers = json.loads(Path(mcp_config).read_text()).get("mcpServers", {})
    # Claude Code tool names carry the server name with non-alphanumerics replaced by "_".
    return [re.sub(r"[^A-Za-z0-9_-]", "_", name) for name in servers]


def claude_cmd(prompt, args, with_plugin):
    settings = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "*", "hooks": [{"type": "command", "command": f"python3 '{HOOK}'"}]}
            ]
        }
    }
    allowed = ["Skill", "ToolSearch", "Read", "Grep", "Glob"]
    for server in mcp_server_names(args.mcp_config):
        allowed += [f"mcp__{server}__{t}" for t in READ_TOOLS]
    cmd = [
        "claude", "-p", prompt,
        "--model", args.model,
        "--output-format", "stream-json", "--verbose",
        # The user's CLI default may be auto mode; evals must never inherit it.
        "--permission-mode", "default",
        "--settings", json.dumps(settings),
        "--allowedTools", *allowed,
    ]
    if with_plugin:
        cmd += ["--plugin-dir", str(REPO)]
    if args.mcp_config:
        cmd += ["--mcp-config", str(Path(args.mcp_config).resolve()), "--strict-mcp-config"]
    return cmd


def run_claude(prompt, args, with_plugin, extra_env=None):
    """Run one headless session from an empty temp dir (so no repo CLAUDE.md or memory loads)."""
    env = dict(os.environ, **(extra_env or {}))
    with tempfile.TemporaryDirectory(prefix="sap-b1-eval-") as cwd:
        proc = subprocess.run(
            claude_cmd(prompt, args, with_plugin), cwd=cwd, env=env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=RUN_TIMEOUT_S,
        )
    events = []
    for line in proc.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    if not events:
        raise RuntimeError(f"claude produced no events (exit {proc.returncode}): {proc.stderr.strip()[:500]}")
    return events


def parse(events):
    """Pull the init info, skills invoked, tool calls (with results), and the final answer."""
    init, calls, by_id, final, cost = {}, [], {}, "", 0.0
    for e in events:
        if e.get("type") == "system" and e.get("subtype") == "init":
            init = e
        elif e.get("type") == "assistant":
            for block in e.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    call = {"id": block["id"], "name": block["name"], "input": block.get("input", {}),
                            "error": False, "result": ""}
                    calls.append(call)
                    by_id[block["id"]] = call
        elif e.get("type") == "user":
            content = e.get("message", {}).get("content", [])
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_result" and block.get("tool_use_id") in by_id:
                    call = by_id[block["tool_use_id"]]
                    call["error"] = bool(block.get("is_error"))
                    body = block.get("content")
                    call["result"] = body if isinstance(body, str) else json.dumps(body)
        elif e.get("type") == "result":
            final = e.get("result") or ""
            cost = e.get("total_cost_usd") or 0.0
    skills = [c["input"].get("skill", "") for c in calls if c["name"] == "Skill"]
    return {"init": init, "calls": calls, "skills": skills, "final": final, "cost": cost}


def short(tool_name):
    return tool_name.split("__")[-1]


def deterministic_checks(case, run):
    checks = []
    invoked = {s.split(":")[-1] for s in run["skills"]}
    for skill in case.get("expect_skills", []):
        checks.append((f"skill {skill} invoked", skill in invoked))
    if case.get("forbid_sap_skills"):
        checks.append(("no sap-b1 skill invoked", not any(s.startswith("sap-b1") for s in invoked)))
    called = [short(c["name"]) for c in run["calls"]]
    if case.get("must_call_any"):
        wanted = case["must_call_any"]
        checks.append((f"called one of {wanted}", any(t in wanted for t in called)))
    for tool in case.get("must_not_call", WRITE_TOOLS):
        checks.append((f"did not call {tool}", tool not in called))
    return checks


def digest(run, limit=600):
    """A compact trace for the judge: tool calls, truncated results, and the final answer."""
    lines = []
    for c in run["calls"]:
        args = json.dumps(c["input"], ensure_ascii=False)[:400]
        lines.append(f"TOOL {short(c['name'])} {args}")
        lines.append(f"  -> {'ERROR ' if c['error'] else ''}{c['result'][:limit]}")
    lines.append("FINAL ANSWER:\n" + run["final"][:4000])
    return "\n".join(lines)


def judge(case, run, args):
    criteria = case.get("expected_behavior", [])
    if not criteria:
        return []
    prompt = (
        "You are grading an AI agent's run against a rubric. Judge only from the trace.\n"
        f"User request: {case['query']}\n\nTrace:\n{digest(run)}\n\n"
        "For each criterion return pass true/false with a one-line reason. Reply with ONLY a JSON "
        'array: [{"criterion": "...", "pass": true, "reason": "..."}]\n\nCriteria:\n'
        + "\n".join(f"- {c}" for c in criteria)
    )
    with tempfile.TemporaryDirectory(prefix="sap-b1-judge-") as cwd:
        proc = subprocess.run(
            ["claude", "-p", "--model", args.judge_model, "--output-format", "json",
             "--permission-mode", "default"],
            input=prompt, cwd=cwd, capture_output=True, text=True, timeout=300,
        )
    try:
        text = json.loads(proc.stdout)["result"]
        verdicts = json.loads(text[text.index("["): text.rindex("]") + 1])
        return [(v["criterion"], bool(v["pass"]), v.get("reason", "")) for v in verdicts]
    except (ValueError, KeyError, json.JSONDecodeError):
        return [(c, False, "judge output unparseable") for c in criteria]


def fill(query, local):
    missing = [k for k in re.findall(r"\{(\w+)\}", query) if k not in local]
    if missing:
        return None, missing
    return query.format(**local), []


def has_sap_tools(init):
    return any("sap_b1_" in t for t in init.get("tools", []))


def probe(args):
    print("Probe: plugin + connector")
    run = parse(run_claude("Reply with OK.", args, with_plugin=True))
    init = run["init"]
    plugins = [p["name"] for p in init.get("plugins", [])]
    sap_skills = sorted({s for s in init.get("skills", []) if s.startswith("sap-b1:")})
    sap_tools = sorted({short(t) for t in init.get("tools", []) if "sap_b1_" in t})
    print(f"  plugin loaded:  {'sap-b1' in plugins}")
    print(f"  sap-b1 skills:  {len(sap_skills)}")
    print(f"  sap_b1 tools:   {sap_tools or 'none (no connector; needs_sap cases will be skipped)'}")
    print(f"  permission:     {init.get('permissionMode')}")

    blocked = "sap_b1_discover" if sap_tools else "Read"
    ask = ("Call the sap_b1_discover tool with action list_entity_sets, then say what happened."
           if sap_tools else "Use the Read tool on /etc/hosts, then say what happened.")
    print(f"Probe: write-block hook (temporarily blocking {blocked})")
    run = parse(run_claude(ask, args, with_plugin=True, extra_env={"EVAL_EXTRA_BLOCKED": blocked}))
    hits = [c for c in run["calls"] if short(c["name"]) == blocked]
    ok = bool(hits) and all(c["error"] and "Blocked by eval harness" in c["result"] for c in hits)
    print(f"  hook blocked the call: {ok}" + ("" if hits else " (model never called it — rerun)"))

    print("Probe: baseline has no sap-b1 plugin")
    base = parse(run_claude("Reply with OK.", args, with_plugin=False))["init"]
    clean = not any(p["name"] == "sap-b1" for p in base.get("plugins", []))
    print(f"  baseline clean: {clean}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", default="*", help="glob on case name")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--judge-model", default="haiku")
    ap.add_argument("--baseline", action="store_true", help="also run each case without the plugin")
    ap.add_argument("--mcp-config", default=None, help="default: evals/local.mcp.json if present")
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()
    if args.mcp_config is None and (EVALS / "local.mcp.json").exists():
        args.mcp_config = str(EVALS / "local.mcp.json")

    if args.probe:
        return probe(args)

    local_path = EVALS / "local.json"
    local = json.loads(local_path.read_text()) if local_path.exists() else {}
    cases = [json.loads(p.read_text()) for p in sorted((EVALS / "cases").glob("*.json"))]
    cases = [c for c in cases if fnmatch.fnmatch(c["name"], args.case)]
    out = EVALS / "results" / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)
    arms = [("plugin", True)] + ([("baseline", False)] if args.baseline else [])
    summary, total_cost = [], 0.0

    for case in cases:
        query, missing = fill(case["query"], local)
        if query is None:
            print(f"SKIP {case['name']}: evals/local.json lacks {missing}")
            continue
        if case.get("needs_sap") and not args.mcp_config:
            print(f"SKIP {case['name']}: needs the SAP connector (evals/local.mcp.json)")
            continue
        filled = dict(case, query=query)
        for arm, with_plugin in arms:
            for n in range(1, args.runs + 1):
                events = run_claude(query, args, with_plugin)
                (out / f"{case['name']}.{arm}.{n}.jsonl").write_text(
                    "\n".join(json.dumps(e) for e in events))
                run = parse(events)
                if arm == "baseline" and any(p["name"] == "sap-b1" for p in run["init"].get("plugins", [])):
                    sys.exit("Baseline arm loaded a sap-b1 plugin anyway; baseline is invalid. Disable it and rerun.")
                if case.get("needs_sap") and not has_sap_tools(run["init"]):
                    sys.exit("SAP tools missing from the run although an MCP config was given; check the connector.")
                checks = deterministic_checks(filled, run) if arm == "plugin" else [
                    c for c in deterministic_checks(filled, run) if not c[0].startswith(("skill ", "no sap-b1"))]
                rubric = judge(filled, run, args)
                total_cost += run["cost"]
                rec = {
                    "case": case["name"], "arm": arm, "run": n, "skills": run["skills"],
                    "tools": [short(c["name"]) for c in run["calls"]],
                    "checks": [{"check": k, "pass": v} for k, v in checks],
                    "rubric": [{"criterion": k, "pass": v, "reason": r} for k, v, r in rubric],
                    "cost_usd": run["cost"],
                }
                summary.append(rec)
                ok = sum(v for _, v in checks), len(checks)
                rb = sum(v for _, v, _ in rubric), len(rubric)
                print(f"{case['name']:<32} {arm:<8} run {n}: checks {ok[0]}/{ok[1]}  rubric {rb[0]}/{rb[1]}"
                      + "".join(f"\n    ✗ {k}" for k, v in checks if not v)
                      + "".join(f"\n    ✗ {k} — {r}" for k, v, r in rubric if not v))

    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nAgent cost ${total_cost:.2f} (judge not included). Results: {out}")
    failed = [r for r in summary if r["arm"] == "plugin"
              and not all(c["pass"] for c in r["checks"])]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
