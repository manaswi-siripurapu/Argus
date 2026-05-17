import json
import os

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return None

load_dotenv()

JETSON_IP = os.getenv("JETSON_IP", "192.168.1.105")
GEMMA_PORT = os.getenv("JETSON_GEMMA_PORT", "8080")
MODEL_NAME = os.getenv("GEMMA_MODEL_NAME", "gemma")
MAX_TOKENS = int(os.getenv("GEMMA_MAX_TOKENS", "1024"))
TEMPERATURE = float(os.getenv("GEMMA_TEMPERATURE", "0.2"))
BASE_URL = f"http://{JETSON_IP}:{GEMMA_PORT}/v1/chat/completions"


def _env_true(name: str) -> bool:
    return os.getenv(name, "false").lower() in {"1", "true", "yes", "on"}


def _mock_gemma_mode() -> bool:
    return _env_true("MOCK_GEMMA_MODE") or _env_true("LAPTOP_DEMO_MODE")


def _base_url() -> str:
    host = os.getenv("JETSON_IP", JETSON_IP)
    port = os.getenv("JETSON_GEMMA_PORT", GEMMA_PORT)
    return f"http://{host}:{port}/v1/chat/completions"


def _health_url() -> str:
    host = os.getenv("JETSON_IP", JETSON_IP)
    port = os.getenv("JETSON_GEMMA_PORT", GEMMA_PORT)
    return f"http://{host}:{port}/health"


def call_gemma(
    system_prompt: str,
    user_message: str,
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
) -> str:
    if _mock_gemma_mode():
        return json.dumps(_demo_response(user_message), indent=2)
    if requests is None:
        raise RuntimeError("requests is not installed. Install requirements.txt or use --laptop-demo.")

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        response = requests.post(_base_url(), json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            f"Cannot reach Gemma server at {_base_url()}. Ensure llama.cpp is running."
        ) from exc
    except (KeyError, IndexError) as exc:
        raw = response.text if "response" in locals() else "<no response>"
        raise ValueError(f"Malformed Gemma response: {exc}\nRaw: {raw}") from exc


def parse_json_response(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def check_gemma_health() -> bool:
    if _mock_gemma_mode():
        return True
    if requests is None:
        return False
    try:
        response = requests.get(_health_url(), timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def _demo_response(user_message: str) -> dict:
    if "REPLAN INSTRUCTION:" in user_message:
        return {
            "replan_id": "REPLAN-001",
            "change_description": "Skip eastern zone, civilians on ground",
            "original_waypoints_remaining": 6,
            "cancelled_waypoints": [5, 6, 7],
            "new_waypoints": [
                {"lat": 9.4162, "lon": 76.5217, "alt": 45, "action": "search"},
                {"lat": 9.4156, "lon": 76.5224, "alt": 25, "action": "thermal_scan"},
                {"lat": 9.4142, "lon": 76.5213, "alt": 20, "action": "rtl"},
            ],
            "coverage_lost_pct": 28,
            "time_saved_min": 3,
            "new_estimated_completion_min": 7,
            "new_rth_trigger_min": 5,
            "battery_impact": "Now RTH at T+5 min instead of T+8 min",
            "operator_confirmation": "Understood. Skipping eastern zone. Continuing with safer western and central coverage. New RTH trigger: 5 minutes.",
        }
    if "DETECTION INPUT:" in user_message:
        return {
            "detection_id": "DET-0001",
            "frame_id": "0193",
            "detection_type": "THERMAL_HUMAN",
            "confidence_pct": 81,
            "thermal_temp_c": 37.2,
            "signature_dimensions_m": "0.6 x 1.4",
            "consistent_with": "Adult human",
            "gps_lat": 9.4156,
            "gps_lon": 76.5224,
            "altitude_at_capture_m": 50,
            "ground_team_message": "Air unit Alpha: possible victim detected at grid 156-224. Thermal signature 37.2C, adult human dimensions. Confidence 81%. Recommend ground team approach via north embankment road. Drone circling for confirmation.",
            "recommended_drone_action": "Descend to 20m and circle for visual confirmation",
            "timestamp": "LAPTOP-DEMO",
        }
    if "TELEMETRY SUMMARY:" in user_message:
        return {
            "mission_id": "SAR-0047",
            "debrief_timestamp": "LAPTOP-DEMO",
            "coverage_pct": 72,
            "flight_duration_min": 8.5,
            "detection_events": [
                {
                    "id": "DET-0001",
                    "type": "THERMAL_HUMAN",
                    "confidence_pct": 81,
                    "gps": "9.4156, 76.5224",
                    "outcome": "Referred to ground team",
                }
            ],
            "false_positives": 0,
            "battery_used_pct": 31,
            "battery_efficiency": "GOOD - 3.6% per minute (within 4% nominal)",
            "peak_esc_temp_c": 46,
            "motor_health": "NOMINAL - all motors within 0.3A of each other",
            "gps_dropouts": 0,
            "anomalies_detected": [],
            "maintenance_required": False,
            "maintenance_notes": "None. Drone is ready for next flight.",
            "next_mission_recommendation": "Complete eastern zone after ground team clears civilians. Recommend 06:30 launch for calmer wind.",
            "overall_assessment": "SUCCESSFUL - Search pattern executed, one medium-confidence victim detection referred to ground team.",
        }
    if "TELEMETRY ANOMALY:" in user_message:
        return {
            "anomaly_type": "ESC_OVERHEAT",
            "severity": "CRITICAL",
            "detected_value": "58C",
            "threshold": "55C",
            "recommended_action": "RTH",
            "action_urgency": "IMMEDIATE",
            "reason": "ESC temperature 58C exceeds critical threshold 55C. Continued flight risks ESC failure and motor loss. Autonomous RTH recommended.",
            "operator_message": "ESC overheating. Land and inspect motor 2 before next flight."
        }
    if "MISSION COMMAND:" in user_message:
        return {
            "decision": "go",
            "waypoints": [
                {"lat": 9.4142, "lon": 76.5213, "alt": 50, "action": "takeoff"},
                {"lat": 9.4147, "lon": 76.5213, "alt": 50, "action": "search"},
                {"lat": 9.4147, "lon": 76.5219, "alt": 50, "action": "search"},
                {"lat": 9.4153, "lon": 76.5219, "alt": 50, "action": "search"},
                {"lat": 9.4156, "lon": 76.5224, "alt": 30, "action": "thermal_scan"},
                {"lat": 9.4142, "lon": 76.5213, "alt": 20, "action": "rtl"},
            ],
            "estimated_time_min": 9,
            "battery_used_pct": 32,
            "coverage_km2": 0.62,
            "notes": "Expanding square over northern riverbank. Western embankment avoided with buffer and a lower thermal pass over vegetation.",
        }
    return {
        "checks": [
            {"name": "Battery", "value": "94%", "status": "PASS", "limit": ">30% for this mission", "note": ""},
            {"name": "Wind speed", "value": "12 km/h", "status": "PASS", "limit": "<35 km/h", "note": ""},
            {"name": "ESC temperature", "value": "35C", "status": "PASS", "limit": "<55C", "note": ""},
            {"name": "GPS fix", "value": "3D fix, 10 satellites", "status": "PASS", "limit": ">6 satellites", "note": ""},
            {"name": "DGCA zone", "value": "Green", "status": "PASS", "limit": "Green or Yellow with permission", "note": ""},
            {"name": "NOTAM", "value": "None active", "status": "PASS", "limit": "No active restrictions", "note": "Cached demo data"},
            {"name": "Geofence", "value": "Loaded", "status": "PASS", "limit": "Must be loaded", "note": ""},
            {"name": "Motor balance", "value": "All within 0.2A", "status": "PASS", "limit": "<0.5A imbalance", "note": ""},
        ],
        "decision": "GO",
        "decision_reason": "Laptop simulation reports all checks passed. Conditions are safe for the SAR demo mission.",
        "estimated_endurance_min": 18,
        "mandatory_rth_at_min": 13,
        "audit_entry": "PRE-FLIGHT-GO-{timestamp}",
    }
