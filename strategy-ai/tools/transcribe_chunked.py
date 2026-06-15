#!/usr/bin/env python3
"""
Transcribe large videos by splitting into chunks.
xAI STT has timeout limits on long files, so we split into 30-min segments.
"""

import sys
import json
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load .env from tools directory
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

def split_audio(audio_path: Path, chunk_duration: int = 1800) -> list:
    """Split audio into chunks of chunk_duration seconds (default 30 min)."""
    chunks_dir = audio_path.parent / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    # Get duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())

    chunks = []
    start = 0
    chunk_num = 0

    while start < duration:
        chunk_file = chunks_dir / f"{audio_path.stem}_chunk{chunk_num:02d}.mp3"
        end = min(start + chunk_duration, duration)

        print(f"  Creating chunk {chunk_num}: {start:.0f}s - {end:.0f}s")

        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-ss", str(start), "-to", str(end),
            "-acodec", "libmp3lame", "-q:a", "2",
            str(chunk_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            chunks.append((chunk_file, start))
            chunk_num += 1

        start += chunk_duration

    return chunks

def transcribe_chunk(chunk_path: Path, start_offset: float, keyterms: list = None) -> dict:
    """Transcribe a single chunk using xAI STT API."""
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise ValueError("XAI_API_KEY not set")

    files = {"file": (chunk_path.name, open(chunk_path, "rb"), "audio/mpeg")}
    data = [("format", "true"), ("language", "en")]

    # Add curling keyterms
    if not keyterms:
        keyterms = [
            "curling", "hammer", "draw", "takeout", "guard",
            "house", "button", "four-foot", "eight-foot", "twelve-foot",
            "hog line", "hack", "sheet", "end", "bonspiel",
            "skip", "vice", "lead", "second", "sweep",
            "blank end", "steal", "blank", "extra end"
        ]
    for term in keyterms:
        data.append(("keyterm", term))

    try:
        response = requests.post(
            "https://api.x.ai/v1/stt",
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
            data=data,
            timeout=300  # 5 minute timeout per chunk
        )
        response.raise_for_status()
    finally:
        files["file"][1].close()

    result = response.json()

    # Adjust timestamps for chunk offset
    words = result.get("words", [])
    for word in words:
        if "start" in word:
            word["start"] += start_offset
        if "end" in word:
            word["end"] += start_offset

    return {
        "text": result.get("text", ""),
        "duration": result.get("duration", 0),
        "words": words,
        "chunk_start": start_offset
    }

def transcribe_video_chunked(video_path: str, output_dir: str = None):
    """Transcribe large video by splitting into chunks."""
    # Step 1: Extract audio
    print(f"🎬 Processing: {video_path}")
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return None

    # Extract audio using ffmpeg
    audio_path = video_path.parent / f"{video_path.stem}.mp3"
    if not audio_path.exists():
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
    else:
        print(f"✅ Audio already extracted: {audio_path}")

    # Step 2: Split into chunks
    print(f"✂️ Splitting audio into 30-minute chunks...")
    chunks = split_audio(Path(audio_path))

    if not chunks:
        print("❌ Failed to split audio")
        return None

    print(f"✅ Created {len(chunks)} chunks")

    # Step 3: Transcribe each chunk
    all_words = []
    all_text = []

    for i, (chunk_path, start_offset) in enumerate(chunks):
        print(f"\n🎙️ Transcribing chunk {i+1}/{len(chunks)}: {chunk_path.name}")

        try:
            result = transcribe_chunk(chunk_path, start_offset)
            all_words.extend(result["words"])
            all_text.append(result["text"])
            print(f"   ✅ {len(result['words'])} words, {result['duration']:.1f}s")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            continue

    # Step 4: Build segments from words
    segments = []
    current_segment = {"start": 0, "end": 0, "text": ""}
    segment_start = 0

    for i, word in enumerate(all_words):
        if i == 0:
            segment_start = word.get("start", 0)

        current_segment["text"] += " " + word.get("text", "")
        current_segment["end"] = word.get("end", 0)

        # New segment every ~15 seconds
        if current_segment["end"] - segment_start > 15 or i == len(all_words) - 1:
            current_segment["start"] = segment_start
            current_segment["text"] = current_segment["text"].strip()
            segments.append(current_segment.copy())
            current_segment = {"start": 0, "end": 0, "text": ""}
            if i < len(all_words) - 1:
                segment_start = all_words[i + 1].get("start", 0)

    # Step 5: Save combined transcript
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "transcripts"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{video_path.stem}_transcript.json"

    final_result = {
        "video_file": video_path.name,
        "duration": sum(c[1] for c in chunks) if chunks else 0,
        "language": "English",
        "text": " ".join(all_text),
        "segments": segments,
        "words_count": len(all_words)
    }

    with open(output_file, "w") as f:
        json.dump(final_result, f, indent=2)

    print(f"\n✅ Transcript saved: {output_file}")
    print(f"   Duration: {final_result['duration']:.1f}s ({final_result['duration']/60:.1f} min)")
    print(f"   Segments: {len(segments)}")
    print(f"   Words: {len(all_words)}")

    return output_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe_chunked.py <video_file>")
        print("       python transcribe_chunked.py videos/brier_2024_final.mp4")
        sys.exit(1)

    transcribe_video_chunked(sys.argv[1])