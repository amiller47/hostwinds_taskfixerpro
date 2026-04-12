#!/usr/bin/env python3
"""
Analyze detections in a video segment.
Shows what classes are detected and when.
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

TEST_VIDEOS = {
    "near_full": "/home/curl/Videos/curling/cam2_20260330_194005.mp4",
}


def infer_frame(frame, api_key=API_KEY, model_id=MODEL_ID):
    """Run inference on a single frame."""
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


def analyze_video(video_path: str, video_name: str, max_frames: int = 200, frame_skip: int = 5, start_frame: int = 0):
    """Analyze detections in video segment."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {video_name}")
    print(f"{'='*70}")
    print(f"Start frame: {start_frame}, Max frames: {max_frames}, Skip: {frame_skip}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Could not open {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Video: {total_frames} frames @ {fps:.1f} fps, duration: {total_frames/fps:.1f}s")

    # Skip to start frame
    if start_frame > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        print(f"Starting at frame {start_frame} ({start_frame/fps:.1f}s)")

    frame_idx = start_frame
    processed = 0

    # Track detections by class
    class_detections = defaultdict(list)  # class -> [(frame, time, x, y, conf)]
    delivery_frames = []

    print(f"\nProcessing...")

    while processed < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        if (frame_idx - start_frame) % frame_skip != 0:
            continue

        video_time = frame_idx / fps if fps > 0 else frame_idx * 0.1

        # Run inference
        result = infer_frame(frame)
        predictions = result.get("predictions", [])

        # Track detections
        for pred in predictions:
            class_name = pred.get("class") or pred.get("name", "unknown")
            x, y = pred.get("x", 0), pred.get("y", 0)
            conf = pred.get("confidence", 0)

            class_detections[class_name].append({
                "frame": frame_idx,
                "time": video_time,
                "x": x,
                "y": y,
                "conf": conf
            })

            if "delivery" in class_name.lower():
                delivery_frames.append(frame_idx)

        processed += 1

        if processed % 20 == 0:
            print(f"  Processed {processed} frames, up to frame {frame_idx}")

    cap.release()

    # Print summary
    print(f"\n{'='*70}")
    print(f"DETECTION SUMMARY")
    print(f"{'='*70}")
    print(f"Frames processed: {processed}")
    print(f"Frame range: {start_frame} - {frame_idx}")
    print(f"Video time: {start_frame/fps:.1f}s - {frame_idx/fps:.1f}s")

    print(f"\nDetections by class:")
    for class_name in sorted(class_detections.keys()):
        dets = class_detections[class_name]
        avg_conf = sum(d["conf"] for d in dets) / len(dets) if dets else 0
        print(f"  {class_name}: {len(dets)} (avg conf: {avg_conf:.3f})")

    if delivery_frames:
        print(f"\nDelivery frames: {delivery_frames[:10]}{'...' if len(delivery_frames) > 10 else ''}")
        print(f"Total delivery detections: {len(delivery_frames)}")

    # Find frames with most rocks
    print(f"\nRock counts over time:")
    rock_counts = defaultdict(int)  # frame -> count
    for det in class_detections.get("red-rock", []):
        rock_counts[det["frame"]] += 1
    for det in class_detections.get("yellow-rock", []):
        rock_counts[det["frame"]] += 1

    if rock_counts:
        max_rocks_frame = max(rock_counts.keys(), key=lambda f: rock_counts[f])
        print(f"  Max rocks in frame {max_rocks_frame}: {rock_counts[max_rocks_frame]}")

        # Show distribution
        counts = sorted(set(rock_counts.values()))
        for c in counts:
            frames_with_count = sum(1 for f in rock_counts if rock_counts[f] == c)
            print(f"  {c} rocks: {frames_with_count} frames")

    return class_detections


def main():
    parser = argparse.ArgumentParser(description="Analyze detections in video")
    parser.add_argument("--video", "-v", default="near_full", help="Video name")
    parser.add_argument("--frames", "-f", type=int, default=200, help="Max frames")
    parser.add_argument("--skip", "-s", type=int, default=5, help="Frame skip")
    parser.add_argument("--start", type=int, default=0, help="Start frame")
    args = parser.parse_args()

    if args.video in TEST_VIDEOS:
        video_path = TEST_VIDEOS[args.video]
    else:
        video_path = args.video

    analyze_video(video_path, args.video, max_frames=args.frames, frame_skip=args.skip, start_frame=args.start)


if __name__ == "__main__":
    main()