# Argus / SARGuard

Argus is an offline Search and Rescue drone AI demo built around SARGuard. It connects ArduPilot SITL on a laptop to Gemma running through `llama.cpp` on a Jetson Orin Nano. The bridge accepts English or Hindi mission commands, runs pre-flight checks, uploads MAVLink missions, processes simulated thermal detections, replans mid-flight, and generates a post-flight debrief.

## Project Layout

```text
Argus/
  .env
  requirements.txt
  bridge/
  overlay/
  jetson/
  logs/
  demo/
```

## Laptop Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Edit `.env` if your Jetson IP, ports, SITL endpoint, or home coordinates differ.

## Jetson Setup

Run once on the Jetson:

```bash
chmod +x jetson/setup_jetson.sh jetson/start_gemma.sh
./jetson/setup_jetson.sh
```

During the demo, keep Gemma running:

```bash
./jetson/start_gemma.sh
```

## Start ArduPilot SITL

Run this first in a dedicated terminal:

```bash
cd ~/ardupilot/ArduCopter
sim_vehicle.py \
  -v ArduCopter \
  --console \
  --map \
  -l 9.4142,76.5213,0,0 \
  --speedup=1 \
  --out=udp:127.0.0.1:14550 \
  --out=udp:127.0.0.1:14551
```

Port `14550` is for the bridge. Port `14551` is for QGroundControl.

## Run The Demo

Open QGroundControl and make sure it is connected to SITL, then run:

```bash
python -m bridge.bridge
```

Open the overlay at:

```text
http://localhost:5000
```

Demo command order:

```text
preflight
Search northern riverbank, start at 50 metres, expanding square pattern, avoid the concrete embankment on the west side
detect
Skip eastern zone, civilians on ground
rtl
debrief
```

You can also launch through:

```bash
chmod +x demo/run_demo.sh
./demo/run_demo.sh
```

## Component Tests

Gemma health:

```bash
python -c "from bridge.gemma_client import check_gemma_health; print('Gemma:', 'OK' if check_gemma_health() else 'UNREACHABLE')"
```

Overlay only:

```bash
python -c "from overlay.server import create_app; app = create_app(lambda: {'text':'test','type':'idle'}, lambda: {'battery_pct':95}); app.run(port=5000)"
```

SITL telemetry:

```bash
python -c "from bridge.telemetry import connect_sitl, start_telemetry_threads, get_state; import time; connect_sitl(); start_telemetry_threads(); time.sleep(3); print(get_state())"
```

## Notes

- Runtime is designed to be offline. Jetson setup requires internet only for installing dependencies and downloading the model.
- All prompt templates live in `bridge/prompts.py`.
- Mission upload uses `pymavlink` directly, not DroneKit.
- `.env` is ignored by git because it can contain machine-specific network settings.
