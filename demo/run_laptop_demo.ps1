$ErrorActionPreference = "Stop"

Write-Host "=== Argus / SARGuard Laptop Demo ==="
Write-Host "Starting fully simulated bridge. Open http://localhost:5000 for the overlay."

python -m bridge.bridge --laptop-demo
