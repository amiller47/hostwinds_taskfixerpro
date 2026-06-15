#!/usr/bin/env python3
"""
Sync vision model detections with transcript timestamps.
Extracts frames at each transcript segment, runs rock detection,
and creates enriched training data with game state.

Usage:
    python sync_vision_transcript.py --video videos/Scotties_2024_Final.mp4 --transcript transcripts/Scotties_2024_Final_transcript.json
"""

import json
import subprocess
import sys
import requests
from pathlib import Path
from typing import Optional
import argparse

# Config
API_KEY = "LeQC1NAh1GQMqKIBo6qS"
MODEL_ID = "fcc-curling-rock-detection/17"
ROBOFLOW_URL = f"https://detect.roboflow.com/{MODEL_ID}"

# House dimensions (in pixels for 1280x720 broadcast)
HOUSE_CENTER = (640, 360)  # Approximate center
BUTTON_RADIUS = 20  # Pixels
FOUR_FOOT_RADIUS = 40
EIGHT_FOOT_RADIUS = 80
TWELVE_FOOT_RADIUS = 120


def extract_frame(video_path: str, timestamp: float, output_path: str) -> bool:
    """Extract a single frame from video at timestamp."""
    cmd = [
        "ffmpeg", "-y", "-ss", str(timestamp),
        "-i", video_path,
        "-frames:v", "1",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def detect_rocks(image_path: str) -> Optional[dict]:
    """Run rock detection on an image using Roboflow API."""
    with open(image_path, "rb") as f:
        image_data = f.read()

    try:
        response = requests.post(
            f"https://detect.roboflow.com/{MODEL_ID}",
            params={"api_key": API_KEY},
            files={"file": image_data},
            timeout=10
        )

        if response.status_code != 200:
            return None

        return response.json()
    except Exception as e:
        print(f"    ❌ Detection error: {e}")
        return None


def analyze_detections(result: dict) -> dict:
    """Analyze detection results to extract game state."""
    if not result:
        return {"detections": 0, "rocks": [], "house": None}

    predictions = result.get("predictions", [])
    image_width = result.get("image", {}).get("width", 1280)
    image_height = result.get("image", {}).get("height", 720)

    rocks = []
    house = None
    delivery = None

    for pred in predictions:
        cls = pred.get("class", "")
        x = pred.get("x", 0)
        y = pred.get("y", 0)
        conf = pred.get("confidence", 0)
        width = pred.get("width", 0)
        height = pred.get("height", 0)

        if cls in ["red-rock", "yellow-rock"]:
            # Calculate distance from button
            dist_from_button = ((x - HOUSE_CENTER[0])**2 + (y - HOUSE_CENTER[1])**2)**0.5

            # Determine if in house
            in_house = dist_from_button <= TWELVE_FOOT_RADIUS
            in_4ft = dist_from_button <= FOUR_FOOT_RADIUS
            in_8ft = dist_from_button <= EIGHT_FOOT_RADIUS

            rocks.append({
                "color": "red" if cls == "red-rock" else "yellow",
                "x": round(x, 1),
                "y": round(y, 1),
                "confidence": round(conf, 2),
                "distance_from_button": round(dist_from_button, 1),
                "in_house": in_house,
                "in_4ft": in_4ft,
                "in_8ft": in_8ft
            })

        elif cls == "house":
            house = {
                "x": round(x, 1),
                "y": round(y, 1),
                "confidence": round(conf, 2)
            }

        elif cls == "curling delivery":
            delivery = {
                "x": round(x, 1),
                "y": round(y, 1),
                "confidence": round(conf, 2)
            }

    # Sort rocks by distance from button (closest first)
    rocks.sort(key=lambda r: r["distance_from_button"])

    # Count rocks by color
    red_count = sum(1 for r in rocks if r["color"] == "red")
    yellow_count = sum(1 for r in rocks if r["color"] == "yellow")

    # Determine shot rock (closest to button)
    shot_rock = rocks[0] if rocks else None

    return {
        "detections": len(predictions),
        "rocks": rocks,
        "rock_count": {"red": red_count, "yellow": yellow_count},
        "shot_rock": shot_rock,
        "house": house,
        "delivery": delivery,
        "image_size": {"width": image_width, "height": image_height}
    }


def determine_score(rocks: list) -> dict:
    """
    Determine score based on rock positions.
    This is approximate - we don't know which end we're viewing.
    """
    if not rocks:
        return {"scoring": "unknown", "score": {"red": 0, "yellow": 0}}

    # Count rocks in house by color
    red_in_house = [r for r in rocks if r["color"] == "red" and r["in_house"]]
    yellow_in_house = [r for r in rocks if r["color"] == "yellow" and r["in_house"]]

    # Simple scoring: team with rock closest to button scores
    shot_rock = rocks[0] if rocks else None

    if not shot_rock:
        return {"scoring": "blank", "score": {"red": 0, "yellow": 0}}

    scoring_team = shot_rock["color"]
    points = 1

    # Count additional rocks for scoring team that are closer than opponent's closest
    if scoring_team == "red":
        closest_yellow = min([r["distance_from_button"] for r in yellow_in_house]) if yellow_in_house else 999
        points = sum(1 for r in red_in_house if r["distance_from_button"] < closest_yellow)
    else:
        closest_red = min([r["distance_from_button"] for r in red_in_house]) if red_in_house else 999
        points = sum(1 for r in yellow_in_house if r["distance_from_button"] < closest_red)

    return {
        "scoring": scoring_team,
        "points": points,
        "red_in_house": len(red_in_house),
        "yellow_in_house": len(yellow_in_house)
    }


def process_video_transcript(
    video_path: str,
    transcript_path: str,
    output_path: str,
    sample_rate: int = 1  # Process every Nth segment
):
    """
    Extract frames at transcript timestamps and run vision detection.

    Args:
        video_path: Path to video file
        transcript_path: Path to transcript JSON
        output_path: Path to output enriched transcript JSON
        sample_rate: Process every Nth segment (1 = all, 2 = every other, etc.)
    """
    video_path = Path(video_path)
    transcript_path = Path(transcript_path)
    output_path = Path(output_path)

    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return None

    if not transcript_path.exists():
        print(f"❌ Transcript not found: {transcript_path}")
        return None

    # Load transcript
    print(f"📖 Loading transcript: {transcript_path.name}")
    with open(transcript_path) as f:
        transcript = json.load(f)

    segments = transcript.get("segments", [])
    total_segments = len(segments)

    print(f"   Found {total_segments} segments")
    print(f"   Processing every {sample_rate}th segment")
    print()

    # Create temp directory for frames
    frames_dir = transcript_path.parent.parent / "frames"
    frames_dir.mkdir(exist_ok=True)

    # Process segments
    enriched_segments = []
    processed = 0
    errors = 0

    for i, segment in enumerate(segments):
        if i % sample_rate != 0:
            enriched_segments.append(segment)
            continue

        timestamp = segment.get("start", 0)
        text = segment.get("text", "")

        # Progress indicator
        mins = int(timestamp // 60)
        secs = int(timestamp % 60)
        print(f"[{i+1}/{total_segments}] {mins:02d}:{secs:02d} - {text[:50]}...")

        # Extract frame
        frame_path = frames_dir / f"frame_{i:04d}.jpg"
        if not extract_frame(str(video_path), timestamp, str(frame_path)):
            print(f"    ❌ Frame extraction failed")
            errors += 1
            enriched_segments.append(segment)
            continue

        # Run detection
        result = detect_rocks(str(frame_path))
        if not result:
            print(f"    ❌ Detection failed")
            errors += 1
            enriched_segments.append(segment)
            continue

        # Analyze detections
        analysis = analyze_detections(result)
        score = determine_score(analysis["rocks"])

        # Enrich segment
        enriched_segment = {
            **segment,
            "vision": {
                "rocks": analysis["rocks"],
                "rock_count": analysis["rock_count"],
                "shot_rock": analysis["shot_rock"],
                "house": analysis["house"],
                "delivery": analysis["delivery"],
                "score_analysis": score,
                "frame_path": str(frame_path.name)
            }
        }

        enriched_segments.append(enriched_segment)
        processed += 1

        # Summary line
        rock_count = analysis["rock_count"]
        print(f"    ✅ {rock_count['red']} red, {rock_count['yellow']} yellow rocks")
        if score["scoring"] != "unknown":
            print(f"       Scoring: {score['scoring']} ({score['points']} point{'s' if score['points'] != 1 else ''})")

    # Save enriched transcript
    enriched = {
        **transcript,
        "segments": enriched_segments,
        "vision_processing": {
            "processed_segments": processed,
            "errors": errors,
            "sample_rate": sample_rate
        }
    }

    with open(output_path, "w") as f:
        json.dump(enriched, f, indent=2)

    print()
    print("="*60)
    print(f"✅ Enriched transcript saved: {output_path}")
    print(f"   Processed: {processed} segments")
    print(f"   Errors: {errors}")
    print()

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Sync vision detections with transcript")
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--transcript", required=True, help="Path to transcript JSON")
    parser.add_argument("--output", help="Output path (default: <transcript>_vision.json)")
    parser.add_argument("--sample-rate", type=int, default=1, help="Process every Nth segment (default: 1)")

    args = parser.parse_args()

    output = args.output
    if not output:
        # Default output path
        transcript_path = Path(args.transcript)
        output = transcript_path.parent / f"{transcript_path.stem}_vision.json"

    process_video_transcript(
        args.video,
        args.transcript,
        output,
        args.sample_rate
    )


if __name__ == "__main__":
    main()