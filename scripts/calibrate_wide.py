#!/usr/bin/env python3
"""
Calibrate wide camera (cam3) for button position and house size.
Processes sample frames and finds the button using rock detection.
"""

import cv2
import json
import time
import sys
import os
import argparse
import requests
import numpy as np

# Config
CONFIG_FILE = "/home/curl/curling_config.json"
CALIBRATION_FILE = "/home/curl/curling_vision/config/calibration.json"

with open(CONFIG_FILE, "r") as f:
    CONFIG = json.load(f)

API_KEY = CONFIG["api_key"]

# Wide camera uses instance detection model
WIDE_MODEL_ID = "fcc-instance-detection/7"


def infer_frame(frame, api_key=API_KEY, model_id=WIDE_MODEL_ID):
    """Run inference on a single frame via REST API."""
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    try:
        response = requests.post(
            f"https://detect.roboflow.com/{model_id}",
            params={"api_key": api_key},
            files={"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("predictions", [])
        else:
            print(f"API error: {response.status_code}")
    except Exception as e:
        print(f"API error: {e}")
    return []


def find_button_from_detections(detections, frame_shape):
    """
    Find button position from detections.
    Look for stationary rocks near center-bottom of frame (near house).
    Also look for the button itself if detected.
    """
    height, width = frame_shape[:2]
    
    # Collect all rocks
    red_rocks = []
    yellow_rocks = []
    buttons = []
    
    for det in detections:
        cls = det.get("class", "").lower()
        x, y = det.get("x"), det.get("y")
        w, h = det.get("width"), det.get("height")
        
        if "button" in cls:
            buttons.append((x, y))
        elif "red" in cls and "rock" in cls:
            red_rocks.append((x, y, w, h))
        elif "yellow" in cls and "rock" in cls:
            yellow_rocks.append((x, y, w, h))
    
    return {
        "buttons": buttons,
        "red_rocks": red_rocks,
        "yellow_rocks": yellow_rocks
    }


def main():
    parser = argparse.ArgumentParser(description="Calibrate wide camera")
    parser.add_argument("--video", "-v", default="/home/curl/Videos/curling/cam3_20260330_194005.mp4")
    parser.add_argument("--frames", "-f", type=int, default=20, help="Frames to sample")
    parser.add_argument("--skip", "-s", type=int, default=100, help="Frame skip")
    parser.add_argument("--model", "-m", default=WIDE_MODEL_ID, help="Model ID")
    args = parser.parse_args()

    print("WIDE CAMERA CALIBRATION")
    print("=" * 60)
    print(f"Video: {args.video}")
    print(f"Model: {args.model}")
    print(f"Sampling {args.frames} frames, skip={args.skip}")
    print()

    if not os.path.exists(args.video):
        print(f"ERROR: Video not found: {args.video}")
        return

    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video: {width}x{height}, {total_frames} frames @ {fps:.1f} fps")
    print()

    # Sample frames
    all_detections = []
    frame_positions = []
    
    start_time = time.time()
    
    for i in range(args.frames):
        # Skip frames
        for _ in range(args.skip - 1):
            cap.read()
        
        ret, frame = cap.read()
        if not ret:
            print(f"End of video at frame {i * args.skip}")
            break
        
        frame_num = i * args.skip
        
        # Run inference
        print(f"Frame {frame_num}...", end=" ")
        detections = infer_frame(frame, model_id=args.model)
        
        if detections:
            print(f"{len(detections)} detections")
            all_detections.append(detections)
            
            # Analyze detections
            result = find_button_from_detections(detections, frame.shape)
            frame_positions.append(result)
            
            # Print what we found
            if result["buttons"]:
                print(f"  Buttons: {result['buttons']}")
            if result["red_rocks"]:
                print(f"  Red rocks: {len(result['red_rocks'])}")
            if result["yellow_rocks"]:
                print(f"  Yellow rocks: {len(result['yellow_rocks'])}")
        else:
            print("no detections")
    
    cap.release()
    elapsed = time.time() - start_time
    
    print()
    print("=" * 60)
    print("CALIBRATION SUMMARY")
    print("=" * 60)
    print(f"Processed {len(all_detections)} frames in {elapsed:.1f}s")
    print()
    
    # Aggregate detections
    total_buttons = sum(len(f["buttons"]) for f in frame_positions)
    total_red = sum(len(f["red_rocks"]) for f in frame_positions)
    total_yellow = sum(len(f["yellow_rocks"]) for f in frame_positions)
    
    print(f"Total detections across all frames:")
    print(f"  Buttons: {total_buttons}")
    print(f"  Red rocks: {total_red}")
    print(f"  Yellow rocks: {total_yellow}")
    
    # If we found buttons, calculate average position
    if total_buttons > 0:
        button_positions = []
        for f in frame_positions:
            for b in f["buttons"]:
                button_positions.append(b)
        
        if button_positions:
            avg_x = np.mean([b[0] for b in button_positions])
            avg_y = np.mean([b[1] for b in button_positions])
            std_x = np.std([b[0] for b in button_positions])
            std_y = np.std([b[1] for b in button_positions])
            
            print()
            print(f"Button position estimate: ({avg_x:.1f}, {avg_y:.1f})")
            print(f"Std dev: ({std_x:.1f}, {std_y:.1f})")
            
            # Update calibration file
            with open(CALIBRATION_FILE) as f:
                cal_data = json.load(f)
            
            if "calibration_sets" not in cal_data:
                cal_data["calibration_sets"] = {}
            if "rtsp" not in cal_data["calibration_sets"]:
                cal_data["calibration_sets"]["rtsp"] = {}
            
            cal_data["calibration_sets"]["rtsp"]["wide"] = {
                "resolution": [width, height],
                "button": [float(avg_x), float(avg_y)],
                "button_std": [float(std_x), float(std_y)],
                "house_size": None,  # Still need to determine
                "source": args.video,
                "model": args.model,
                "notes": f"Calibrated from {len(button_positions)} button detections"
            }
            
            with open(CALIBRATION_FILE, "w") as f:
                json.dump(cal_data, f, indent=2)
            
            print()
            print(f"Calibration saved to {CALIBRATION_FILE}")
    else:
        print()
        print("No buttons detected. The wide model may not detect buttons directly.")
        print("Manual calibration may be needed, or check model output classes.")
        
        # Print what classes the model detected
        all_classes = set()
        for detections in all_detections:
            for det in detections:
                all_classes.add(det.get("class", "unknown"))
        
        print()
        print(f"Classes detected by model: {sorted(all_classes)}")


if __name__ == "__main__":
    main()