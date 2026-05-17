#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bridge.detection import format_detection_display, process_thermal_detection


if __name__ == "__main__":
    print("Injecting thermal detection...")
    data = process_thermal_detection()
    display = format_detection_display(data)
    print(display)
    print("\nDetection logged.")
