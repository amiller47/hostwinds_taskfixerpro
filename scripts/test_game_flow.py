#!/usr/bin/env python3
"""
Test game tracker with real video detections.
Processes a video file and outputs game state changes.
"""

import cv2
import json
import time
import sys
import os
import argparse
import requests
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_tracker import GameTracker
from scoring import calculate_score_from_detections, visualize_house_state

# Config
CONFIG_FILE = "/home/curl/curling_config.json"
CALIBRATION_FILE = "/home/curl/curling_vision/config/calibration.json"
OUTPUT_DIR = "/home/curl/curling_vision/test_output"

with open(CONFIG_FILE, "r") as f:
    CONFIG = json.load(f)

API_KEY = CONFIG["api_key"]
MODEL_ID = CONFIG["model_id"]

TEST_VIDEOS = {
    "far_crop": "/home/curl/Videos/sheet5FarCrop.mp4",
    "near_crop": "/home/curl/Videos/sheet5NearCrop.mp4",
    "far_full": "/home/curl/Videos/curling/cam1_20260330_194005.mp4",
    "near_full": "/home/curl/Videos/curling/cam2_20260330_194005.mp4",
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
            return response.json()
        else:
            return {"predictions": []}
    except Exception as e:
        print(f"API error: {e}")
        return {"predictions": []}


def get_calibration_for_video(video_name: str) -> dict:
    """Get appropriate calibration for video."""
    # Try loading from file
    try:
        cal = load_calibration(CALIBRATION_FILE)
        if "cropped" in video_name or "crop" in video_name:
            return cal.get("calibration_sets", {}).get("cropped", {})
        else:
            return cal.get("calibration_sets", {}).get("rtsp", {})
    except:
        pass

    # Fallback to hardcoded
    if "crop" in video_name:
        return {
            "near": {"button": (207, 375), "house_size": 400},
            "far": {"button": (222, 374), "house_size": 400},
        }
    else:
        return {
            "near": {"button": (349, 697), "house_size": 748},
            "far": {"button": (360, 596), "house_size": 748},
        }


def run_game_tracking(video_path: str, video_name: str, max_frames: int = 500, frame_skip: int = 10, start_frame: int = 0):
    """
    Run game tracking on a video.
    Processes every Nth frame and outputs state changes.
    """
    print(f"\n{'='*70}")
    print(f"GAME TRACKING TEST: {video_name}")
    print(f"{'='*70}")
    print(f"Video: {video_path}")
    print(f"Start frame: {start_frame}, Max frames: {max_frames}, Frame skip: {frame_skip}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Could not open {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Video: {total_frames} frames @ {fps:.1f} fps")

    # Skip to start frame
    if start_frame > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        print(f"Skipping to frame {start_frame} ({start_frame/fps:.1f}s)")

    # Initialize tracker
    calibration = get_calibration_for_video(video_name)
    print(f"Calibration: {calibration}")

    tracker = GameTracker(calibration, CONFIG)

    frame_idx = start_frame
    processed = 0
    start_time = time.time()
    last_state = None

    results = {
        "video": video_name,
        "start_frame": start_frame,
        "frames_processed": 0,
        "state_changes": [],
        "events": [],
        "final_state": None
    }

    print(f"\nProcessing...")

    while processed < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        if (frame_idx - start_frame) % frame_skip != 0:
            continue

        # Calculate video timestamp
        video_time = frame_idx / fps if fps > 0 else frame_idx * 0.1

        # Run inference
        result = infer_frame(frame)
        predictions = result.get("predictions", [])

        # Convert to detection format
        detections = []
        for pred in predictions:
            class_name = pred.get("class") or pred.get("name", "unknown")
            detections.append({
                "class": class_name,
                "x": pred.get("x", 0),
                "y": pred.get("y", 0),
                "confidence": pred.get("confidence", 0),
                "width": pred.get("width", 0),
                "height": pred.get("height", 0)
            })

        # Process through tracker
        tracker.process_detections(detections, "near" if "near" in video_name else "far", time.time())

        # Check for state changes
        current_state = tracker.get_state()
        if last_state is None or current_state["state"] != last_state["state"]:
            state_change = {
                "frame": frame_idx,
                "video_time": video_time,
                "state": current_state["state"],
                "throws": current_state["total_throws"],
                "end": current_state["end"]
            }
            results["state_changes"].append(state_change)
            print(f"  Frame {frame_idx} ({video_time:.1f}s): State -> {current_state['state']} | Throws: {current_state['total_throws']}")

        last_state = current_state
        processed += 1

        if processed % 20 == 0:
            print(f"  ...processed {processed} frames")

    cap.release()

    # Final state
    results["frames_processed"] = processed
    results["final_state"] = tracker.get_state()
    results["events"] = tracker.get_events()

    # Save results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"{OUTPUT_DIR}/game_tracking_{video_name}_{timestamp}.json"

    with open(result_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    elapsed = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Frames processed: {processed} in {elapsed:.1f}s ({processed/elapsed:.2f} fps)")
    print(f"State changes: {len(results['state_changes'])}")
    print(f"Events logged: {len(results['events'])}")

    print(f"\nFinal state:")
    for key, value in results["final_state"].items():
        print(f"  {key}: {value}")

    print(f"\nState changes:")
    for sc in results["state_changes"]:
        print(f"  {sc}")

    print(f"\nResults saved to: {result_file}")

    # Optionally save dashboard data
    if args.dashboard:
        dashboard_data = tracker.get_dashboard_data()
        with open(args.dashboard, "w") as f:
            json.dump(dashboard_data, f, indent=2)
        print(f"Dashboard data saved to: {args.dashboard}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Test game tracking on video")
    parser.add_argument("--video", "-v", help="Video name (far_crop, near_crop, far_full, near_full)")
    parser.add_argument("--frames", "-f", type=int, default=200, help="Max frames to process")
    parser.add_argument("--skip", "-s", type=int, default=10, help="Process every Nth frame")
    parser.add_argument("--start", type=int, default=0, help="Start frame")
    parser.add_argument("--dashboard", "-d", help="Output dashboard JSON to this file")
    args = parser.parse_args()

    print("GAME FLOW TRACKING TEST")
    print("=" * 70)

    if args.video:
        if args.video in TEST_VIDEOS:
            videos = [(args.video, TEST_VIDEOS[args.video])]
        else:
            videos = [("custom", args.video)]
    else:
        videos = [
            ("near_crop", TEST_VIDEOS["near_crop"]),
        ]

    for name, path in videos:
        if not os.path.exists(path):
            print(f"Skipping {name} — not found: {path}")
            continue
        run_game_tracking(path, name, max_frames=args.frames, frame_skip=args.skip, start_frame=args.start)


if __name__ == "__main__":
    main()