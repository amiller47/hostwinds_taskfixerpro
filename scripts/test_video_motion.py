#!/usr/bin/env python3
"""Test motion detection with video file."""
import cv2
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_tracker import GameTracker

# Config
CONFIG_FILE = "/home/curl/curling_config.json"
CALIBRATION_FILE = "/home/curl/curling_vision/config/calibration.json"
VIDEO_FILE = "/home/curl/Videos/curling/cam2_20260330_194005.mp4"
API_KEY = ""
MODEL_ID = ""

def load_config():
    global API_KEY, MODEL_ID
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    API_KEY = config["api_key"]
    MODEL_ID = config["model_id"]
    return config

def infer_frame(frame):
    """Run inference on a single frame via REST API."""
    import requests
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    try:
        response = requests.post(
            f"https://detect.roboflow.com/{MODEL_ID}",
            params={"api_key": API_KEY},
            files={"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
            timeout=15
        )
        if response.status_code == 200:
            return response.json().get("predictions", [])
    except Exception as e:
        print(f"API error: {e}")
    return []

def main():
    print("Testing Motion Detection with Video")
    print("=" * 60)
    print(f"Video: {VIDEO_FILE}")
    print()
    
    # Load config and calibration
    config = load_config()
    with open(CALIBRATION_FILE) as f:
        calibration_data = json.load(f)
    
    # Use RTSP calibration for full videos
    calibration = calibration_data.get("calibration_sets", {}).get("rtsp", calibration_data)
    print(f"Calibration: near button = {calibration.get('near', {}).get('button')}")
    
    # Initialize tracker
    tracker = GameTracker(calibration, config)
    print(f"Motion detection enabled: {tracker.use_motion_detection}")
    print()
    
    # Open video
    cap = cv2.VideoCapture(VIDEO_FILE)
    if not cap.isOpened():
        print(f"Error: Could not open {VIDEO_FILE}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video: {total_frames} frames @ {fps:.1f} fps")
    print(f"Testing with first 100 frames (skip=5)")
    print()
    
    frame_idx = 0
    processed = 0
    start_time = time.time()
    
    state_log = []
    
    while processed < 100:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_idx += 1
        
        # Process every 5th frame
        if frame_idx % 5 != 0:
            continue
            
        # Run inference
        detections = infer_frame(frame)
        
        # Update tracker
        tracker.process_detections(detections, "near", time.time())
        
        # Log state changes
        state = tracker.get_state()
        state_log.append({
            "frame": frame_idx,
            "state": state["state"],
            "throws": state["total_throws"],
            "rocks": state["near_rocks"]
        })
        
        if len(state_log) < 2 or state_log[-2]["state"] != state["state"]:
            print(f"Frame {frame_idx}: {state['state']} | Rocks: {state['near_rocks']} | Throws: {state['total_throws']}")
        
        processed += 1
    
    cap.release()
    elapsed = time.time() - start_time
    
    print()
    print("=" * 60)
    print(f"Processed {processed} frames in {elapsed:.1f}s ({processed/elapsed:.2f} fps)")
    print()
    print("Final State:")
    final = tracker.get_state()
    print(f"  State: {final['state']}")
    print(f"  End: {final['end']}")
    print(f"  Throws: {final['total_throws']}")
    print(f"  Score: Red {final['scores']['team_red']} - Yellow {final['scores']['team_yellow']}")
    print()
    print("Events:")
    for event in tracker.events[-10:]:
        print(f"  {event['event']}: {event.get('details', {})}")
    
    print()
    print("Motion Detection Summary:")
    motion_events = [e for e in tracker.events if e['event'] in ('throw_started', 'false_throw', 'throw_complete')]
    print(f"  Throw starts detected: {len([e for e in motion_events if e['event'] == 'throw_started'])}")
    print(f"  False throws (no motion): {len([e for e in motion_events if e['event'] == 'false_throw'])}")
    print(f"  Throws completed: {len([e for e in motion_events if e['event'] == 'throw_complete'])}")

if __name__ == "__main__":
    main()