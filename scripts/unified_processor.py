#!/usr/bin/env python3
"""
Unified curling vision processor.
Processes near/far/wide cameras and tracks game state.
"""

import cv2
import json
import time
import sys
import os
import argparse
import requests
import threading
from collections import defaultdict
from datetime import datetime
from queue import Queue

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

# Video sources
VIDEO_SOURCES = {
    "near_crop": "/home/curl/Videos/sheet5NearCrop.mp4",
    "far_crop": "/home/curl/Videos/sheet5FarCrop.mp4",
    "near_full": "/home/curl/Videos/curling/cam2_20260330_194005.mp4",
    "far_full": "/home/curl/Videos/curling/cam1_20260330_194005.mp4",
    "wide_full": "/home/curl/Videos/curling/cam3_20260330_194005.mp4",
}


class CameraProcessor:
    """Process a single camera feed."""

    def __init__(self, name: str, video_path: str, calibration: dict, api_key: str, model_id: str):
        self.name = name
        self.video_path = video_path
        self.calibration = calibration
        self.api_key = api_key
        self.model_id = model_id

        self.cap = None
        self.frame_queue = Queue(maxsize=10)
        self.running = False
        self.latest_detections = []
        self.frame_count = 0

    def start(self):
        """Start processing."""
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print(f"[{self.name}] ERROR: Could not open {self.video_path}")
            return False

        self.running = True
        return True

    def stop(self):
        """Stop processing."""
        self.running = False
        if self.cap:
            self.cap.release()

    def process_frame(self) -> dict:
        """Process a single frame and return detections."""
        if not self.cap or not self.cap.isOpened():
            return {"error": "Video not open"}

        ret, frame = self.cap.read()
        if not ret:
            return {"error": "End of video"}

        self.frame_count += 1

        # Encode frame for API
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

        try:
            response = requests.post(
                f"https://detect.roboflow.com/{self.model_id}",
                params={"api_key": self.api_key},
                files={"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
                timeout=15
            )
            if response.status_code == 200:
                result = response.json()
                predictions = result.get("predictions", [])
                self.latest_detections = predictions
                return {"predictions": predictions, "frame": self.frame_count}
            else:
                return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_button_position(self) -> tuple:
        """Get button position from calibration."""
        return self.calibration.get("button", (0, 0))

    def get_house_radius(self) -> float:
        """Get house radius from calibration."""
        house_size = self.calibration.get("house_size")
        if house_size is None:
            return 200.0  # Default for cropped videos
        return house_size / 2


class UnifiedGameProcessor:
    """Process all cameras and track game state."""

    def __init__(self, calibration: dict, config: dict):
        self.calibration = calibration
        self.config = config

        # Create game tracker
        self.game_tracker = GameTracker(calibration, config)

        # Camera processors
        self.processors = {}

        # State
        self.running = False
        self.frame_count = 0

    def add_camera(self, name: str, video_path: str):
        """Add a camera processor."""
        # Determine calibration key
        cal_key = "near" if "near" in name else "far"

        # Get calibration set based on video type
        cal_set = "cropped" if "crop" in name else "rtsp"
        cam_cal = self.calibration.get("calibration_sets", {}).get(cal_set, {}).get(cal_key, {})

        if not cam_cal:
            # Fallback
            cam_cal = {"button": (320, 240), "house_size": 400}

        processor = CameraProcessor(name, video_path, cam_cal, API_KEY, MODEL_ID)
        self.processors[name] = processor

    def start(self):
        """Start all cameras."""
        for name, proc in self.processors.items():
            if not proc.start():
                print(f"Failed to start {name}")
                return False

        self.running = True
        return True

    def stop(self):
        """Stop all cameras."""
        for proc in self.processors.values():
            proc.stop()
        self.running = False

    def process_frame(self, skip: int = 10) -> dict:
        """Process one frame from each camera (with skip)."""
        results = {}

        for name, proc in self.processors.items():
            # Skip frames
            for _ in range(skip - 1):
                proc.cap.read()

            result = proc.process_frame()
            results[name] = result

            if "predictions" in result:
                # Process through game tracker
                camera_key = "near" if "near" in name else "far"
                self.game_tracker.process_detections(
                    result["predictions"],
                    camera_key,
                    time.time()
                )

        self.frame_count += 1
        return results

    def get_state(self) -> dict:
        """Get current game state."""
        return self.game_tracker.get_state()

    def get_house_state(self, camera: str = "near") -> dict:
        """Get house state for a camera."""
        processor = self.processors.get(camera)
        if not processor:
            return {}

        detections = processor.latest_detections
        button = processor.get_button_position()
        house_radius = processor.get_house_radius()

        house_state = calculate_score_from_detections(
            detections, button[0], button[1], house_radius
        )

        return {
            "camera": camera,
            "scoring_team": house_state.scoring_team,
            "points": house_state.points,
            "red_rocks": len(house_state.red_rocks),
            "yellow_rocks": len(house_state.yellow_rocks),
            "visualization": visualize_house_state(house_state)
        }


def run_unified_test(
    near_video: str = "near_crop",
    far_video: str = "far_crop",
    max_frames: int = 100,
    frame_skip: int = 10
):
    """Test unified processor with video files."""
    print("=" * 70)
    print("UNIFIED CURLING VISION PROCESSOR")
    print("=" * 70)

    # Load calibration
    try:
        with open(CALIBRATION_FILE, "r") as f:
            calibration = json.load(f)
    except:
        calibration = {
            "calibration_sets": {
                "cropped": {
                    "near": {"button": (207, 375), "house_size": 400},
                    "far": {"button": (222, 374), "house_size": 400}
                }
            }
        }

    # Create processor
    processor = UnifiedGameProcessor(calibration, CONFIG)

    # Add cameras
    if near_video in VIDEO_SOURCES:
        processor.add_camera("near", VIDEO_SOURCES[near_video])
    if far_video in VIDEO_SOURCES:
        processor.add_camera("far", VIDEO_SOURCES[far_video])

    if not processor.start():
        print("Failed to start processors")
        return

    print(f"Processing {max_frames} frames, skip={frame_skip}")
    print(f"Cameras: {list(processor.processors.keys())}")
    print()

    start_time = time.time()
    results = []

    for i in range(max_frames):
        frame_results = processor.process_frame(skip=frame_skip)

        # Log state changes
        state = processor.get_state()
        if i % 10 == 0:
            print(f"Frame {i}: state={state['state']}, throws={state['total_throws']}, "
                  f"end={state['end']}")

        # Get house state periodically
        if i % 20 == 0 and "near" in processor.processors:
            house = processor.get_house_state("near")
            if house.get("visualization"):
                print(house["visualization"])

        results.append({
            "frame": i,
            "state": state,
            "house": house if i % 20 == 0 else None
        })

        # Check for end of video
        for name, res in frame_results.items():
            if "error" in res:
                print(f"[{name}] {res['error']}")
                break

    processor.stop()
    elapsed = time.time() - start_time

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Processed {max_frames} frames in {elapsed:.1f}s ({max_frames/elapsed:.2f} fps)")

    final_state = processor.get_state()
    print(f"\nFinal state:")
    for key, value in final_state.items():
        print(f"  {key}: {value}")

    # Count events
    events = processor.game_tracker.get_events()
    print(f"\nEvents logged: {len(events)}")
    for event in events[:10]:
        print(f"  {event}")

    # Save results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"{OUTPUT_DIR}/unified_test_{timestamp}.json"

    with open(result_file, "w") as f:
        json.dump({
            "frames_processed": max_frames,
            "elapsed": elapsed,
            "final_state": final_state,
            "events": events,
            "frame_results": results
        }, f, indent=2, default=str)

    print(f"\nResults saved to: {result_file}")


def main():
    parser = argparse.ArgumentParser(description="Unified curling vision processor")
    parser.add_argument("--near", "-n", default="near_crop", help="Near camera video")
    parser.add_argument("--far", "-f", default="far_crop", help="Far camera video")
    parser.add_argument("--frames", type=int, default=100, help="Max frames to process")
    parser.add_argument("--skip", "-s", type=int, default=10, help="Frame skip")
    args = parser.parse_args()

    run_unified_test(
        near_video=args.near,
        far_video=args.far,
        max_frames=args.frames,
        frame_skip=args.skip
    )


if __name__ == "__main__":
    main()