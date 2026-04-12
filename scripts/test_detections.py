#!/usr/bin/env python3
"""
Test harness for curling vision detection pipeline.
Uses REST API instead of InferencePipeline for Pi compatibility.

Usage:
    source /home/curl/timer_env/bin/activate
    python3 test_detections.py --video far_crop --frames 100
"""

import cv2
import json
import time
import sys
import os
import argparse
import requests
from collections import defaultdict
from datetime import datetime

# Config
CONFIG_FILE = "/home/curl/curling_config.json"
with open(CONFIG_FILE, "r") as f:
    CONFIG = json.load(f)

API_KEY = CONFIG["api_key"]
MODEL_ID = CONFIG["model_id"]

# Output directory
OUTPUT_DIR = "/home/curl/curling_vision/test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Test videos
TEST_VIDEOS = {
    "far_crop": "/home/curl/Videos/sheet5FarCrop.mp4",
    "near_crop": "/home/curl/Videos/sheet5NearCrop.mp4",
    "far_full": "/home/curl/Videos/curling/cam1_20260330_194005.mp4",
    "near_full": "/home/curl/Videos/curling/cam2_20260330_194005.mp4",
    "wide_full": "/home/curl/Videos/curling/cam3_20260330_194005.mp4",
}

# Calibration from saved state
CALIBRATION = {
    "far": {"button": (361.0, 599.0), "house_size": 748.7},
    "near": {"button": None, "house_size": None},
}


class DetectionStats:
    """Track detection statistics across frames."""
    def __init__(self):
        self.class_counts = defaultdict(int)
        self.confidence_samples = defaultdict(list)
        self.position_samples = defaultdict(list)
        self.frame_count = 0
        self.start_time = time.time()
        self.detections_per_frame = []

    def add_frame(self, detections):
        """Add all detections from a frame."""
        self.frame_count += 1
        self.detections_per_frame.append(len(detections))

        for det in detections:
            class_name = det.get("class") or det.get("name", "unknown")
            x, y = det.get("x", 0), det.get("y", 0)
            conf = det.get("confidence", 0)

            self.class_counts[class_name] += 1
            self.confidence_samples[class_name].append(conf)

            if class_name in ["red-rock", "yellow-rock", "Button", "house", "curling delivery"]:
                self.position_samples[class_name].append((x, y, conf))

    def report(self):
        """Print detection statistics."""
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0

        print(f"\n{'='*60}")
        print(f"DETECTION REPORT")
        print(f"{'='*60}")
        print(f"Frames: {self.frame_count} in {elapsed:.1f}s ({fps:.2f} fps)")

        if self.detections_per_frame:
            avg_det = sum(self.detections_per_frame) / len(self.detections_per_frame)
            print(f"Avg detections/frame: {avg_det:.1f}")

        print(f"\nDetections by class:")
        for class_name in sorted(self.class_counts.keys()):
            count = self.class_counts[class_name]
            if self.confidence_samples[class_name]:
                avg_conf = sum(self.confidence_samples[class_name]) / len(self.confidence_samples[class_name])
                print(f"  {class_name}: {count} (avg conf: {avg_conf:.3f})")
            else:
                print(f"  {class_name}: {count}")

        # Rock position analysis
        for rock_type in ["red-rock", "yellow-rock"]:
            if rock_type in self.position_samples and len(self.position_samples[rock_type]) > 0:
                positions = self.position_samples[rock_type]
                xs = [p[0] for p in positions]
                ys = [p[1] for p in positions]
                print(f"\n{rock_type}:")
                print(f"  Count: {len(positions)}")
                print(f"  X range: {min(xs):.1f} - {max(xs):.1f}")
                print(f"  Y range: {min(ys):.1f} - {max(ys):.1f}")

        # Button calibration analysis
        if "Button" in self.position_samples and len(self.position_samples["Button"]) > 0:
            buttons = self.position_samples["Button"]
            avg_x = sum(b[0] for b in buttons) / len(buttons)
            avg_y = sum(b[1] for b in buttons) / len(buttons)
            print(f"\nButton calibration:")
            print(f"  Samples: {len(buttons)}")
            print(f"  Avg position: ({avg_x:.1f}, {avg_y:.1f})")

            if len(buttons) >= 5:
                std_x = (sum((b[0] - avg_x)**2 for b in buttons) / len(buttons)) ** 0.5
                std_y = (sum((b[1] - avg_y)**2 for b in buttons) / len(buttons)) ** 0.5
                print(f"  Std deviation: ({std_x:.2f}, {std_y:.2f})")

        # Delivery detection
        if "curling delivery" in self.position_samples and len(self.position_samples["curling delivery"]) > 0:
            deliveries = self.position_samples["curling delivery"]
            print(f"\nCurling delivery:")
            print(f"  Count: {len(deliveries)}")
            if len(deliveries) > 0:
                avg_conf = sum(d[2] for d in deliveries) / len(deliveries)
                print(f"  Avg confidence: {avg_conf:.3f}")

        return {
            "frames": self.frame_count,
            "elapsed": elapsed,
            "fps": fps,
            "class_counts": dict(self.class_counts),
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
            print(f"API error: {response.status_code} - {response.text[:100]}")
            return {"predictions": []}
    except requests.Timeout:
        print("API timeout")
        return {"predictions": []}
    except Exception as e:
        print(f"API exception: {e}")
        return {"predictions": []}


def run_test(video_path, name="test", max_frames=100, frame_skip=3):
    """Run detection on video with frame skipping for speed."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Video: {video_path}")
    print(f"{'='*60}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Could not open {video_path}")
        return None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video: {total_frames} frames @ {video_fps:.1f} fps, {width}x{height}")
    print(f"Processing every {frame_skip}th frame, max {max_frames} frames\n")

    stats = DetectionStats()
    frame_idx = 0
    processed = 0

    while processed < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        # Skip frames
        if frame_idx % frame_skip != 0:
            continue

        # Run inference
        result = infer_frame(frame)
        detections = result.get("predictions", [])
        stats.add_frame(detections)

        processed += 1
        if processed % 10 == 0:
            print(f"  Processed {processed} frames, {len(detections)} detections in last frame")

    cap.release()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"{OUTPUT_DIR}/{name}_{timestamp}.json"

    report = stats.report()

    with open(result_file, "w") as f:
        json.dump({
            "video": name,
            "frames_processed": processed,
            "frame_skip": frame_skip,
            "stats": report,
            "calibration_saved": CALIBRATION,
        }, f, indent=2)

    print(f"\nResults saved to: {result_file}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Test curling vision detection (REST API)")
    parser.add_argument("--video", "-v", help="Video name or path")
    parser.add_argument("--frames", "-f", type=int, default=100, help="Max frames to process")
    parser.add_argument("--skip", "-s", type=int, default=3, help="Process every Nth frame")
    args = parser.parse_args()

    print("CURLING VISION TEST HARNESS (REST API)")
    print("=" * 60)
    print(f"Model: {MODEL_ID}")
    print(f"Max frames: {args.frames}")
    print(f"Frame skip: {args.skip}")
    print()

    # Determine video
    if args.video:
        if args.video in TEST_VIDEOS:
            videos = [(args.video, TEST_VIDEOS[args.video])]
        else:
            videos = [("custom", args.video)]
    else:
        # Default: test cropped videos
        videos = [
            ("far_crop", TEST_VIDEOS["far_crop"]),
            ("near_crop", TEST_VIDEOS["near_crop"]),
        ]

    for name, path in videos:
        if not os.path.exists(path):
            print(f"Skipping {name} — not found: {path}")
            continue
        run_test(path, name=name, max_frames=args.frames, frame_skip=args.skip)

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()