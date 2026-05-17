$ErrorActionPreference = "Stop"

Write-Host "=== Argus / SARGuard Real Gemma + Simulated Drone ==="
Write-Host "Requires llama.cpp llama-server already running at http://127.0.0.1:8080"

python -m bridge.bridge --sim-drone --gemma-host 127.0.0.1 --gemma-port 8080
