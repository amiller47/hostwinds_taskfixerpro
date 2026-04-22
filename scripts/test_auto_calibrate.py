#!/usr/bin/env python3
"""
Test script for Auto-Calibration Module

Tests the auto-calibration on our existing test videos to validate:
1. Button detection accuracy
2. House size estimation
3. Team color detection
4. Perspective estimation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_calibrate import AutoCalibrator, CalibrationProfile
import json

def test_auto_calibrate():
    """Test auto-calibration on existing test videos."""

    test_videos = [
        {
            'source': '/home/curl/Videos/curling/cam1_20260330_194005.mp4',
            'name': 'far_camera',
            'expected_button': (360.0, 596.0),  # From calibration.json
            'expected_house_size': 748.0
        },
        {
            'source': '/home/curl/Videos/curling/cam2_20260330_194005.mp4',
            'name': 'near_camera',
            'expected_button': (349.0, 697.0),  # Estimated from calibration.json
            'expected_house_size': 748.0
        },
        {
            'source': '/home/curl/Videos/curling/cam3_20260330_194005.mp4',
            'name': 'wide_camera',
            'expected_button': (637.0, 134.0),  # From calibration.json
            'expected_house_size': None  # Unknown for wide
        }
    ]

    results = []

    for test in test_videos:
        print(f"\n{'='*60}")
        print(f"Testing: {test['name']}")
        print(f"Source: {test['source']}")
        print(f"{'='*60}")

        calibrator = AutoCalibrator()

        try:
            # Analyze first 50 frames (skip 10 = sample every 10th frame)
            profile = calibrator.analyze_video(
                test['source'],
                frames=30,  # 30 frames for quick test
                skip=10,    # Sample every 10 frames
                verbose=True
            )

            # Compare with expected
            if test['expected_button']:
                expected_btn = test['expected_button']
                actual_btn = profile.button_position
                distance = ((expected_btn[0] - actual_btn[0])**2 + 
                           (expected_btn[1] - actual_btn[1])**2)**0.5
                print(f"\nButton Position Accuracy:")
                print(f"  Expected: ({expected_btn[0]:.1f}, {expected_btn[1]:.1f})")
                print(f"  Actual:   ({actual_btn[0]:.1f}, {actual_btn[1]:.1f})")
                print(f"  Distance: {distance:.1f} px")

                if distance < 30:
                    print(f"  ✓ PASS (within 30px tolerance)")
                else:
                    print(f"  ✗ FAIL (outside 30px tolerance)")

            if test['expected_house_size']:
                expected_size = test['expected_house_size']
                actual_size = profile.house_size
                diff = abs(expected_size - actual_size)
                print(f"\nHouse Size Accuracy:")
                print(f"  Expected: {expected_size:.1f} px")
                print(f"  Actual:   {actual_size:.1f} px")
                print(f"  Difference: {diff:.1f} px ({100*diff/expected_size:.1f}%)")

                if diff / expected_size < 0.2:  # Within 20%
                    print(f"  ✓ PASS (within 20% tolerance)")
                else:
                    print(f"  ✗ FAIL (outside 20% tolerance)")

            print(f"\nTeam Colors: {profile.team_colors}")
            print(f"Color Counts: {profile.team_color_counts}")
            print(f"Perspective: {profile.perspective} ({profile.perspective_confidence:.2f})")

            # Save results
            result = {
                'name': test['name'],
                'source': test['source'],
                'button_position': list(profile.button_position),
                'button_confidence': profile.button_confidence,
                'house_size': profile.house_size,
                'team_colors': profile.team_colors,
                'perspective': profile.perspective,
                'frames_analyzed': profile.frames_analyzed,
                'calibration_time_ms': profile.calibration_time_ms
            }
            results.append(result)

        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                'name': test['name'],
                'source': test['source'],
                'error': str(e)
            })

    # Save test results
    output_path = '/home/curl/curling_vision/test_output/auto_calibrate_test.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Test results saved to: {output_path}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    test_auto_calibrate()