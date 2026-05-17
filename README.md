# Argus - SARGuard

Argus is an offline Search and Rescue drone AI demo built around SARGuard. It accepts English or Hindi mission commands, runs pre-flight checks, monitors simulated telemetry, detects a synthetic thermal victim, replans mid-flight, and generates a post-flight debrief.

For the hackathon laptop demo, use **real local Gemma through `llama.cpp`** and simulate only the drone/SITL layer. This keeps the important AI part real while avoiding Jetson, ArduPilot, and QGroundControl setup during judging.

## Demo Modes

| Mode | Command | Gemma | Drone/SITL | Best use |
|---|---|---|---|---|
| Recommended laptop demo | `--sim-drone --gemma-host 127.0.0.1 --gemma-port 8080` | Real local `llama.cpp` server | Simulated | Hackathon presentation |
| Full system | no simulation flags | Jetson/remote `llama.cpp` server | Real ArduPilot SITL | End-to-end integration |
| Fallback mock demo | `--laptop-demo` | Hardcoded mock responses | Simulated | Emergency no-model fallback |

## Project Layout

```text
Argus/
  .env
  requirements.txt
  requirements-laptop-demo.txt
  bridge/
  overlay/
  jetson/
  logs/
  demo/
```

## 1. Install Laptop Dependencies

PowerShell:

```powershell
cd "C:\Users\manas\OneDrive\Desktop\Argus"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-laptop-demo.txt
```

For the full SITL/voice stack later:

```powershell
pip install -r requirements.txt
```

## 2. Start Gemma Locally

Start a `llama.cpp` OpenAI-compatible server on the laptop. Example:

```powershell
cd C:\path\to\llama.cpp
.\build\bin\Release\llama-server.exe `
  -m C:\path\to\models\gemma-4-4b-it-Q4_K_M.gguf `
  --host 127.0.0.1 `
  --port 8080 `
  --ctx-size 8192 `
  --threads 8
```

If your executable or model path is different, change those two paths. Keep the host and port as:

```text
127.0.0.1:8080
```

Verify Gemma is running:

```text
http://127.0.0.1:8080/health
```

You should see a health response from `llama.cpp`.

## 3. Run Argus With Real Gemma + Simulated Drone

Open a second PowerShell terminal:

```powershell
cd "C:\Users\manas\OneDrive\Desktop\Argus"
.\.venv\Scripts\Activate.ps1
python -m bridge.bridge --sim-drone --gemma-host 127.0.0.1 --gemma-port 8080
```

Or use the launcher:

```powershell
.\demo\run_local_gemma_sim_drone.ps1
```

Open the dashboard:

```text
http://127.0.0.1:5000
```

## 4. Demo From The Dashboard

Use the browser dashboard controls. You do not need to type in the terminal.

Recommended flow:

1. Click `Preflight`
2. Send the mission command:

```text
Search northern riverbank, start at 50 metres, expanding square pattern, avoid the concrete embankment on the west side
```

3. Click `Detect`
4. Click `Replan`
5. Click `RTL`
6. Click `Debrief`

The dashboard shows:

- AI output from Gemma
- Simulated telemetry
- Moving drone marker
- Home point
- Riverbank and embankment context
- Thermal detection marker

## What To Say During The Demo

Use this explanation if asked what is real versus simulated:

```text
For the laptop demo, the drone physics and telemetry are simulated so we do not need a Jetson, ArduPilot, or QGroundControl at the booth. The AI layer is real: the dashboard sends natural-language commands to a local Gemma model running through llama.cpp's OpenAI-compatible API. The same bridge can also connect to a Jetson-hosted Gemma server and ArduPilot SITL for the full setup.
```

## Fallback Mock Demo

Use this only if Gemma is not available. It uses hardcoded mock AI responses.

```powershell
cd "C:\Users\manas\OneDrive\Desktop\Argus"
.\.venv\Scripts\Activate.ps1
python -m bridge.bridge --laptop-demo
```

Or:

```powershell
.\demo\run_laptop_demo.ps1
```

Open:

```text
http://127.0.0.1:5000
```

## Full SITL + Jetson Mode

Use this after the laptop demo is working.

On the Jetson, run once:

```bash
chmod +x jetson/setup_jetson.sh jetson/start_gemma.sh
./jetson/setup_jetson.sh
```

Start Gemma on the Jetson:

```bash
./jetson/start_gemma.sh
```

Start ArduPilot SITL:

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

Edit `.env` so `JETSON_IP` points to the Jetson, then run:

```powershell
python -m bridge.bridge
```

Open:

```text
http://127.0.0.1:5000
```

## Component Tests

Gemma health:

```powershell
python -c "from bridge.gemma_client import check_gemma_health; print('Gemma:', 'OK' if check_gemma_health() else 'UNREACHABLE')"
```

Overlay only:

```powershell
python -c "from overlay.server import create_app; app = create_app(lambda: {'text':'test','type':'idle'}, lambda: {'battery_pct':95}); app.run(port=5000)"
```

Simulated telemetry:

```powershell
$env:SIM_DRONE_MODE='true'
python -c "from bridge.telemetry import start_sim_telemetry_threads, get_state; import time; start_sim_telemetry_threads(); time.sleep(2); print(get_state())"
```

## Notes

- `--sim-drone` simulates only the drone layer; Gemma is still real.
- `--laptop-demo` mocks Gemma and should be treated as a fallback only.
- All prompt templates live in `bridge/prompts.py`.
- Mission upload uses `pymavlink` directly, not DroneKit.
- `.env` is ignored by git because it can contain machine-specific network settings.
