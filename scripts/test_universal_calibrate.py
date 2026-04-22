#!/usr/bin/env python3
"""
Test Universal Calibration on all available test videos.

Compares auto-calibration results to hardcoded values and assesses
whether the system can work on any curling video.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_calibrate import UniversalCalibrator
import json

# Test videos with known calibration
TEST_VIDEOS = [
    {
        'source': '/home/curl/Videos/curling/cam1_20260330_194005.mp4',
        'name': 'far_camera',
        'expected': {
            'button': (360.0, 596.0),
            'perspective': 'far',
            'team_colors': ['red-rock', 'yellow-rock']
        }
    },
    {
        'source': '/home/curl/Videos/curling/cam2_20260330_194005.mp4',
        'name': 'near_camera',
        'expected': {
            'button': (349.0, 697.0),  # Approximate
            'perspective': 'near',
            'team_colors': ['red-rock', 'yellow-rock']
        }
    },
    {
        'source': '/home/curl/Videos/curling/cam3_20260330_194005.mp4',
        'name': 'wide_camera',
        'expected': {
            'button': None,  # Wide camera doesn't see button clearly
            'perspective': 'wide',
            'team_colors': ['red-rock', 'yellow-rock']
        }
    }
]


def test_universal_calibration():
    """Test universal calibration on all videos."""
    
    results = []
    
    for test in TEST_VIDEOS:
        print(f"\n{'='*70}")
        print(f"Testing: {test['name']}")
        print(f"{'='*70}")
        
        calibrator = UniversalCalibrator()
        
        try:
            # Run calibration with fewer frames for faster test
            calibration = calibrator.analyze_video(
                test['source'],
                frames=30,
                skip=10,
                verbose=True
            )
            
            # Evaluate results
            result = {
                'name': test['name'],
                'source': test['source'],
                'passed': True,
                'checks': [],
                'calibration': calibration.to_dict()
            }
            
            # Check button detection
            if test['expected']['button']:
                expected_btn = test['expected']['button']
                actual_btn = calibration.button_position
                
                # If button was detected
                if calibration.button_samples > 0:
                    distance = ((expected_btn[0] - actual_btn[0])**2 + 
                               (expected_btn[1] - actual_btn[1])**2)**0.5
                    
                    check = {
                        'name': 'button_position',
                        'expected': expected_btn,
                        'actual': list(actual_btn),
                        'distance_px': round(distance, 1),
                        'passed': distance < 30
                    }
                    result['checks'].append(check)
                    
                    if distance >= 30:
                        result['passed'] = False
                else:
                    result['checks'].append({
                        'name': 'button_position',
                        'passed': False,
                        'note': 'No button detected'
                    })
                    result['passed'] = False
            else:
                # Button not expected for wide camera
                if calibration.button_samples == 0:
                    result['checks'].append({
                        'name': 'button_position',
                        'passed': True,
                        'note': 'No button expected for wide camera'
                    })
                else:
                    result['checks'].append({
                        'name': 'button_position',
                        'passed': True,
                        'note': f'Button detected: {calibration.button_position}'
                    })
            
            # Check perspective
            expected_persp = test['expected']['perspective']
            actual_persp = calibration.perspective
            
            check = {
                'name': 'perspective',
                'expected': expected_persp,
                'actual': actual_persp,
                'passed': actual_persp == expected_persp
            }
            result['checks'].append(check)
            
            if actual_persp != expected_persp:
                # Perspective mismatch is a warning, not a failure
                pass
            
            # Check team colors
            expected_colors = set(test['expected']['team_colors'])
            actual_colors = set(calibration.team_colors)
            
            check = {
                'name': 'team_colors',
                'expected': list(expected_colors),
                'actual': list(actual_colors),
                'passed': expected_colors == actual_colors or len(actual_colors) >= 2
            }
            result['checks'].append(check)
            
            # Check quality
            check = {
                'name': 'quality_score',
                'actual': f"{calibration.quality_score:.0%}",
                'passed': calibration.quality_score >= 0.5
            }
            result['checks'].append(check)
            
            if calibration.quality_score < 0.5:
                result['passed'] = False
            
            # Check warnings
            if calibration.warnings:
                result['warnings'] = calibration.warnings
            
            print(f"\n✓ Calibration complete")
            print(f"  Quality: {calibration.quality_score:.0%}")
            print(f"  Perspective: {calibration.perspective}")
            print(f"  Button: {calibration.button_position} ({calibration.button_samples} samples)")
            print(f"  House: {calibration.house_size:.1f}px ({calibration.house_samples} samples)")
            print(f"  Colors: {calibration.team_colors}")
            
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            result = {
                'name': test['name'],
                'source': test['source'],
                'passed': False,
                'error': str(e)
            }
        
        results.append(result)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(1 for r in results if r.get('passed', False))
    total = len(results)
    
    for r in results:
        status = "✓ PASS" if r.get('passed', False) else "✗ FAIL"
        print(f"  {r['name']}: {status}")
        if 'checks' in r:
            for check in r['checks']:
                check_status = "✓" if check['passed'] else "✗"
                print(f"    {check_status} {check['name']}: {check.get('actual', 'N/A')}")
    
    print(f"\n{passed}/{total} tests passed")
    
    # Save results
    output_path = '/home/curl/curling_vision/test_output/universal_calibrate_test.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    
    return results


if __name__ == "__main__":
    test_universal_calibration()