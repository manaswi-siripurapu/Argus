import json
import os
import random
import sys
import threading
import time

from dotenv import load_dotenv
from pymavlink import mavutil

load_dotenv()

SITL_UDP = os.getenv("SITL_UDP", "udp:127.0.0.1:14550")
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_INTERVAL = float(os.getenv("TELEMETRY_LOG_INTERVAL_SEC", "2"))

state = {
    "battery_pct": 100,
    "altitude_m": 0.0,
    "gps_fix": False,
    "esc_temp_c": 35,
    "wind_speed": 12,
    "wind_dir": 270,
    "motor1_a": 4.2,
    "motor2_a": 4.1,
    "motor3_a": 4.3,
    "motor4_a": 4.2,
    "lat": float(os.getenv("HOME_LAT", "9.4142")),
    "lon": float(os.getenv("HOME_LON", "76.5213")),
    "flight_mode": "STABILIZE",
    "armed": False,
    "current_wp": 0,
    "total_wp": 0,
    "airspeed_ms": 0.0,
    "groundspeed_ms": 0.0,
    "heading_deg": 0,
    "voltage_v": 16.8,
    "timestamp": time.time(),
}

_lock = threading.Lock()
_master = None
_threads_started = False


def connect_sitl() -> mavutil.mavlink_connection:
    global _master
    print(f"[telemetry] Connecting to SITL at {SITL_UDP}...")
    try:
        _master = mavutil.mavlink_connection(SITL_UDP)
        _master.wait_heartbeat(timeout=10)
    except Exception as exc:
        print(f"[telemetry] ERROR: SITL not running or no heartbeat at {SITL_UDP}: {exc}")
        sys.exit(1)
    print(
        f"[telemetry] SITL connected - system {_master.target_system}, "
        f"component {_master.target_component}"
    )
    return _master


def get_master():
    return _master


def _read_loop():
    while True:
        msg = _master.recv_match(blocking=True, timeout=1)
        if not msg:
            continue
        message_type = msg.get_type()
        with _lock:
            if message_type == "SYS_STATUS":
                state["battery_pct"] = msg.battery_remaining
                state["voltage_v"] = msg.voltage_battery / 1000.0
            elif message_type == "GLOBAL_POSITION_INT":
                state["altitude_m"] = msg.relative_alt / 1000.0
                state["lat"] = msg.lat / 1e7
                state["lon"] = msg.lon / 1e7
            elif message_type == "GPS_RAW_INT":
                state["gps_fix"] = msg.fix_type >= 3
            elif message_type == "VFR_HUD":
                state["airspeed_ms"] = msg.airspeed
                state["groundspeed_ms"] = msg.groundspeed
                state["heading_deg"] = msg.heading
            elif message_type == "HEARTBEAT":
                state["armed"] = bool(
                    msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                )
                mode_map = {
                    0: "STABILIZE",
                    2: "ALT_HOLD",
                    3: "AUTO",
                    4: "GUIDED",
                    5: "LOITER",
                    6: "RTL",
                    9: "LAND",
                }
                state["flight_mode"] = mode_map.get(msg.custom_mode, "UNKNOWN")
            elif message_type == "MISSION_CURRENT":
                state["current_wp"] = msg.seq
            elif message_type == "MISSION_COUNT":
                state["total_wp"] = msg.count
            elif message_type == "RC_CHANNELS":
                throttle_norm = max(0.0, min(1.0, msg.chan3_raw / 2000.0))
                base_current = throttle_norm * 8.0
                for index in range(1, 5):
                    state[f"motor{index}_a"] = round(
                        base_current + random.uniform(-0.3, 0.3), 2
                    )
                state["esc_temp_c"] = int(25 + throttle_norm * 30)
            state["timestamp"] = time.time()


def _log_loop():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, "flight_log.json")
    log_entries = []
    while True:
        time.sleep(LOG_INTERVAL)
        with _lock:
            entry = dict(state)
        log_entries.append(entry)
        with open(log_path, "w", encoding="utf-8") as handle:
            json.dump(log_entries, handle, indent=2)


def start_telemetry_threads():
    global _threads_started
    if _threads_started:
        return
    if _master is None:
        raise RuntimeError("connect_sitl() must be called before start_telemetry_threads().")
    threading.Thread(target=_read_loop, daemon=True).start()
    threading.Thread(target=_log_loop, daemon=True).start()
    _threads_started = True
    print("[telemetry] Reader and logger threads started")


def get_state() -> dict:
    with _lock:
        return dict(state)
