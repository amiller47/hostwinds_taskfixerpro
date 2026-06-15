#!/usr/bin/env python3
"""
Transcribe curling videos using OpenAI Whisper API.
Usage: python transcribe.py <video_file>
Output: JSON file with transcript + timestamps
"""

import sys
import json
import os
from pathlib import Path

# Add venv to path
venv_path = Path(__file__).parent.parent / "venv"
if venv_path.exists():
    sys.path.insert(0, str(venv_path / "lib" / "python3.11" / "site-packages"))

try:
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI library not installed. Run: pip install openai")
    sys.exit(1)

def transcribe_video(video_path: str, output_dir: str = None):
    """Transcribe video using Whisper API."""
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return None

    if output_dir is None:
        output_dir = video_path.parent.parent / "transcripts"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{video_path.stem}_transcript.json"

    print(f"🎬 Transcribing: {video_path.name}")
    print(f"📤 Output: {output_file}")

    client = OpenAI()  # Uses OPENAI_API_KEY env var

    try:
        with open(video_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return None

    # Parse response
    result = {
        "video_file": video_path.name,
        "duration": transcript.duration,
        "language": transcript.language,
        "segments": []
    }

    for seg in transcript.segments:
        result["segments"].append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip()
        })

    # Save JSON
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"✅ Transcript saved: {output_file}")
    print(f"   Duration: {transcript.duration:.1f}s ({transcript.duration/60:.1f} min)")
    print(f"   Segments: {len(result['segments'])}")

    return output_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <video_file>")
        print("       python transcribe.py videos/brier_2024_final.mp4")
        sys.exit(1)

    transcribe_video(sys.argv[1])