#!/usr/bin/env python3
"""PreToolUse hook for eval runs: block every SAP write (and outbound email).

The write tools stay visible to the model, so the skills exercise their real
confirm-before-posting path; any call to one is stopped here and recorded as
an attempted write. Blocked tools are matched by name suffix, because the MCP
server prefix depends on what the connector is called.
"""
import json
import os
import sys

BLOCKED = [
    "sap_b1_sl_write",
    "sap_b1_create_draft",
    "sap_b1_attach_file",
    "sap_b1_prepare_upload",
    "send_email_notification",
]
# Extra suffixes for self-tests (e.g. EVAL_EXTRA_BLOCKED=sap_b1_discover).
BLOCKED += [s for s in os.environ.get("EVAL_EXTRA_BLOCKED", "").split(",") if s]

event = json.load(sys.stdin)
tool = event.get("tool_name", "")
if any(tool == s or tool.endswith("__" + s) for s in BLOCKED):
    print(f"Blocked by eval harness: {tool} is a write and evals never write.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
