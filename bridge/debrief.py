import json
import os
import time

from bridge.gemma_client import call_gemma, parse_json_response
from bridge.prompts import DEBRIEF_PROMPT, SYSTEM_PROMPT_BASE
from bridge.telemetry import get_state


def generate_debrief(log_path: str = "logs/flight_log.json") -> dict:
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"No telemetry log found at {log_path}")

    with open(log_path, encoding="utf-8") as handle:
        log_data = json.load(handle)

    summary = _summarise_log(log_data)
    state = get_state()
    system = SYSTEM_PROMPT_BASE.format(**state)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    user = (
        DEBRIEF_PROMPT.replace("{timestamp}", timestamp)
        + f"\n\nTELEMETRY SUMMARY:\n{json.dumps(summary, indent=2)}"
    )

    raw = call_gemma(system, user, temperature=0.1, max_tokens=1500)
    data = parse_json_response(raw)

    os.makedirs("logs", exist_ok=True)
    with open(f"logs/debrief_{timestamp}.json", "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    print(f"[debrief] Report saved: logs/debrief_{timestamp}.json")
    return data


def _summarise_log(entries: list) -> dict:
    if not entries:
        return {}
    batt_values = [entry["battery_pct"] for entry in entries]
    alt_values = [entry["altitude_m"] for entry in entries]
    esc_values = [entry["esc_temp_c"] for entry in entries]
    motor_imbalances = []
    for entry in entries:
        currents = [entry.get(f"motor{index}_a", 0) for index in range(1, 5)]
        if all(current > 0 for current in currents):
            motor_imbalances.append(max(currents) - min(currents))
    duration_min = round((entries[-1]["timestamp"] - entries[0]["timestamp"]) / 60, 1)
    return {
        "flight_duration_min": duration_min,
        "battery_start_pct": batt_values[0],
        "battery_end_pct": batt_values[-1],
        "battery_used_pct": batt_values[0] - batt_values[-1],
        "max_altitude_m": max(alt_values),
        "peak_esc_temp_c": max(esc_values),
        "avg_esc_temp_c": round(sum(esc_values) / len(esc_values), 1),
        "max_motor_imbalance_a": round(max(motor_imbalances), 2)
        if motor_imbalances
        else 0,
        "total_telemetry_entries": len(entries),
        "gps_dropouts": sum(1 for entry in entries if not entry.get("gps_fix", True)),
    }


def format_debrief_display(data: dict) -> str:
    lines = [f"\nPOST-FLIGHT DEBRIEF - {data.get('mission_id', 'SAR')}", "-" * 60]
    lines.append(f"Coverage achieved:    {data.get('coverage_pct', '?')}%")
    lines.append(f"Flight duration:      {data.get('flight_duration_min', '?')} min")
    lines.append(f"Battery used:         {data.get('battery_used_pct', '?')}%")
    lines.append(f"Battery efficiency:   {data.get('battery_efficiency', '?')}")
    lines.append(f"Peak ESC temp:        {data.get('peak_esc_temp_c', '?')}C")
    lines.append(f"Motor health:         {data.get('motor_health', '?')}")
    lines.append(f"GPS dropouts:         {data.get('gps_dropouts', 0)}")

    detections = data.get("detection_events", [])
    lines.append(f"\nDetection events:     {len(detections)}")
    for detection in detections:
        lines.append(
            f"  [{detection.get('id')}] {detection.get('type')} - "
            f"Confidence {detection.get('confidence_pct')}% - GPS {detection.get('gps')}"
        )

    anomalies = data.get("anomalies_detected", [])
    lines.append(f"Anomalies:            {len(anomalies) or 'None'}")

    maintenance_required = data.get("maintenance_required", False)
    maintenance = (
        "YES - " + data.get("maintenance_notes", "")
        if maintenance_required
        else "None"
    )
    lines.append(f"Maintenance needed:   {maintenance}")
    lines.append(f"\nNext mission:         {data.get('next_mission_recommendation', '')}")
    lines.append(f"\nAssessment:           {data.get('overall_assessment', '')}")
    return "\n".join(lines)
