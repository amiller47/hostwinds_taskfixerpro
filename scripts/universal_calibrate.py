#!/usr/bin/env python3
"""
Universal Auto-Calibration for Curling Vision System

This module handles calibration for ANY curling video source, adapting to:
- Different camera perspectives (overhead, side, wide)
- Different resolution/aspect ratios
- Different ice sheets and lighting conditions
- Videos with or without visible button/house

Key insight: The "house size" from the model is the bounding box width,
which may differ from actual ring diameter. We use the button position
as primary reference and derive other parameters from resolution ratios.
"""

import cv2
import numpy as np
import json
import sys
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_source import open_video_source, detect_source_type


@dataclass
class UniversalCalibration:
    """Calibration that adapts to any curling video source."""
    source: str
    source_type: str
    resolution: Tuple[int, int]
    
    # Primary: Button detection (most reliable)
    button_position: Tuple[float, float]
    button_confidence: float
    button_samples: int
    
    # Secondary: House detection
    house_size: float  # Bounding box width from model
    house_center: Optional[Tuple[float, float]]
    house_samples: int
    
    # Team composition
    team_colors: List[str]
    team_color_counts: Dict[str, int]
    
    # Derived: Camera perspective classification
    perspective: str  # 'near', 'far', 'wide', 'unknown'
    perspective_confidence: float
    
    # Scoring parameters (derived from button + resolution)
    score_radius: float  # Pixels from button for scoring
    
    # Metadata
    frames_analyzed: int
    frames_with_detections: int
    calibration_time_ms: float
    model_id: str
    
    # Quality indicators
    quality_score: float  # 0-1, how reliable is this calibration
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['resolution'] = list(self.resolution)
        d['button_position'] = list(self.button_position)
        if self.house_center:
            d['house_center'] = list(self.house_center)
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> 'UniversalCalibration':
        d['resolution'] = tuple(d['resolution'])
        d['button_position'] = tuple(d['button_position'])
        if 'house_center' in d and d['house_center']:
            d['house_center'] = tuple(d['house_center'])
        return cls(**d)


class UniversalCalibrator:
    """
    Calibrates curling vision for ANY video source.
    
    Strategy:
    1. Sample first N frames to detect button, house, and rocks
    2. Use button position as primary anchor (most reliable)
    3. Estimate house size from bounding box or resolution ratio
    4. Classify camera perspective (near/far/wide) from resolution and position
    5. Calculate scoring radius from button position
    """
    
    # Standard curling dimensions (for reference)
    HOUSE_DIAMETER_FT = 12.0  # 12-foot rings
    BUTTON_RADIUS_FT = 0.5    # Button is ~1ft diameter
    
    def __init__(self, model_id: str = "fcc-curling-rock-detection/17", 
                 wide_model_id: str = "fcc-instance-detection/7",
                 api_key: str = None):
        """
        Initialize calibrator.
        
        Args:
            model_id: Primary Roboflow model (button, house, rocks)
            wide_model_id: Wide camera model (rocks, hog lines)
            api_key: Roboflow API key
        """
        self.model_id = model_id
        self.wide_model_id = wide_model_id
        
        # Load API key
        if api_key is None:
            config_paths = [
                '/home/curl/curling_config.json',
                os.path.expanduser('~/.curling_config.json'),
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
        self.api_url = "https://detect.roboflow.com"
        
        self.calibration: Optional[UniversalCalibration] = None
    
    def analyze_video(self, source: str, frames: int = 50, 
                      skip: int = 10, verbose: bool = True) -> UniversalCalibration:
        """
        Analyze video and produce universal calibration.
        
        Args:
            source: Video source (file, RTSP, YouTube URL)
            frames: Number of frames to sample
            skip: Frames to skip between samples
            verbose: Print progress
            
        Returns:
            UniversalCalibration with all detected parameters
        """
        import time
        start_time = time.time()
        
        source_type = detect_source_type(source)
        if verbose:
            print(f"\n{'='*60}")
            print(f"Universal Calibration: {source}")
            print(f"{'='*60}")
            print(f"Source type: {source_type}")
        
        cap, actual_source = open_video_source(source, verbose=verbose)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {source}")
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        resolution = (width, height)
        
        if verbose:
            print(f"Resolution: {width}x{height}")
            print(f"Sampling {frames} frames (skip={skip})...")
        
        # Collect detections
        all_detections = []
        button_positions = []
        house_boxes = []
        frame_count = 0
        frames_with_detections = 0
        
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
            
            if detections:
                frames_with_detections += 1
            
            # Extract button and house
            for det in detections:
                class_lower = det['class'].lower()
                
                if class_lower == 'button':
                    button_positions.append((det['x'], det['y']))
                
                elif class_lower == 'house':
                    house_boxes.append({
                        'x': det['x'],
                        'y': det['y'],
                        'width': det['width'],
                        'height': det['height']
                    })
            
            frame_count += 1
        
        cap.release()
        
        if verbose:
            print(f"Analyzed {frame_count} frames, {frames_with_detections} with detections")
        
        # Process button positions
        button_pos, button_conf, button_samples = self._compute_button(button_positions)
        
        # Process house boxes
        house_size, house_center, house_samples = self._compute_house(house_boxes)
        
        # Team colors
        team_colors, team_color_counts = self._analyze_colors(all_detections)
        
        # Classify perspective
        perspective, persp_conf = self._classify_perspective(
            resolution, button_pos, house_size, frame_count, frames_with_detections
        )
        
        # Calculate scoring radius (distance from button for scoring)
        score_radius = self._compute_score_radius(
            resolution, button_pos, house_size, perspective
        )
        
        # Quality assessment
        quality, warnings = self._assess_quality(
            button_samples, house_samples, team_colors, 
            frames_with_detections, frame_count
        )
        
        calibration_time_ms = (time.time() - start_time) * 1000
        
        self.calibration = UniversalCalibration(
            source=actual_source,
            source_type=source_type,
            resolution=resolution,
            button_position=button_pos,
            button_confidence=button_conf,
            button_samples=button_samples,
            house_size=house_size,
            house_center=house_center,
            house_samples=house_samples,
            team_colors=team_colors,
            team_color_counts=team_color_counts,
            perspective=perspective,
            perspective_confidence=persp_conf,
            score_radius=score_radius,
            frames_analyzed=frame_count,
            frames_with_detections=frames_with_detections,
            calibration_time_ms=calibration_time_ms,
            model_id=self.model_id,
            quality_score=quality,
            warnings=warnings
        )
        
        if verbose:
            self._print_summary()
        
        return self.calibration
    
    def _detect_frame(self, frame: np.ndarray) -> List[Dict]:
        """Run detection on a single frame via Roboflow API."""
        import requests
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        url = f"{self.api_url}/{self.model_id}"
        params = {"api_key": self.api_key} if self.api_key else {}
        
        try:
            response = requests.post(
                url,
                params=params,
                files={"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
                timeout=15
            )
            response.raise_for_status()
            return response.json().get('predictions', [])
        except Exception as e:
            # Silent fail during calibration - just return empty
            return []
    
    def _compute_button(self, positions: List[Tuple[float, float]]) -> Tuple[Tuple[float, float], float, int]:
        """Compute button position from detections."""
        if not positions:
            return ((0.0, 0.0), 0.0, 0)
        
        positions = np.array(positions)
        mean_x = np.mean(positions[:, 0])
        mean_y = np.mean(positions[:, 1])
        
        # Confidence based on consistency
        std_x = np.std(positions[:, 0])
        std_y = np.std(positions[:, 1])
        std_avg = (std_x + std_y) / 2
        
        # Lower std = higher confidence
        confidence = max(0.0, min(1.0, 1.0 - (std_avg / 50.0)))
        
        return ((float(mean_x), float(mean_y)), float(confidence), len(positions))
    
    def _compute_house(self, boxes: List[Dict]) -> Tuple[float, Optional[Tuple[float, float]], int]:
        """Compute house size and center from detections."""
        if not boxes:
            return (0.0, None, 0)
        
        # House size is the width of the bounding box
        widths = [b['width'] for b in boxes]
        house_size = float(np.median(widths))
        
        # House center
        centers_x = [b['x'] for b in boxes]
        centers_y = [b['y'] for b in boxes]
        house_center = (float(np.mean(centers_x)), float(np.mean(centers_y)))
        
        return (house_size, house_center, len(boxes))
    
    def _analyze_colors(self, all_detections: List[List[Dict]]) -> Tuple[List[str], Dict[str, int]]:
        """Analyze team colors from detections."""
        color_counts = Counter()
        
        for frame_dets in all_detections:
            for det in frame_dets:
                class_lower = det['class'].lower()
                if 'rock' in class_lower or 'stone' in class_lower:
                    if 'red' in class_lower:
                        color_counts['red-rock'] += 1
                    elif 'yellow' in class_lower:
                        color_counts['yellow-rock'] += 1
                    elif 'blue' in class_lower:
                        color_counts['blue-rock'] += 1
                    elif 'white' in class_lower:
                        color_counts['white-rock'] += 1
                    else:
                        color_counts[class_lower] += 1
        
        top_colors = [c[0] for c in color_counts.most_common(2)]
        return top_colors, dict(color_counts)
    
    def _classify_perspective(self, resolution: Tuple[int, int],
                               button_pos: Tuple[float, float],
                               house_size: float,
                               frames_with_dets: int,
                               total_frames: int) -> Tuple[str, float]:
        """
        Classify camera perspective from resolution and detections.
        
        Returns:
            (perspective_type, confidence)
            perspective: 'near', 'far', 'wide', 'unknown'
        """
        width, height = resolution
        det_rate = frames_with_dets / total_frames if total_frames > 0 else 0
        
        # Portrait orientation (height > width) = near or far camera
        if height > width:
            # Near camera: button closer to bottom
            # Far camera: button more centered
            btn_x_ratio = button_pos[0] / width if button_pos[0] > 0 else 0.5
            btn_y_ratio = button_pos[1] / height if button_pos[1] > 0 else 0.5
            
            if btn_y_ratio > 0.6:
                # Button in lower third = near camera (looking down at near house)
                return ('near', 0.8 if det_rate > 0.5 else 0.5)
            elif btn_y_ratio > 0.3:
                # Button in middle = far camera
                return ('far', 0.7 if det_rate > 0.5 else 0.4)
            else:
                # Button at top = unknown portrait
                return ('unknown', 0.3)
        
        else:
            # Landscape orientation = wide camera
            # Wide cameras typically don't see button clearly
            if house_size > 0 and house_size < min(width, height) * 0.3:
                return ('wide', 0.6)
            else:
                return ('wide', 0.4)
    
    def _compute_score_radius(self, resolution: Tuple[int, int],
                               button_pos: Tuple[float, float],
                               house_size: float,
                               perspective: str) -> float:
        """
        Compute scoring radius in pixels.
        
        The scoring radius defines how far from button we consider for scoring.
        Standard house is 12ft diameter, button is ~1ft.
        Ratio: house_radius / button_radius ≈ 12
        
        We derive this from house_size if available, or from resolution if not.
        """
        width, height = resolution
        min_dim = min(width, height)
        
        if house_size > 0:
            # House size detected - use it
            # Scoring radius is ~45% of house diameter (the rings)
            return house_size * 0.45
        else:
            # No house detected - estimate from resolution
            # Standard curling sheet: house takes ~40% of frame height in portrait
            # Score radius is ~15% of frame height
            if perspective in ('near', 'far'):
                return height * 0.15
            else:
                return min_dim * 0.1
    
    def _assess_quality(self, button_samples: int, house_samples: int,
                        team_colors: List[str],
                        frames_with_dets: int, total_frames: int) -> Tuple[float, List[str]]:
        """Assess calibration quality and generate warnings."""
        warnings = []
        scores = []
        
        # Button detection quality
        if button_samples >= 10:
            scores.append(1.0)
        elif button_samples >= 5:
            scores.append(0.7)
            warnings.append(f"Low button detections ({button_samples})")
        elif button_samples > 0:
            scores.append(0.4)
            warnings.append(f"Very low button detections ({button_samples})")
        else:
            scores.append(0.0)
            warnings.append("No button detected")
        
        # House detection quality
        if house_samples >= 5:
            scores.append(1.0)
        elif house_samples >= 2:
            scores.append(0.6)
        elif house_samples > 0:
            scores.append(0.3)
            warnings.append(f"Low house detections ({house_samples})")
        else:
            scores.append(0.2)
            warnings.append("No house detected")
        
        # Team color detection
        if len(team_colors) >= 2:
            scores.append(1.0)
        elif len(team_colors) == 1:
            scores.append(0.5)
            warnings.append("Only one team color detected")
        else:
            scores.append(0.1)
            warnings.append("No team colors detected")
        
        # Detection rate
        det_rate = frames_with_dets / total_frames if total_frames > 0 else 0
        if det_rate >= 0.5:
            scores.append(1.0)
        elif det_rate >= 0.2:
            scores.append(0.6)
        else:
            scores.append(0.3)
            warnings.append(f"Low detection rate ({det_rate:.1%})")
        
        quality = sum(scores) / len(scores)
        return (quality, warnings)
    
    def _print_summary(self):
        """Print calibration summary."""
        if not self.calibration:
            return
        
        c = self.calibration
        print(f"\n{'='*60}")
        print(f"CALIBRATION RESULTS")
        print(f"{'='*60}")
        print(f"Source: {c.source}")
        print(f"Type: {c.source_type}")
        print(f"Resolution: {c.resolution[0]}x{c.resolution[1]}")
        print(f"Perspective: {c.perspective} ({c.perspective_confidence:.0%})")
        print()
        print(f"Button: ({c.button_position[0]:.1f}, {c.button_position[1]:.1f})")
        print(f"  Confidence: {c.button_confidence:.0%}")
        print(f"  Samples: {c.button_samples}")
        print()
        print(f"House Size: {c.house_size:.1f} px")
        print(f"  Samples: {c.house_samples}")
        print(f"Score Radius: {c.score_radius:.1f} px")
        print()
        print(f"Team Colors: {c.team_colors}")
        print(f"Color Counts: {c.team_color_counts}")
        print()
        print(f"Quality Score: {c.quality_score:.0%}")
        if c.warnings:
            print(f"Warnings:")
            for w in c.warnings:
                print(f"  ⚠ {w}")
        print(f"Frames: {c.frames_analyzed} analyzed, {c.frames_with_detections} with detections")
        print(f"Time: {c.calibration_time_ms:.0f}ms")
        print(f"{'='*60}\n")
    
    def save(self, filepath: str):
        """Save calibration to JSON."""
        if not self.calibration:
            raise ValueError("No calibration to save")
        
        with open(filepath, 'w') as f:
            json.dump(self.calibration.to_dict(), f, indent=2)
        print(f"Calibration saved to {filepath}")
    
    def load(self, filepath: str) -> UniversalCalibration:
        """Load calibration from JSON."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.calibration = UniversalCalibration.from_dict(data)
        return self.calibration
    
    def get_game_tracker_config(self) -> Dict:
        """Get calibration parameters for game_tracker.py."""
        if not self.calibration:
            raise ValueError("No calibration available")
        
        c = self.calibration
        return {
            'button': list(c.button_position),
            'house_size': c.house_size,
            'score_radius': c.score_radius,
            'team_colors': c.team_colors,
            'resolution': list(c.resolution),
            'perspective': c.perspective,
            'source': c.source,
            'quality': c.quality_score,
            'calibration_time_ms': c.calibration_time_ms
        }


def calibrate_video(source: str, frames: int = 50, skip: int = 10,
                    verbose: bool = True, save_path: Optional[str] = None) -> UniversalCalibration:
    """Convenience function to calibrate a video."""
    calibrator = UniversalCalibrator()
    return calibrator.analyze_video(source, frames=frames, skip=skip, 
                                    verbose=verbose, save_path=save_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Universal auto-calibration for curling videos")
    parser.add_argument("source", help="Video source (file, RTSP, YouTube URL)")
    parser.add_argument("--frames", type=int, default=50, help="Frames to analyze")
    parser.add_argument("--skip", type=int, default=10, help="Frames to skip between samples")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
    
    args = parser.parse_args()
    
    calibrator = UniversalCalibrator()
    calibrator.analyze_video(
        args.source,
        frames=args.frames,
        skip=args.skip,
        verbose=not args.quiet
    )
    
    if args.output:
        calibrator.save(args.output)