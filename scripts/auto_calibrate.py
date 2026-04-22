#!/usr/bin/env python3
"""
Auto-Calibration Module for Curling Vision System

Automatically detects calibration parameters from any curling video:
- Button position (center of house)
- House size (rings diameter in pixels)
- Team colors (rock color detection)
- Camera perspective (overhead/side/angle estimate)

This enables the system to work on ANY curling video without manual calibration.
"""

import cv2
import numpy as np
import json
import sys
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter

# Add scripts directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_source import open_video_source, detect_source_type


@dataclass
class CalibrationProfile:
    """Calibration parameters for a curling video source."""
    source: str
    source_type: str  # 'file', 'rtsp', 'youtube', 'usb'
    resolution: Tuple[int, int]  # (width, height)

    # House/Button detection
    button_position: Tuple[float, float]  # (x, y)
    button_confidence: float
    house_size: float  # diameter in pixels

    # Team colors detected
    team_colors: List[str]  # e.g., ['red-rock', 'yellow-rock']
    team_color_counts: Dict[str, int]  # detection counts per color

    # Camera perspective estimate
    perspective: str  # 'overhead', 'side', 'angle', 'unknown'
    perspective_confidence: float

    # Frame sampling info
    frames_analyzed: int
    calibration_time_ms: float

    # Model used
    model_id: str

    # Notes
    notes: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d['resolution'] = list(self.resolution)
        d['button_position'] = list(self.button_position)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'CalibrationProfile':
        """Create from dictionary."""
        d['resolution'] = tuple(d['resolution'])
        d['button_position'] = tuple(d['button_position'])
        return cls(**d)


class AutoCalibrator:
    """
    Automatically calibrates curling vision system for any video source.
    """

    def __init__(self, model_id: str = "fcc-curling-rock-detection/17",
                 api_key: str = None):
        """
        Initialize calibrator.

        Args:
            model_id: Roboflow model ID for detection
            api_key: Roboflow API key (reads from config if not provided)
        """
        self.model_id = model_id
        
        # Try to load API key from config file if not provided
        if api_key is None:
            config_paths = [
                '/home/curl/curling_config.json',
                os.path.expanduser('~/.curling_config.json'),
                os.path.join(os.path.dirname(__file__), '../config/curling_config.json')
            ]
            for config_path in config_paths:
                if os.path.exists(config_path):
                    try:
                        with open(config_path) as f:
                            config = json.load(f)
                            api_key = config.get('roboflow', {}).get('api_key') or config.get('api_key')
                            if api_key:
                                break
                    except (json.JSONDecodeError, IOError):
                        pass
        
        self.api_key = api_key or os.environ.get('ROBOFLOW_API_KEY', '')
        # Use Roboflow cloud REST API (same as other scripts)
        self.api_url = "https://detect.roboflow.com"
        self.calibration_profile: Optional[CalibrationProfile] = None

    def analyze_video(self, source: str, frames: int = 50,
                      skip: int = 10, verbose: bool = True) -> CalibrationProfile:
        """
        Analyze video and generate calibration profile.

        Args:
            source: Video source (file path, RTSP, YouTube URL, etc.)
            frames: Number of frames to analyze
            skip: Frames to skip between samples
            verbose: Print progress

        Returns:
            CalibrationProfile with detected parameters
        """
        import time
        start_time = time.time()

        # Detect source type
        source_type = detect_source_type(source)
        if verbose:
            print(f"Source type: {source_type}")

        # Open video
        cap, actual_source = open_video_source(source, verbose=verbose)
        if not cap.isOpened():
            raise ValueError(f"Could not open video source: {source}")

        # Get resolution
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        resolution = (width, height)

        if verbose:
            print(f"Resolution: {width}x{height}")
            print(f"Analyzing {frames} frames (skip={skip})...")

        # Collect detections across frames
        all_detections = []
        button_positions = []
        house_sizes = []
        frame_count = 0

        while frame_count < frames:
            ret, frame = cap.read()
            if not ret:
                break

            # Skip frames
            for _ in range(skip - 1):
                cap.read()

            # Run detection
            detections = self._detect_frame(frame)
            all_detections.append(detections)

            # Extract button and house info
            for det in detections:
                if det['class'] == 'Button' or det['class'] == 'button':
                    x = det['x']
                    y = det['y']
                    button_positions.append((x, y))
                elif det['class'] == 'house':
                    # House size is the width of bounding box
                    w = det.get('width', det.get('w', 0))
                    if w > 0:
                        house_sizes.append(w)

            frame_count += 1

        cap.release()

        if verbose:
            print(f"Analyzed {frame_count} frames")

        # Process button positions
        button_position, button_confidence = self._compute_button_position(button_positions)

        # Process house sizes
        house_size = self._compute_house_size(house_sizes)

        # Count team colors
        team_colors, team_color_counts = self._analyze_team_colors(all_detections)

        # Estimate perspective
        perspective, perspective_confidence = self._estimate_perspective(
            resolution, button_position, house_size
        )

        calibration_time_ms = (time.time() - start_time) * 1000

        # Create calibration profile
        profile = CalibrationProfile(
            source=actual_source,
            source_type=source_type,
            resolution=resolution,
            button_position=button_position,
            button_confidence=button_confidence,
            house_size=house_size,
            team_colors=team_colors,
            team_color_counts=team_color_counts,
            perspective=perspective,
            perspective_confidence=perspective_confidence,
            frames_analyzed=frame_count,
            calibration_time_ms=calibration_time_ms,
            model_id=self.model_id,
            notes=f"Auto-calibrated from {frame_count} frames"
        )

        self.calibration_profile = profile
        return profile

    def _detect_frame(self, frame: np.ndarray) -> List[Dict]:
        """
        Run detection on a single frame via Roboflow REST API.

        Args:
            frame: BGR image as numpy array

        Returns:
            List of detections with class, confidence, x, y, width, height
        """
        import requests

        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

        # Build API URL
        url = f"{self.api_url}/{self.model_id}"
        
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = requests.post(
                url,
                params=params,
                files={"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            print(f"Detection API error: {e}")
            return []

        # Parse detections
        detections = []
        predictions = result.get('predictions', [])

        for pred in predictions:
            det = {
                'class': pred.get('class', 'unknown'),
                'confidence': pred.get('confidence', 0),
                'x': pred.get('x', 0),
                'y': pred.get('y', 0),
                'width': pred.get('width', 0),
                'height': pred.get('height', 0)
            }
            detections.append(det)

        return detections

    def _compute_button_position(self, positions: List[Tuple[float, float]]) -> Tuple[Tuple[float, float], float]:
        """
        Compute button position from multiple detections.

        Returns:
            (button_position, confidence)
        """
        if not positions:
            return ((0.0, 0.0), 0.0)

        # Convert to numpy array
        positions = np.array(positions)

        # Compute mean position
        mean_x = np.mean(positions[:, 0])
        mean_y = np.mean(positions[:, 1])

        # Compute confidence based on consistency
        std_x = np.std(positions[:, 0])
        std_y = np.std(positions[:, 1])
        std_avg = (std_x + std_y) / 2

        # Lower std = higher confidence
        # std < 10px = high confidence (>0.9)
        # std > 50px = low confidence (<0.5)
        confidence = max(0.0, min(1.0, 1.0 - (std_avg / 100.0)))

        return ((float(mean_x), float(mean_y)), float(confidence))

    def _compute_house_size(self, sizes: List[float]) -> float:
        """
        Compute house size from multiple detections.

        Returns:
            Median house size in pixels
        """
        if not sizes:
            return 0.0
        return float(np.median(sizes))

    def _analyze_team_colors(self, all_detections: List[List[Dict]]) -> Tuple[List[str], Dict[str, int]]:
        """
        Analyze team colors from all detections.

        Returns:
            (list of team colors, count per color)
        """
        color_counts = Counter()

        for frame_dets in all_detections:
            for det in frame_dets:
                class_name = det['class'].lower()
                if 'rock' in class_name or 'stone' in class_name:
                    # Normalize color names
                    if 'red' in class_name:
                        color_counts['red-rock'] += 1
                    elif 'yellow' in class_name:
                        color_counts['yellow-rock'] += 1
                    elif 'blue' in class_name:
                        color_counts['blue-rock'] += 1
                    elif 'white' in class_name:
                        color_counts['white-rock'] += 1
                    else:
                        # Unknown color - count it
                        color_counts[class_name] += 1

        # Get top colors (assume 2 teams)
        top_colors = [c[0] for c in color_counts.most_common(2)]

        return top_colors, dict(color_counts)

    def _estimate_perspective(self, resolution: Tuple[int, int],
                               button_position: Tuple[float, float],
                               house_size: float) -> Tuple[str, float]:
        """
        Estimate camera perspective based on resolution and house position.

        Returns:
            (perspective_type, confidence)
        """
        width, height = resolution

        # Heuristics for perspective
        # Portrait (height > width) = likely end-camera (near or far)
        # Landscape (width > height) = likely wide or overhead
        # House size relative to frame also indicates perspective

        if height > width:
            # Portrait orientation
            # Button position near center = overhead-ish
            # Button position near edge = side view
            btn_x_ratio = button_position[0] / width
            btn_y_ratio = button_position[1] / height

            if 0.3 < btn_x_ratio < 0.7 and 0.3 < btn_y_ratio < 0.7:
                return ('overhead', 0.6)
            else:
                return ('side', 0.7)
        else:
            # Landscape orientation
            # Large house size relative to frame = overhead
            # Small house size = wide angle
            house_ratio = house_size / min(width, height) if house_size > 0 else 0

            if house_ratio > 0.3:
                return ('overhead', 0.7)
            else:
                return ('wide', 0.6)

    def save_calibration(self, filepath: str) -> None:
        """Save calibration profile to JSON file."""
        if self.calibration_profile is None:
            raise ValueError("No calibration profile to save")

        with open(filepath, 'w') as f:
            json.dump(self.calibration_profile.to_dict(), f, indent=2)

        print(f"Calibration saved to {filepath}")

    def load_calibration(self, filepath: str) -> CalibrationProfile:
        """Load calibration profile from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.calibration_profile = CalibrationProfile.from_dict(data)
        return self.calibration_profile

    def get_calibration_for_game_tracker(self) -> Dict:
        """
        Get calibration parameters formatted for game_tracker.py.

        Returns:
            Dict with button_position, house_size, team_colors, etc.
        """
        if self.calibration_profile is None:
            raise ValueError("No calibration profile available")

        p = self.calibration_profile

        return {
            'button': list(p.button_position),
            'house_size': p.house_size,
            'team_colors': p.team_colors,
            'resolution': list(p.resolution),
            'perspective': p.perspective,
            'source': p.source,
            'calibrated_at': p.calibration_time_ms,
            'frames_analyzed': p.frames_analyzed
        }


def auto_calibrate(source: str, frames: int = 50, skip: int = 10,
                   verbose: bool = True, save_path: Optional[str] = None) -> CalibrationProfile:
    """
    Convenience function to auto-calibrate a video source.

    Args:
        source: Video source (file, RTSP, YouTube URL, etc.)
        frames: Number of frames to analyze
        skip: Frames to skip between samples
        verbose: Print progress
        save_path: Optional path to save calibration JSON

    Returns:
        CalibrationProfile
    """
    calibrator = AutoCalibrator()
    profile = calibrator.analyze_video(source, frames=frames, skip=skip, verbose=verbose)

    if save_path:
        calibrator.save_calibration(save_path)

    return profile


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto-calibrate curling video")
    parser.add_argument("source", help="Video source (file, RTSP, YouTube URL)")
    parser.add_argument("--frames", type=int, default=50, help="Frames to analyze")
    parser.add_argument("--skip", type=int, default=10, help="Frames to skip between samples")
    parser.add_argument("--output", "-o", help="Output JSON file for calibration")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")

    args = parser.parse_args()

    verbose = not args.quiet

    calibrator = AutoCalibrator()
    profile = calibrator.analyze_video(
        args.source,
        frames=args.frames,
        skip=args.skip,
        verbose=verbose
    )

    if verbose:
        print("\n=== Calibration Profile ===")
        print(f"Source: {profile.source}")
        print(f"Type: {profile.source_type}")
        print(f"Resolution: {profile.resolution[0]}x{profile.resolution[1]}")
        print(f"Button: ({profile.button_position[0]:.1f}, {profile.button_position[1]:.1f})")
        print(f"Button Confidence: {profile.button_confidence:.2f}")
        print(f"House Size: {profile.house_size:.1f} px")
        print(f"Team Colors: {profile.team_colors}")
        print(f"Perspective: {profile.perspective} ({profile.perspective_confidence:.2f})")
        print(f"Frames Analyzed: {profile.frames_analyzed}")
        print(f"Calibration Time: {profile.calibration_time_ms:.0f}ms")

    if args.output:
        calibrator.save_calibration(args.output)