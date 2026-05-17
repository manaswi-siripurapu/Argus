import time
import os

try:
    from pymavlink import mavutil
except ImportError:
    mavutil = None

from bridge.telemetry import get_master, set_sim_mission, sim_land, sim_rtl


def _env_true(name: str) -> bool:
    return os.getenv(name, "false").lower() in {"1", "true", "yes", "on"}


def _sim_drone_mode() -> bool:
    return _env_true("SIM_DRONE_MODE") or _env_true("LAPTOP_DEMO_MODE")


def _require_master():
    master = get_master()
    if master is None:
        raise RuntimeError("SITL is not connected. Run connect_sitl() first.")
    return master


def arm_and_takeoff(alt_m: float = 50.0):
    if _sim_drone_mode():
        print(f"[mission] SIM takeoff to {alt_m}m commanded")
        return True
    master = _require_master()
    master.set_mode("GUIDED")
    time.sleep(1)

    master.arducopter_arm()
    master.motors_armed_wait()
    print("[mission] Armed")

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        alt_m,
    )
    print(f"[mission] Takeoff to {alt_m}m commanded")

    start = time.time()
    while time.time() - start < 30:
        msg = master.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=2)
        if msg and (msg.relative_alt / 1000.0) >= (alt_m - 1):
            print(f"[mission] Reached {alt_m}m")
            return True
        time.sleep(0.5)
    print("[mission] WARNING: Takeoff timeout")
    return False


def upload_mission(waypoints: list) -> bool:
    if _sim_drone_mode():
        set_sim_mission(waypoints)
        print(f"[mission] SIM mission accepted: {len(waypoints)} waypoints")
        print("[mission] SIM AUTO mode - virtual drone following mission")
        return True

    master = _require_master()
    if not waypoints:
        print("[mission] No waypoints to upload")
        return False

    master.mav.mission_clear_all_send(master.target_system, master.target_component)
    time.sleep(0.5)

    count = len(waypoints)
    master.mav.mission_count_send(
        master.target_system,
        master.target_component,
        count,
        mavutil.mavlink.MAV_MISSION_TYPE_MISSION,
    )

    action_map = {
        "takeoff": mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        "search": mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        "thermal_scan": mavutil.mavlink.MAV_CMD_NAV_LOITER_TIME,
        "photo": mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        "hover": mavutil.mavlink.MAV_CMD_NAV_LOITER_TIME,
        "rtl": mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
    }

    for index, waypoint in enumerate(waypoints):
        msg = master.recv_match(
            type=["MISSION_REQUEST", "MISSION_REQUEST_INT"], blocking=True, timeout=5
        )
        if not msg:
            print(f"[mission] No MISSION_REQUEST for seq {index}")
            return False

        action = waypoint.get("action", "search")
        command = action_map.get(action, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT)
        param1 = 10.0 if action == "thermal_scan" else 5.0 if action == "hover" else 0.0
        master.mav.mission_item_int_send(
            master.target_system,
            master.target_component,
            index,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            command,
            0,
            1,
            param1,
            0,
            0,
            0,
            int(float(waypoint["lat"]) * 1e7),
            int(float(waypoint["lon"]) * 1e7),
            float(waypoint["alt"]),
        )
        time.sleep(0.05)

    ack = master.recv_match(type="MISSION_ACK", blocking=True, timeout=5)
    if ack and ack.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
        print(f"[mission] Mission accepted: {count} waypoints")
        master.set_mode("AUTO")
        print("[mission] AUTO mode - drone following mission")
        return True

    print(f"[mission] Mission REJECTED: {ack}")
    return False


def rtl():
    if _sim_drone_mode():
        sim_rtl()
        print("[mission] SIM RTL commanded")
        return
    master = _require_master()
    master.set_mode("RTL")
    print("[mission] RTL commanded")


def land():
    if _sim_drone_mode():
        sim_land()
        print("[mission] SIM LAND commanded")
        return
    master = _require_master()
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    print("[mission] LAND commanded")
