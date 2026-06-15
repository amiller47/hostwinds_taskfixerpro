#!/usr/bin/env python3
"""
Annotate strategic moments in curling videos.
Usage: python annotate.py <transcript_file>
Interactive tool to mark strategic commentary moments.
"""

import sys
import json
from pathlib import Path
from datetime import timedelta

def format_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    return str(timedelta(seconds=int(seconds)))

def load_transcript(transcript_path: str):
    """Load transcript JSON."""
    with open(transcript_path) as f:
        return json.load(f)

def annotate_transcript(transcript: dict, output_file: str = None):
    """Interactive annotation of strategic moments."""
    print("\n" + "="*60)
    print("🥌 CURLING STRATEGY ANNOTATOR")
    print("="*60)
    print("\nInstructions:")
    print("  - Read transcript segments")
    print("  - Press 's' to mark a segment as strategic")
    print("  - Press 'n' to skip (not strategic)")
    print("  - Press 'q' to quit and save")
    print("  - Press 'p' to see previous segments")
    print("\n" + "="*60 + "\n")

    annotations = []
    current_idx = 0
    segments = transcript["segments"]

    while current_idx < len(segments):
        seg = segments[current_idx]
        time_str = format_time(seg["start"])

        print(f"\n[{current_idx+1}/{len(segments)}] {time_str}")
        print(f"   \"{seg['text']}\"")
        print()

        cmd = input("Mark as strategic? (s/n/p/q): ").strip().lower()

        if cmd == 'q':
            break
        elif cmd == 'p' and current_idx > 0:
            current_idx -= 1
            continue
        elif cmd == 's':
            # Get game state from user
            print("\n--- Game State ---")
            end_num = input("End number (1-10): ").strip() or "?"
            score_red = input("Red score: ").strip() or "?"
            score_yellow = input("Yellow score: ").strip() or "?"
            hammer = input("Hammer (red/yellow): ").strip() or "?"
            shot_num = input("Shot number in end: ").strip() or "?"

            strategic_type = input("Strategy type (tactical/coaching/broadcast): ").strip() or "broadcast"

            annotation = {
                "segment_idx": current_idx,
                "timestamp": seg["start"],
                "commentary": seg["text"],
                "game_state": {
                    "end": end_num,
                    "score": {"red": score_red, "yellow": score_yellow},
                    "hammer": hammer,
                    "shot_number": shot_num
                },
                "type": strategic_type,
                "annotation_source": "human"
            }
            annotations.append(annotation)
            print("✅ Marked as strategic")
            current_idx += 1
        elif cmd == 'n':
            current_idx += 1

    # Save annotations
    if output_file is None:
        video_name = Path(transcript["video_file"]).stem
        output_file = Path(__file__).parent.parent / "annotations" / f"{video_name}_annotated.json"

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "video_file": transcript["video_file"],
        "total_segments": len(segments),
        "strategic_segments": len(annotations),
        "annotations": annotations
    }

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n✅ Saved {len(annotations)} annotations to {output_file}")
    return output_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python annotate.py <transcript_file>")
        print("       python annotate.py transcripts/brier_2024_final_transcript.json")
        sys.exit(1)

    transcript = load_transcript(sys.argv[1])
    annotate_transcript(transcript)