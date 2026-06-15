#!/usr/bin/env python3
"""
Download curling videos from YouTube.
Usage: python download_video.py <youtube_url> [--title "Brier 2024 Final"]
"""

import sys
import subprocess
from pathlib import Path

def download_video(url: str, title: str = None, output_dir: str = None):
    """Download video using yt-dlp."""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "videos"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build filename
    if title:
        filename = title.replace(" ", "_").replace("/", "-")
        output_template = str(output_dir / f"{filename}.%(ext)s")
    else:
        output_template = str(output_dir / "%(title)s.%(ext)s")

    print(f"🎬 Downloading: {url}")
    print(f"📤 Output dir: {output_dir}")

    # Run yt-dlp
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-playlist",
        url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Download failed: {result.stderr}")
        return None

    print(f"✅ Download complete")

    # Find the downloaded file
    videos = list(output_dir.glob("*.mp4"))
    if videos:
        # Return most recent
        return max(videos, key=lambda p: p.stat().st_mtime)
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_video.py <youtube_url> [--title \"Brier 2024 Final\"]")
        print("Example: python download_video.py https://youtube.com/watch?v=xxx --title \"Brier 2024 Final\"")
        sys.exit(1)

    url = sys.argv[1]
    title = None

    if "--title" in sys.argv:
        idx = sys.argv.index("--title")
        if idx + 1 < len(sys.argv):
            title = sys.argv[idx + 1]

    video_path = download_video(url, title)
    if video_path:
        print(f"\n📹 Video saved: {video_path}")