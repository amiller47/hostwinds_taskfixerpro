#!/usr/bin/env python3
"""Test motion-based throw detection."""
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_tracker import GameTracker, MotionBasedThrowDetector, Rock, RockState

def test_motion_detector():
    """Test the MotionBasedThrowDetector class."""
    print("Testing MotionBasedThrowDetector")
    print("=" * 60)
    
    detector = MotionBasedThrowDetector(velocity_threshold=50.0)
    
    # Test 1: No rocks, no throw
    rocks = []
    started, reason = detector.detect_throw_start(rocks, 0.0)
    print(f"Test 1 - Empty frame: started={started}, reason={reason}")
    assert not started, "Should not detect throw with no rocks"
    
    # Test 2: One rock appears (new rock detection)
    rocks = [Rock(id=0, x=100, y=100, color="red", confidence=0.9)]
    started, reason = detector.detect_throw_start(rocks, 1.0)
    print(f"Test 2 - First rock: started={started}, reason={reason}")
    assert started, "Should detect throw when rock appears"
    assert reason == "new_rock", f"Reason should be 'new_rock', got {reason}"
    
    # Test 3: Rock is moving (velocity detection)
    # Need to have rock count match prev_rock_count to trigger velocity, not new_rock
    detector.reset()
    detector.prev_rock_count = {"red": 1, "yellow": 0}  # Pretend we already have 1 red rock
    rocks = [Rock(id=0, x=100, y=100, color="red", confidence=0.9, vx=100, vy=50)]
    started, reason = detector.detect_throw_start(rocks, 2.0)
    print(f"Test 3 - Moving rock: started={started}, reason={reason}")
    assert started, "Should detect throw when rock moves"
    assert reason == "velocity", f"Reason should be 'velocity', got {reason}"
    
    # Test 4: Throw completion
    detector.throw_in_progress = True
    rocks = [Rock(id=0, x=100, y=100, color="red", confidence=0.9, vx=0, vy=0)]
    complete = detector.detect_throw_complete(rocks, 3.0, min_settle_frames=2)
    print(f"Test 4 - Stationary rock (1 frame): complete={complete}")
    
    # Need more frames for completion
    complete = detector.detect_throw_complete(rocks, 3.1, min_settle_frames=2)
    print(f"Test 5 - Stationary rock (2 frames): complete={complete}")
    assert complete, "Should complete throw after settle frames"
    
    print()
    print("All tests passed!")
    

def test_game_tracker_integration():
    """Test GameTracker with motion detection enabled."""
    print("\nTesting GameTracker integration")
    print("=" * 60)
    
    calibration = {
        "near": {"button": (207, 375), "house_size": 400},
        "far": {"button": (222, 374), "house_size": 400}
    }
    config = {}
    
    tracker = GameTracker(calibration, config)
    
    # Verify motion detector is enabled
    assert hasattr(tracker, 'motion_detector'), "Should have motion_detector"
    assert hasattr(tracker, 'use_motion_detection'), "Should have use_motion_detection flag"
    print(f"Motion detection enabled: {tracker.use_motion_detection}")
    
    # Simulate detection sequence
    print("\nSimulating rock appearing (throw)...")
    import time
    now = time.time()
    
    # Frame 1: No rocks
    tracker.process_detections([], "near", now)
    state = tracker.get_state()
    print(f"Frame 1: state={state['state']}, throws={state['total_throws']}")
    
    # Frame 2: Rock appears (simulating thrown rock)
    detections = [{"class": "red-rock", "x": 100, "y": 100, "confidence": 0.9}]
    tracker.process_detections(detections, "near", now + 0.1)
    state = tracker.get_state()
    print(f"Frame 2: state={state['state']}, throws={state['total_throws']}")
    
    # Frame 3-5: Rock settles
    for i in range(3):
        tracker.process_detections(detections, "near", now + 0.2 + i * 0.1)
        state = tracker.get_state()
        print(f"Frame {3+i}: state={state['state']}, throws={state['total_throws']}")
    
    print()
    print("Integration test complete!")
    print(f"Final state: {tracker.get_state()}")
    print(f"Events: {len(tracker.events)} logged")
    for event in tracker.events[-5:]:
        print(f"  {event['event']}: {event.get('details', {})}")


if __name__ == "__main__":
    test_motion_detector()
    test_game_tracker_integration()