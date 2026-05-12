#!/usr/bin/env python3
import subprocess
import sys
import json
import time

# Run 300 frames starting at frame 1000 (multiple throws)
result = subprocess.run(
    ["/home/curl/timer_env/bin/python3", "scripts/realtime_dashboard.py", 
     "--video", "far_full", "--start", "1000", "--frames", "300"],
    cwd="/home/curl/curling_vision",
    capture_output=True,
    text=True,
    timeout=600
)
print("=== PROCESSING COMPLETE ===")
print(f"Return code: {result.returncode}")

# Analyze the output
try:
    with open('/home/curl/curling_vision/dashboard_data.json') as f:
        data = json.load(f)
    
    far_dets = data.get('current_raw_detections', {}).get('far', [])
    far_button = data.get('locked_button', {}).get('far', [360, 596])
    far_house = data.get('locked_house_size', {}).get('far', 540)
    
    print(f"\n=== ANALYSIS ===")
    print(f"Button: {far_button}")
    print(f"House Y range: {far_button[1] - far_house//2} to {far_button[1] + far_house//2}")
    print(f"Total detections: {len(far_dets)}")
    
    # Count by category
    rocks_in_house = 0
    rocks_hack = 0
    rocks_above = 0
    
    for det in far_dets:
        name, x, y, conf = det
        if 'rock' in name.lower():
            y_min = far_button[1] - far_house//2
            y_max = far_button[1] + far_house//2
            if y_min <= y <= y_max:
                rocks_in_house += 1
            elif y > 1000:
                rocks_hack += 1
            else:
                rocks_above += 1
    
    print(f"\nRocks in house: {rocks_in_house}")
    print(f"Rocks in hack (Y>1000): {rocks_hack}")
    print(f"Rocks above house (Y<200): {rocks_above}")
    
except Exception as e:
    print(f"Error analyzing: {e}")