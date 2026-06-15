#!/usr/bin/env python3
"""
Transcribe curling videos using xAI Speech-to-Text API.
Usage: python transcribe_xai.py <video_file>
Output: JSON file with transcript + timestamps

Requires: XAI_API_KEY environment variable (or .env file)
"""

import sys
import json
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load .env from tools directory
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

def extract_audio(video_path: str, output_dir: str = None):
    """Extract audio from video file using ffmpeg."""
    video_path = Path(video_path)
    if output_dir is None:
        output_dir = video_path.parent
    output_dir = Path(output_dir)

    # Extract audio as MP3 (xAI supports many formats)
    audio_path = output_dir / f"{video_path.stem}.mp3"

    print(f"🎬 Extracting audio from: {video_path.name}")
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        str(audio_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Audio extraction failed: {result.stderr}")
        return None

    print(f"✅ Audio extracted: {audio_path}")
    return audio_path

def transcribe_audio(audio_path: str, output_dir: str = None, keyterms: list = None):
    """Transcribe audio using xAI STT API."""
    import requests

    audio_path = Path(audio_path)
    if output_dir is None:
        output_dir = audio_path.parent.parent / "transcripts"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("❌ XAI_API_KEY environment variable not set")
        print("   Set it with: export XAI_API_KEY=your_api_key")
        return None

    print(f"🎙️ Transcribing: {audio_path.name}")
    print(f"📤 Output dir: {output_dir}")

    # Build form data
    files = {"file": (audio_path.name, open(audio_path, "rb"), "audio/mpeg")}
    data = [
        ("format", "true"),  # Enable text formatting (numbers, currency)
        ("language", "en"),  # English for curling commentary
    ]

    # Add keyterms for better recognition of curling terminology
    if keyterms:
        for term in keyterms:
            data.append(("keyterm", term))
    else:
        # Default curling keyterms
        curling_terms = [
            "curling", "hammer", "draw", "takeout", "guard",
            "house", "button", "four-foot", "eight-foot", "twelve-foot",
            "hog line", "hack", "sheet", "end", "bonspiel",
            "skip", "vice", "lead", "second", "sweep",
            "blank end", "steal", "blank", "extra end"
        ]
        for term in curling_terms:
            data.append(("keyterm", term))

    try:
        response = requests.post(
            "https://api.x.ai/v1/stt",
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
            data=data
        )
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return None
    finally:
        files["file"][1].close()

    result = response.json()

    # Parse response
    output = {
        "video_file": audio_path.stem.replace("_audio", ""),
        "audio_file": audio_path.name,
        "duration": result.get("duration", 0),
        "language": result.get("language", "English"),
        "text": result.get("text", ""),
        "segments": []
    }

    # Convert word-level timestamps to segments
    words = result.get("words", [])
    if words:
        # Group words into segments (roughly every 10-15 seconds)
        current_segment = {"start": 0, "end": 0, "text": ""}
        segment_start = 0

        for i, word in enumerate(words):
            if i == 0:
                segment_start = word.get("start", 0)

            current_segment["text"] += " " + word.get("text", "")
            current_segment["end"] = word.get("end", 0)

            # New segment every ~15 seconds or at end
            if current_segment["end"] - segment_start > 15 or i == len(words) - 1:
                current_segment["start"] = segment_start
                current_segment["text"] = current_segment["text"].strip()
                output["segments"].append(current_segment.copy())
                current_segment = {"start": 0, "end": 0, "text": ""}
                if i < len(words) - 1:
                    segment_start = words[i + 1].get("start", 0)

    # Save JSON
    output_file = output_dir / f"{audio_path.stem}_transcript.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✅ Transcript saved: {output_file}")
    print(f"   Duration: {output['duration']:.1f}s ({output['duration']/60:.1f} min)")
    print(f"   Segments: {len(output['segments'])}")
    print(f"   Words: {len(words)}")

    return output_file

def transcribe_video(video_path: str, output_dir: str = None):
    """Full pipeline: extract audio from video, then transcribe."""
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return None

    # Step 1: Extract audio
    audio_path = extract_audio(video_path)
    if not audio_path:
        return None

    # Step 2: Transcribe
    return transcribe_audio(audio_path, output_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe_xai.py <video_file>")
        print("       python transcribe_xai.py videos/brier_2024_final.mp4")
        print("\nRequires XAI_API_KEY environment variable")
        sys.exit(1)

    if not os.environ.get("XAI_API_KEY"):
        print("❌ XAI_API_KEY not set")
        print("   Get your key from: https://console.x.ai/team/default/api-keys")
        print("   Set it with: export XAI_API_KEY=your_key")
        sys.exit(1)

    transcribe_video(sys.argv[1])