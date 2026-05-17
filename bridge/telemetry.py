import json
import os
import random
import sys
import threading
import time

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return None

try:
    from pymavlink import mavutil
except ImportError:
    mavutil = None

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
_sim_active = False
_sim_rtl = False
_sim_land = False
_sim_waypoints = []
_sim_start_time = None


def connect_sitl():
    global _master
    if mavutil is None:
        print("[telemetry] ERROR: pymavlink is not installed. Use --laptop-demo or install requirements.")
        sys.exit(1)
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


def start_sim_telemetry_threads():
    global _threads_started
    if _threads_started:
        return
    with _lock:
        state.update(
            {
                "battery_pct": 94,
                "altitude_m": 0.0,
                "gps_fix": True,
                "esc_temp_c": 35,
                "flight_mode": "GUIDED",
                "armed": False,
                "airspeed_ms": 0.0,
                "groundspeed_ms": 0.0,
                "current_wp": 0,
                "total_wp": 0,
                "timestamp": time.time(),
            }
        )
    threading.Thread(target=_sim_loop, daemon=True).start()
    threading.Thread(target=_log_loop, daemon=True).start()
    _threads_started = True
    print("[telemetry] Laptop simulation telemetry started")


def set_sim_mission(waypoints: list):
    global _sim_active, _sim_rtl, _sim_land, _sim_waypoints, _sim_start_time
    with _lock:
        _sim_waypoints = list(waypoints)
        _sim_active = True
        _sim_rtl = False
        _sim_land = False
        _sim_start_time = time.time()
        state["armed"] = True
        state["flight_mode"] = "AUTO"
        state["current_wp"] = 0
        state["total_wp"] = len(_sim_waypoints)
        state["airspeed_ms"] = 8.0
        state["groundspeed_ms"] = 8.0


def sim_rtl():
    global _sim_active, _sim_rtl
    with _lock:
        _sim_active = True
        _sim_rtl = True
        state["flight_mode"] = "RTL"


def sim_land():
    global _sim_active, _sim_land
    with _lock:
        _sim_active = True
        _sim_land = True
        state["flight_mode"] = "LAND"


def _sim_loop():
    global _sim_active
    while True:
        time.sleep(1)
        with _lock:
            now = time.time()
            if _sim_active and _sim_start_time:
                elapsed = now - _sim_start_time
                if _sim_rtl:
                    state["altitude_m"] = max(0.0, state["altitude_m"] - 5.5)
                    state["lat"] += (float(os.getenv("HOME_LAT", "9.4142")) - state["lat"]) * 0.22
                    state["lon"] += (float(os.getenv("HOME_LON", "76.5213")) - state["lon"]) * 0.22
                    if state["altitude_m"] <= 0.2:
                        state["armed"] = False
                        _sim_active = False
                elif _sim_land:
                    state["altitude_m"] = max(0.0, state["altitude_m"] - 6.0)
                    if state["altitude_m"] <= 0.2:
                        state["armed"] = False
                        _sim_active = False
                else:
                    waypoint_index = min(int(elapsed // 5), max(len(_sim_waypoints) - 1, 0))
                    state["current_wp"] = waypoint_index + 1 if _sim_waypoints else 0
                    if _sim_waypoints:
                        target = _sim_waypoints[waypoint_index]
                        state["lat"] += (float(target["lat"]) - state["lat"]) * 0.18
                        state["lon"] += (float(target["lon"]) - state["lon"]) * 0.18
                        target_alt = float(target["alt"])
                        state["altitude_m"] += (target_alt - state["altitude_m"]) * 0.2
                        if target.get("action") == "rtl" and elapsed > 5:
                            state["flight_mode"] = "RTL"
                    if elapsed > max(len(_sim_waypoints), 1) * 5 + 8:
                        state["flight_mode"] = "RTL"
                        state["altitude_m"] = max(0.0, state["altitude_m"] - 4.0)
                state["battery_pct"] = max(22, state["battery_pct"] - 1)
                state["esc_temp_c"] = min(48, state["esc_temp_c"] + (1 if state["armed"] else 0))
                state["motor1_a"] = round(4.3 + random.uniform(-0.2, 0.2), 2)
                state["motor2_a"] = round(4.2 + random.uniform(-0.2, 0.2), 2)
                state["motor3_a"] = round(4.4 + random.uniform(-0.2, 0.2), 2)
                state["motor4_a"] = round(4.3 + random.uniform(-0.2, 0.2), 2)
            state["timestamp"] = now


def get_state() -> dict:
    with _lock:
        return dict(state)
