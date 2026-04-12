#!/usr/bin/env python3
"""
Real-time game tracking with dashboard updates.
Processes video and writes to dashboard_data.json for the web dashboard.
"""

import cv2
import json
import time
import sys
import os
import argparse
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_tracker import GameTracker
from video_source import open_video_source, detect_source_type
from bingo import BingoGame, BINGO_EVENTS
from bingo_events import detect_bingo_events

# Config
CONFIG_FILE = "/home/curl/curling_config.json"
CALIBRATION_FILE = "/home/curl/curling_vision/config/calibration.json"
DASHBOARD_FILE = "/home/curl/curling_vision/dashboard_data.json"

with open(CONFIG_FILE, "r") as f:
    CONFIG = json.load(f)

API_KEY = CONFIG["api_key"]
MODEL_ID = CONFIG["model_id"]

# Hostwinds upload
HOSTWINDS_URL = "https://taskfixerpro.com/curling_update.php"
UPLOAD_INTERVAL = 3.0  # seconds
_last_upload = 0.0
_upload_enabled = False

# Bingo game
_bingo_game = BingoGame()
_previous_state = None

WIDE_MODEL_ID = CONFIG.get("roboflow", {}).get("wide_model_id", "fcc-instance-detection/7")

TEST_VIDEOS = {
    "far_crop": "/home/curl/Videos/sheet5FarCrop.mp4",
    "near_crop": "/home/curl/Videos/sheet5NearCrop.mp4",
    "far_full": "/home/curl/Videos/curling/cam1_20260330_194005.mp4",
    "near_full": "/home/curl/Videos/curling/cam2_20260330_194005.mp4",
    "wide_full": "/home/curl/Videos/curling/cam3_20260330_194005.mp4",
}


def infer_frame(frame, api_key=API_KEY, model_id=MODEL_ID):
    """Run inference on a single frame via REST API."""
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    try:
        response = requests.post(
            f"https://detect.roboflow.com/{model_id}",
            params={"api_key": api_key},
            files={"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
            timeout=15
        )
        if response.status_code == 200:
            return response.json().get("predictions", [])
    except Exception as e:
        print(f"API error: {e}")
    return []


def infer_frame_wide(frame, api_key=API_KEY, model_id=WIDE_MODEL_ID):
    """Run inference on wide camera frame via REST API."""
    return infer_frame(frame, api_key, model_id)


def send_to_hostwinds(data):
    """Upload game state to Hostwinds dashboard."""
    global _last_upload
    if not _upload_enabled:
        return False
    try:
        response = requests.post(HOSTWINDS_URL, json=data, timeout=5)
        if response.status_code == 200:
            _last_upload = time.time()
            print(f"Uploaded to Hostwinds")
            return True
    except Exception as e:
        print(f"Hostwinds upload error: {e}")
    return False

def update_dashboard(tracker, detections=None, frame=None):
    """Write current state to dashboard file."""
    data = tracker.get_dashboard_data()

    # Add raw detections
    if detections:
        data["current_raw_detections"] = detections

    # Write to file
    with open(DASHBOARD_FILE, "w") as f:
        json.dump(data, f, indent=2)

    # Upload to Hostwinds every UPLOAD_INTERVAL seconds
    if time.time() - _last_upload >= UPLOAD_INTERVAL:
        send_to_hostwinds(data)


def main():
    parser = argparse.ArgumentParser(description="Real-time game tracking with dashboard")
    parser.add_argument("--video", "-v", required=True, help="Video source: local file, RTSP URL, YouTube URL, or usb:N")
    parser.add_argument("--frames", "-f", type=int, default=0, help="Max frames (0 = all)")
    parser.add_argument("--skip", "-s", type=int, default=10, help="Process every Nth frame")
    parser.add_argument("--start", type=int, default=0, help="Start frame")
    parser.add_argument("--wide", "-w", action="store_true", help="Process both near and wide cameras")
    parser.add_argument("--upload", "-u", action="store_true", help="Upload to Hostwinds dashboard")
    args = parser.parse_args()
    
    print("REAL-TIME GAME TRACKING WITH DASHBOARD")
    print("=" * 60)

    # Load calibration
    with open(CALIBRATION_FILE) as f:
        calibration_data = json.load(f)

    # Use RTSP calibration for full videos
    cal_key = "rtsp" if "full" in args.video else "cropped"
    calibration = calibration_data.get("calibration_sets", {}).get(cal_key, calibration_data)

    print(f"Calibration: {cal_key}")
    print(f"Near button: {calibration.get('near', {}).get('button')}")
    print(f"Far button: {calibration.get('far', {}).get('button')}")

    # Enable Hostwinds upload if requested
    global _upload_enabled
    _upload_enabled = args.upload
    if args.upload:
        print(f"Hostwinds upload enabled: {HOSTWINDS_URL}")

    # Wide camera calibration
    if args.wide and "wide" in calibration:
        print(f"Wide button: {calibration.get('wide', {}).get('button')}")

    # Initialize tracker
    tracker = GameTracker(calibration, CONFIG)

    # Video setup - use flexible source handler
    video_source = TEST_VIDEOS.get(args.video, args.video)

    try:
        cap, source_type = open_video_source(video_source, verbose=True)
    except Exception as e:
        print(f"Error opening video source: {e}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames > 0:
        duration = total_frames / fps if fps > 0 else 0
        print(f"Duration: {duration:.1f}s")

    # Wide video setup (if --wide flag)
    cap_wide = None
    if args.wide:
        wide_name = args.video.replace("near", "wide").replace("far", "wide")
        if "wide" not in wide_name:
            wide_name = "wide_" + wide_name if not wide_name.startswith("wide") else wide_name
        wide_path = TEST_VIDEOS.get(wide_name, wide_name)
        if os.path.exists(wide_path):
            cap_wide = cv2.VideoCapture(wide_path)
            print(f"Wide video: {wide_path}")
        else:
            print(f"Wide video not found: {wide_path}, using single-camera mode")
            args.wide = False

    # Skip to start
    if args.start > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, args.start)
        if cap_wide:
            cap_wide.set(cv2.CAP_PROP_POS_FRAMES, args.start)
        print(f"Starting at frame {args.start}")

    # Initialize dashboard
    update_dashboard(tracker)
    print(f"Dashboard initialized: {DASHBOARD_FILE}")
    print()
    print("Processing... (Dashboard updates every 5 frames)")
    print()

    last_state = None
    frame_idx = args.start
    processed = 0

    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        # Skip frames
        if frame_idx % args.skip != 0:
            continue

        # Max frames
        if args.frames > 0 and processed >= args.frames:
            break

        # Run inference on main camera
        detections = infer_frame(frame)

        # Determine camera
        camera = "near" if "near" in args.video else "far"

        # Update tracker with main camera
        tracker.process_detections(detections, camera, time.time())

        # Process wide camera if available
        wide_detections = []
        if cap_wide:
            ret_wide, frame_wide = cap_wide.read()
            if ret_wide:
                wide_detections = infer_frame_wide(frame_wide)
                # Wide camera sees both houses - can be used for scoring validation
                tracker.process_wide_detections(wide_detections, time.time())

        # Get current state
        current_state = tracker.get_state()

        # Log state changes
        if last_state is None or current_state["state"] != last_state["state"]:
            print(f"Frame {frame_idx}: {current_state['state']} | Throws: {current_state['total_throws']}")

        # Detect bingo events from state changes
        global _previous_state
        if last_state and current_state["state"] != last_state["state"]:
            bingo_events = detect_bingo_events(last_state, current_state, detections)
            for event_id in bingo_events:
                winners = _bingo_game.mark_event(event_id)
                print(f"Bingo event: {event_id} {'- WINNER!' if winners else ''}")
        _previous_state = current_state

        # Update dashboard every 5 frames
        if processed % 5 == 0:
            det_list = [[d["class"], d["x"], d["y"], d["confidence"]] for d in detections]
            wide_list = [[d["class"], d["x"], d["y"], d["confidence"]] for d in wide_detections] if wide_detections else []
            update_dashboard(tracker, {camera: det_list, "wide": wide_list})

        last_state = current_state
        processed += 1

    cap.release()
    if cap_wide:
        cap_wide.release()

    # Final dashboard update
    update_dashboard(tracker)

    elapsed = time.time() - start_time
    print(f"\nProcessed {processed} frames in {elapsed:.1f}s ({processed/elapsed:.2f} fps)")
    print(f"Final state: {tracker.get_state()['state']}")
    print(f"Total throws: {tracker.get_state()['total_throws']}")
    print(f"\nDashboard at: http://localhost:5000/")


if __name__ == "__main__":
    main()