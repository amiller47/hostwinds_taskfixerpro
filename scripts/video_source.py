#!/usr/bin/env python3
"""
Flexible video source handler for curling vision system.
Supports: RTSP, video files, YouTube, USB cameras, HTTP streams.
"""

import cv2
import subprocess
import json
import re
from typing import Optional, Tuple

def get_youtube_stream_url(url: str, quality: str = "best") -> Optional[str]:
    """
    Extract direct stream URL from YouTube using yt-dlp.

    Args:
        url: YouTube URL
        quality: 'best', 'worst', or specific quality like '720p'

    Returns:
        Direct stream URL or None if failed
    """
    try:
        # Try multiple yt-dlp locations
        ytdlp_paths = ['yt-dlp', '/home/curl/timer_env/bin/yt-dlp']
        ytdlp = None
        for path in ytdlp_paths:
            try:
                subprocess.run([path, '--version'], capture_output=True, timeout=5)
                ytdlp = path
                break
            except:
                continue
        
        if not ytdlp:
            print("yt-dlp not found")
            return None
        
        cmd = [
            ytdlp,
            '--get-url',
            '--format', f'best[ext=mp4]' if quality == 'best' else quality,
            '--no-playlist',
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            stream_url = result.stdout.strip().split('\n')[0]
            return stream_url
    except Exception as e:
        print(f"yt-dlp error: {e}")
    return None


def get_stream_info(url: str) -> dict:
    """
    Get info about a stream/video using yt-dlp.

    Returns dict with: title, duration, resolution, etc.
    """
    try:
        # Try multiple yt-dlp locations
        ytdlp_paths = ['yt-dlp', '/home/curl/timer_env/bin/yt-dlp']
        ytdlp = None
        for path in ytdlp_paths:
            try:
                subprocess.run([path, '--version'], capture_output=True, timeout=5)
                ytdlp = path
                break
            except:
                continue
        
        if not ytdlp:
            return {}
        
        cmd = [ytdlp, '--dump-json', '--no-playlist', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"yt-dlp info error: {e}")
    return {}


def detect_source_type(source: str) -> str:
    """
    Detect the type of video source.

    Returns: 'rtsp', 'youtube', 'http', 'usb', 'file'
    """
    if source.startswith('rtsp://'):
        return 'rtsp'
    elif 'youtube.com' in source or 'youtu.be' in source:
        return 'youtube'
    elif source.startswith('http://') or source.startswith('https://'):
        # Could be HTTP stream or yt-dlp supported site
        return 'http'
    elif source.startswith('usb:') or source.startswith('/dev/video'):
        return 'usb'
    elif source.isdigit():
        return 'usb'  # Camera index
    else:
        return 'file'


def open_video_source(source: str, verbose: bool = True) -> Tuple[cv2.VideoCapture, str]:
    """
    Open any video source and return a VideoCapture object.

    Args:
        source: Video source specification:
            - Local file: "/path/to/video.mp4"
            - RTSP: "rtsp://camera-ip/stream"
            - YouTube: "https://youtube.com/watch?v=xxx"
            - USB camera: "usb:0" or "/dev/video0" or just "0"
            - HTTP stream: "http://ip:port/stream.m3u8"
            - Any yt-dlp supported URL

    Returns:
        Tuple of (VideoCapture, source_type)
    """
    source_type = detect_source_type(source)
    cap = None

    if verbose:
        print(f"Opening video source: {source}")
        print(f"Detected type: {source_type}")

    if source_type == 'rtsp':
        # RTSP stream
        cap = cv2.VideoCapture(source)
        # Set buffer size for RTSP
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    elif source_type == 'youtube':
        # YouTube - get direct stream URL
        if verbose:
            print("Extracting YouTube stream URL...")
        stream_url = get_youtube_stream_url(source)
        if stream_url:
            if verbose:
                print(f"Got stream URL: {stream_url[:80]}...")
            cap = cv2.VideoCapture(stream_url)
        else:
            raise ValueError(f"Could not extract YouTube stream from: {source}")

    elif source_type == 'http':
        # HTTP stream or other yt-dlp supported site
        # Try direct OpenCV first
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            # Try yt-dlp
            if verbose:
                print("Trying yt-dlp for HTTP source...")
            stream_url = get_youtube_stream_url(source)
            if stream_url:
                cap = cv2.VideoCapture(stream_url)

    elif source_type == 'usb':
        # USB camera
        if source.startswith('usb:'):
            device = int(source.split(':')[1])
        elif source.isdigit():
            device = int(source)
        elif '/dev/video' in source:
            device = int(source.replace('/dev/video', ''))
        else:
            device = 0

        if verbose:
            print(f"Opening USB camera /dev/video{device}")
        cap = cv2.VideoCapture(device)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)

    else:
        # Local file
        cap = cv2.VideoCapture(source)

    if cap is None or not cap.isOpened():
        raise ValueError(f"Could not open video source: {source}")

    # Get video info
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if verbose:
        print(f"Video opened: {width:.0f}x{height:.0f} @ {fps:.1f} fps")
        if frame_count > 0:
            duration = frame_count / fps if fps > 0 else 0
            print(f"Frames: {frame_count}, Duration: {duration:.1f}s")

    return cap, source_type


def list_usb_cameras() -> list:
    """List available USB cameras."""
    cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append(i)
            cap.release()
    return cameras


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python video_source.py <source>")
        print("  source can be:")
        print("    - Local file: /path/to/video.mp4")
        print("    - RTSP: rtsp://camera-ip/stream")
        print("    - YouTube: https://youtube.com/watch?v=xxx")
        print("    - USB camera: usb:0 or just 0")
        print("    - HTTP stream: http://ip:port/stream")
        print("")
        print("Available USB cameras:")
        for cam in list_usb_cameras():
            print(f"  /dev/video{cam}")
        sys.exit(1)

    source = sys.argv[1]
    print(f"Testing: {source}")
    print()

    try:
        cap, source_type = open_video_source(source, verbose=True)
        print()
        print("✅ Source opened successfully!")
        print(f"   Type: {source_type}")

        # Read a few frames
        print()
        print("Reading 5 frames...")
        for i in range(5):
            ret, frame = cap.read()
            if ret:
                print(f"  Frame {i+1}: {frame.shape[1]}x{frame.shape[0]}")
            else:
                print(f"  Frame {i+1}: FAILED")
                break

        cap.release()
        print()
        print("Done!")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)