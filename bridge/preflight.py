import json
import os
import time

from bridge.gemma_client import call_gemma, parse_json_response
from bridge.prompts import PREFLIGHT_PROMPT, SYSTEM_PROMPT_BASE
from bridge.telemetry import get_state


def run_preflight_check() -> dict:
    state = get_state()
    system = SYSTEM_PROMPT_BASE.format(**state)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    user = PREFLIGHT_PROMPT.replace("{timestamp}", timestamp)

    raw = call_gemma(system, user, temperature=0.1)
    data = parse_json_response(raw)
    data["audit_entry"] = data.get("audit_entry", "").replace("{timestamp}", timestamp)

    os.makedirs("logs", exist_ok=True)
    with open(f"logs/preflight_{timestamp}.json", "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    print(f"[preflight] Audit log written: logs/preflight_{timestamp}.json")
    return data


def format_preflight_display(data: dict) -> str:
    lines = [f"\nPRE-FLIGHT CHECK - {time.strftime('%H:%M:%S IST')}", "-" * 60]
    for check in data.get("checks", []):
        status_icon = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}.get(
            check.get("status"), "[?]"
        )
        lines.append(
            f"{status_icon} {check.get('name', ''):<20} "
            f"{check.get('value', ''):<18} {check.get('status', '')}"
        )
        if check.get("note"):
            lines.append(f"    Note: {check['note']}")
    lines.append("-" * 60)
    lines.append(f"DECISION: {data.get('decision', 'UNKNOWN')}")
    if data.get("decision_reason"):
        lines.append(f"Reason:   {data['decision_reason']}")
    if data.get("mandatory_rth_at_min"):
        lines.append(f"RTH at:   T+{data['mandatory_rth_at_min']} min")
    if data.get("audit_entry"):
        lines.append(f"Audit:    {data['audit_entry']}")
    return "\n".join(lines)
