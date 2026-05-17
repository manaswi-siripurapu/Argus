#!/bin/bash
set -e

echo "=== SARGuard Demo Launcher ==="

python3 -c "
from pymavlink import mavutil
import os, sys
target = os.getenv('SITL_UDP', 'udp:127.0.0.1:14550')
try:
    mav = mavutil.mavlink_connection(target)
    mav.wait_heartbeat(timeout=5)
    print('SITL OK')
except Exception as exc:
    print(f'ERROR: SITL not running at {target}. Start: sim_vehicle.py -v ArduCopter')
    sys.exit(1)
"

JETSON_IP=$(grep '^JETSON_IP=' .env | cut -d= -f2)
JETSON_GEMMA_PORT=$(grep '^JETSON_GEMMA_PORT=' .env | cut -d= -f2)
python3 -c "
import requests, sys
try:
    requests.get('http://${JETSON_IP}:${JETSON_GEMMA_PORT}/health', timeout=5).raise_for_status()
    print('Gemma OK')
except Exception:
    print('ERROR: Gemma unreachable at ${JETSON_IP}:${JETSON_GEMMA_PORT}')
    sys.exit(1)
"

echo "Opening overlay in browser..."
xdg-open http://localhost:5000 2>/dev/null || open http://localhost:5000 2>/dev/null || true

echo "Starting SARGuard bridge..."
python -m bridge.bridge "$@"
