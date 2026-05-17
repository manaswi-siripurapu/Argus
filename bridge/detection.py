import json
import os
import time

from bridge.gemma_client import call_gemma, parse_json_response
from bridge.prompts import DETECTION_PROMPT, SYSTEM_PROMPT_BASE
from bridge.telemetry import get_state

DEMO_DETECTIONS = [
    {
        "frame_id": "0193",
        "thermal_temp_c": 37.2,
        "blob_dimensions_m": "0.6 x 1.4",
        "background_temp_c": 28.1,
        "gps_lat": 9.4156,
        "gps_lon": 76.5224,
        "altitude_m": 50,
        "description": "Warm elongated blob, adult human dimensions, flood water background",
    }
]

_detection_counter = 0


def process_thermal_detection(detection_data: dict | None = None) -> dict:
    global _detection_counter
    if detection_data is None:
        detection_data = DEMO_DETECTIONS[_detection_counter % len(DEMO_DETECTIONS)]
        _detection_counter += 1

    state = get_state()
    system = SYSTEM_PROMPT_BASE.format(**state)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    user = (
        DETECTION_PROMPT.replace("{timestamp}", timestamp)
        + f"\n\nDETECTION INPUT:\n{json.dumps(detection_data, indent=2)}"
    )

    raw = call_gemma(system, user, temperature=0.1)
    data = parse_json_response(raw)

    os.makedirs("logs", exist_ok=True)
    with open(f"logs/detection_{timestamp}.json", "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    return data


def format_detection_display(data: dict) -> str:
    lines = [f"\nDETECTION EVENT - {data.get('detection_id', 'DET')}", "-" * 60]
    lines.append(f"Type:           {data.get('detection_type')}")
    lines.append(f"Confidence:     {data.get('confidence_pct')}%")
    lines.append(f"Temperature:    {data.get('thermal_temp_c')}C")
    lines.append(f"Signature:      {data.get('consistent_with')}")
    lines.append(f"GPS:            {data.get('gps_lat')}, {data.get('gps_lon')}")
    lines.append("\nGROUND TEAM MESSAGE:")
    lines.append(f"  {data.get('ground_team_message')}")
    lines.append(f"\nDRONE ACTION:   {data.get('recommended_drone_action')}")
    return "\n".join(lines)
