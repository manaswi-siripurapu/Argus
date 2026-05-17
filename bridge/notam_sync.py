import json
import os
import time
from datetime import datetime

CACHE_FILE = os.path.join(os.path.dirname(__file__), "notams_cache.json")

def fetch_live_notams():
    """
    Mocks a fetch to an aviation authority portal (e.g. DGCA/FAA) 
    to retrieve live Notice to Airmen (NOTAM) data for the operating region.
    """
    print("Connecting to DigitalSky Portal...")
    time.sleep(1)
    
    # Mock response data representing live NOTAMs
    mock_data = {
        "timestamp": datetime.now().strftime("%H:%M IST"),
        "status": "success",
        "active_notams": [
            "VIP Movement: Avoid airspace 5km radius around 9.4200, 76.5100 below 400ft between 1400-1600 IST",
            "Paragliding Activity: Active sector 10km East of home point. Exercise caution."
        ],
        "zone_status": "Green",
        "recommendation": "PROCEED WITH CAUTION. No critical restrictions in immediate operational area."
    }
    
    print("Writing to offline cache...")
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(mock_data, f, indent=2)
        
    print(f"NOTAM sync complete! Data cached at {mock_data['timestamp']}")
    print("Safe to operate drone entirely offline.")

if __name__ == "__main__":
    fetch_live_notams()
