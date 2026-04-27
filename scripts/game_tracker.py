#!/usr/bin/env python3
"""
Curling Game State Tracker
Processes detections and tracks game flow through a state machine.
"""

import json
import time
import math
import sys
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Add scripts directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Shot classification
from shot_classifier import ShotClassifier, ShotType, RockState, format_shot_result

# Trajectory prediction
from trajectory_predictor import TrajectoryPredictor, PredictedPosition, format_prediction, IceConditions


class GameState(Enum):
    IDLE = "idle"
    DELIVERY_IN_PROGRESS = "delivery_in_progress"
    ROCK_IN_FLIGHT = "rock_in_flight"
    ROCKS_SETTLING = "rocks_settling"
    THROW_COMPLETE = "throw_complete"
    END_COMPLETE = "end_complete"


@dataclass
class Rock:
    """Tracked rock with position and velocity."""
    id: int
    x: float
    y: float
    color: str  # "red" or "yellow"
    confidence: float
    vx: float = 0.0  # velocity x
    vy: float = 0.0  # velocity y
    last_seen: float = 0.0
    stationary_frames: int = 0
    frames_seen: int = 0

    def speed(self) -> float:
        return math.sqrt(self.vx**2 + self.vy**2)


@dataclass
class TrackedDelivery:
    """Tracked delivery (person throwing)."""
    x: float
    y: float
    confidence: float
    first_seen: float
    last_seen: float
    frame_count: int = 1


class RockTracker:
    """Track rocks across frames with velocity estimation."""

    def __init__(self, max_lost_frames: int = 10, velocity_threshold: float = 5.0):
        self.rocks: Dict[int, Rock] = {}
        self.next_id = 0
        self.max_lost_frames = max_lost_frames
        self.velocity_threshold = velocity_threshold
        self.position_history: Dict[int, List[Tuple[float, float, float]]] = defaultdict(list)  # id -> [(x, y, t)]

    def update(self, detections: List[dict], timestamp: float) -> List[Rock]:
        """
        Update rock tracking with new detections.
        Returns list of currently tracked rocks.
        """
        # Match detections to existing rocks
        matched_rocks = set()
        new_rocks = []

        for det in detections:
            if det.get("class") not in ["red-rock", "yellow-rock"]:
                continue

            x, y = det.get("x", 0), det.get("y", 0)
            color = "red" if "red" in det.get("class", "") else "yellow"
            conf = det.get("confidence", 0)

            # Find closest existing rock of same color
            best_match = None
            best_dist = float("inf")

            for rock_id, rock in self.rocks.items():
                if rock.color != color:
                    continue
                dist = math.sqrt((rock.x - x)**2 + (rock.y - y)**2)
                if dist < best_dist and dist < 150:  # 150px threshold for fast-moving rocks
                    best_match = rock_id
                    best_dist = dist

            if best_match is not None:
                # Update existing rock
                rock = self.rocks[best_match]

                # Calculate velocity from position history
                if len(self.position_history[best_match]) > 0:
                    prev_x, prev_y, prev_t = self.position_history[best_match][-1]
                    dt = timestamp - prev_t
                    if dt > 0:
                        rock.vx = (x - prev_x) / dt
                        rock.vy = (y - prev_y) / dt

                # Update position history
                self.position_history[best_match].append((x, y, timestamp))
                if len(self.position_history[best_match]) > 10:
                    self.position_history[best_match] = self.position_history[best_match][-10:]

                rock.x = x
                rock.y = y
                rock.confidence = conf
                rock.last_seen = timestamp
                rock.frames_seen += 1

                # Check if stationary
                if rock.speed() < self.velocity_threshold:
                    rock.stationary_frames += 1
                else:
                    rock.stationary_frames = 0

                matched_rocks.add(best_match)
            else:
                # New rock
                new_rock = Rock(
                    id=self.next_id,
                    x=x,
                    y=y,
                    color=color,
                    confidence=conf,
                    last_seen=timestamp
                )
                self.rocks[self.next_id] = new_rock
                self.position_history[self.next_id].append((x, y, timestamp))
                new_rocks.append(self.next_id)
                self.next_id += 1

        # Remove rocks not seen recently
        to_remove = []
        for rock_id, rock in self.rocks.items():
            if timestamp - rock.last_seen > self.max_lost_frames * 0.1:  # Assume ~10fps
                to_remove.append(rock_id)

        for rock_id in to_remove:
            del self.rocks[rock_id]
            del self.position_history[rock_id]

        return list(self.rocks.values())

    def get_moving_rocks(self) -> List[Rock]:
        """Return rocks currently in motion."""
        return [r for r in self.rocks.values() if r.speed() > self.velocity_threshold]

    def get_stationary_rocks(self) -> List[Rock]:
        """Return rocks that have been stationary."""
        return [r for r in self.rocks.values() if r.stationary_frames > 0]

    def get_all_rocks(self) -> List[Rock]:
        return list(self.rocks.values())

    def clear(self):
        """Clear all tracking."""
        self.rocks.clear()
        self.position_history.clear()
        self.next_id = 0


class DeliveryTracker:
    """Track deliveries (curlers throwing)."""

    def __init__(self, min_frames: int = 2, max_gap: float = 1.0):
        self.current_delivery: Optional[TrackedDelivery] = None
        self.min_frames = min_frames
        self.max_gap = max_gap  # seconds
        self.delivery_history: List[TrackedDelivery] = []

    def update(self, detections: List[dict], timestamp: float) -> Tuple[bool, bool]:
        """
        Update delivery tracking.
        Returns (delivery_active, delivery_just_ended)
        """
        # Find delivery in detections
        delivery_det = None
        for det in detections:
            class_name = det.get("class", "").lower()
            # Check for both "curling delivery" and "delivery"
            if "delivery" in class_name:
                delivery_det = det
                break

        delivery_just_ended = False

        if delivery_det is not None:
            # Delivery detected
            x, y = delivery_det.get("x", 0), delivery_det.get("y", 0)
            conf = delivery_det.get("confidence", 0)

            # Lower confidence threshold for better detection
            if conf >= 0.5:  # Was 0.7
                if self.current_delivery is None:
                    # New delivery started
                    self.current_delivery = TrackedDelivery(
                        x=x, y=y,
                        confidence=conf,
                        first_seen=timestamp,
                        last_seen=timestamp
                    )
                else:
                    # Update existing delivery
                    self.current_delivery.x = x
                    self.current_delivery.y = y
                    self.current_delivery.confidence = conf
                    self.current_delivery.last_seen = timestamp
                    self.current_delivery.frame_count += 1
        else:
            # No delivery detected
            if self.current_delivery is not None:
                # Check if delivery ended
                if timestamp - self.current_delivery.last_seen > self.max_gap:
                    # Delivery ended
                    if self.current_delivery.frame_count >= self.min_frames:
                        delivery_just_ended = True
                        self.delivery_history.append(self.current_delivery)
                    self.current_delivery = None

        delivery_active = self.current_delivery is not None
        return delivery_active, delivery_just_ended


class MotionBasedThrowDetector:
    """
    Detect throws based on rock motion when delivery class is unavailable.
    
    Fallback mechanism for models that don't have a "curling delivery" class.
    Detects throws by:
    1. New rock appearing in frame
    2. Rock velocity exceeding threshold
    3. Rock count changes over time
    """
    
    def __init__(self, velocity_threshold: float = 50.0, min_frames_moving: int = 2):
        self.velocity_threshold = velocity_threshold  # pixels per frame
        self.min_frames_moving = min_frames_moving
        
        # Track previous rock states
        self.prev_rock_count = {"red": 0, "yellow": 0}
        self.throw_in_progress = False
        self.throw_start_time = 0.0
        self.moving_rock_id = None
        self.frames_since_motion = 0
        
        # History for debugging
        self.throw_events: List[dict] = []
    
    def detect_throw_start(
        self, 
        rocks: List[Rock], 
        timestamp: float,
        delivery_active: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect if a throw has started based on rock motion.
        
        Returns (throw_started, reason) where reason is:
        - "delivery": delivery class detected (passed through)
        - "new_rock": new rock appeared
        - "velocity": rock velocity exceeded threshold
        - None: no throw detected
        """
        # If delivery is active, pass through
        if delivery_active:
            return False, None
        
        # Count rocks by color
        rock_count = {"red": 0, "yellow": 0}
        for rock in rocks:
            if rock.color == "red":
                rock_count["red"] += 1
            else:
                rock_count["yellow"] += 1
        
        # Check for moving rocks FIRST (higher priority than new rock)
        # This catches rocks that are already being tracked
        moving_rocks = [r for r in rocks if r.speed() > self.velocity_threshold]
        if moving_rocks:
            if not self.throw_in_progress:
                self.throw_in_progress = True
                self.throw_start_time = timestamp
                self.frames_since_motion = 0
                self.moving_rock_id = moving_rocks[0].id
                self.prev_rock_count = rock_count.copy()
                return True, "velocity"
        
        # Check for new rocks (throw started)
        for color in ["red", "yellow"]:
            if rock_count[color] > self.prev_rock_count[color]:
                self.throw_in_progress = True
                self.throw_start_time = timestamp
                self.frames_since_motion = 0
                self.prev_rock_count = rock_count.copy()
                return True, "new_rock"
        
        self.prev_rock_count = rock_count.copy()
        return False, None
    
    def detect_throw_complete(
        self, 
        rocks: List[Rock], 
        timestamp: float,
        min_settle_frames: int = 3
    ) -> bool:
        """
        Detect if thrown rocks have settled.
        
        Returns True if all rocks are stationary for min_settle_frames.
        """
        if not self.throw_in_progress:
            return False
        
        # Check if all rocks are stationary
        moving_rocks = [r for r in rocks if r.speed() > self.velocity_threshold]
        
        if not moving_rocks:
            self.frames_since_motion += 1
            if self.frames_since_motion >= min_settle_frames:
                return True
        else:
            self.frames_since_motion = 0
        
        return False
    
    def end_throw(self):
        """Mark the throw as complete and reset state."""
        self.throw_in_progress = False
        self.moving_rock_id = None
        self.frames_since_motion = 0
    
    def reset(self):
        """Reset all tracking state."""
        self.prev_rock_count = {"red": 0, "yellow": 0}
        self.throw_in_progress = False
        self.throw_start_time = 0.0
        self.moving_rock_id = None
        self.frames_since_motion = 0



@dataclass
class GameScore:
    """Score for a single end."""
    end: int
    red: int
    yellow: int
    rocks_in_house: Dict[str, List[Tuple[float, float]]]  # color -> [(x, y)]


class GameTracker:
    """Main game state machine."""

    def __init__(self, calibration: dict, config: dict):
        self.calibration = calibration
        self.config = config
        
        # Persistent detections for dashboard (prevents flickering)
        self.last_detections: Dict[str, List] = {"far": [], "near": []}

        # State
        self.state = GameState.IDLE
        self.current_end = 1
        self.hammer = "team_yellow"  # Team with hammer this end
        self.possession = "team_red"  # Team throwing next
        self.scores = {"team_red": 0, "team_yellow": 0}
        self.end_scores: List[GameScore] = []
        self.throws = {"team_red": 0, "team_yellow": 0}
        self.total_throws = 0
        
        # End-based camera selection
        # Odd ends (1,3,5...) throw to FAR end, Even ends (2,4,6...) throw to NEAR end
        self.end_camera_map = {
            "far": [1, 3, 5, 7, 9, 11],   # Far camera active for odd ends
            "near": [2, 4, 6, 8, 10, 12]  # Near camera active for even ends
        }
        
        # Shot tracking for classification
        self.rock_state_before_throw: List[RockState] = []
        self.last_shot_type: Optional[str] = None
        self.shot_history: List[dict] = []

        # Rock tracking (separate for near/far)
        self.near_tracker = RockTracker()
        self.far_tracker = RockTracker()
        self.wide_tracker = RockTracker()  # Wide camera sees both houses
        
        # Shot classifier
        house_radius = calibration.get("near", {}).get("house_size", 748) // 2
        self.shot_classifier = ShotClassifier(house_radius=house_radius)

        # Delivery tracking
        self.delivery_tracker = DeliveryTracker()
        
        # Motion-based throw detection (fallback when delivery class unavailable)
        self.motion_detector = MotionBasedThrowDetector(
            velocity_threshold=50.0,  # pixels per frame
            min_frames_moving=2
        )
        self.use_motion_detection = True  # Set False if delivery class available
        
        # Trajectory prediction (requires 5+ fps for accuracy)
        self.trajectory_predictor = TrajectoryPredictor(
            ice_conditions=IceConditions.default(),
            frame_rate=6.0
        )

        # Timing
        self.last_update = 0.0
        self.state_entered_time = 0.0
        self.last_throw_time = 0.0
        
        # Inactivity timeout for end completion (seconds)
        self.inactivity_timeout = 60.0  # End after 60s of no activity (was 30s, too aggressive for video)
        self.last_activity_time = 0.0

        # Log
        self.events: List[dict] = []

    def _log_event(self, event_type: str, details: dict = None):
        """Log a game event."""
        self.events.append({
            "time": time.time(),
            "state": self.state.value,
            "event": event_type,
            "details": details or {}
        })

    def _get_active_tracker(self, camera: str) -> RockTracker:
        """Get the appropriate rock tracker for the camera."""
        return self.near_tracker if camera == "near" else self.far_tracker
    
    def get_active_camera_for_end(self) -> str:
        """
        Get which camera should be active for the current end.
        
        In curling:
        - Odd ends (1,3,5...): Teams throw to FAR end → far camera
        - Even ends (2,4,6...): Teams throw to NEAR end → near camera
        
        Returns: 'far' or 'near'
        """
        if self.current_end % 2 == 1:  # Odd end
            return "far"
        else:  # Even end
            return "near"

    def _calculate_distance_from_button(self, rock: Rock, camera: str) -> float:
        """Calculate distance from button in pixels."""
        button = self.calibration.get(camera, {}).get("button")
        if button is None:
            return float("inf")

        return math.sqrt((rock.x - button[0])**2 + (rock.y - button[1])**2)

    def _is_in_house(self, rock: Rock, camera: str) -> bool:
        """Check if rock is in the house."""
        house_size = self.calibration.get(camera, {}).get("house_size") or self.calibration.get(camera, {}).get("house_size_estimate")
        if house_size is None:
            return False

        dist = self._calculate_distance_from_button(rock, camera)
        return dist < (house_size / 2)

    def _calculate_score(self, camera: str) -> GameScore:
        """Calculate score for current state."""
        tracker = self._get_active_tracker(camera)
        rocks = tracker.get_all_rocks()

        # Get rocks in house
        rocks_in_house = {"red": [], "yellow": []}
        distances = []

        for rock in rocks:
            if self._is_in_house(rock, camera):
                dist = self._calculate_distance_from_button(rock, camera)
                rocks_in_house[rock.color].append((rock.x, rock.y))
                distances.append((dist, rock.color))

        if not distances:
            return GameScore(
                end=self.current_end,
                red=0, yellow=0,
                rocks_in_house=rocks_in_house
            )

        # Sort by distance
        distances.sort(key=lambda x: x[0])

        # Determine scoring
        closest_color = distances[0][1]
        opponent_color = "yellow" if closest_color == "red" else "red"

        # Count scoring rocks
        points = 0
        opponent_closest = float("inf")

        for dist, color in distances:
            if color != closest_color:
                opponent_closest = min(opponent_closest, dist)
            if dist >= opponent_closest:
                break
            points += 1

        return GameScore(
            end=self.current_end,
            red=points if closest_color == "red" else 0,
            yellow=points if closest_color == "yellow" else 0,
            rocks_in_house=rocks_in_house
        )

    def process_detections(self, detections: List[dict], camera: str, timestamp: float):
        """
        Process detections from a camera and update game state.
        This is the main entry point for the state machine.
        """
        self.last_update = timestamp

        # Store detections for dashboard (prevents flickering)
        det_list = [[d["class"], d["x"], d["y"], d["confidence"]] for d in detections]
        self.last_detections[camera] = det_list

        # Update rock tracking
        tracker = self._get_active_tracker(camera)
        rocks = tracker.update(detections, timestamp)
        
        # Update trajectory predictions for all tracked rocks
        for rock in rocks:
            self.trajectory_predictor.update_rock(
                rock.id, rock.x, rock.y, timestamp
            )

        # Update delivery tracking
        delivery_active, delivery_ended = self.delivery_tracker.update(detections, timestamp)

        # State machine transitions
        self._update_state(camera, delivery_active, delivery_ended, timestamp)

    def process_wide_detections(self, detections: List[dict], timestamp: float):
        """
        Process detections from wide camera (sees both houses).
        Wide camera is used for scoring validation, not state tracking.
        """
        # Update wide tracker with all rock detections
        self.wide_tracker.update(detections, timestamp)
        
        # Wide camera provides additional scoring data
        # This can be used to cross-validate near/far camera scoring
        self._log_event("wide_update", {
            "rocks_detected": len([d for d in detections if "rock" in d.get("class", "")]),
            "timestamp": timestamp
        })

    def _update_state(self, camera: str, delivery_active: bool, delivery_ended: bool, timestamp: float):
        """Update state machine based on current conditions."""

        # Get current rock state for motion detection
        tracker = self._get_active_tracker(camera)
        rocks = tracker.get_all_rocks()

        if self.state == GameState.IDLE:
            # Check for inactivity timeout (end complete if no throws for a while)
            if self.total_throws > 0 and self.last_activity_time > 0:
                if timestamp - self.last_activity_time > self.inactivity_timeout:
                    self._log_event("inactivity_timeout", {
                        "elapsed": timestamp - self.last_activity_time,
                        "throws": self.total_throws
                    })
                    self._transition_to(GameState.END_COMPLETE, timestamp)
                    return
            
            # Try delivery detection first, then motion-based fallback
            if delivery_active:
                # Capture rock state before throw for shot classification
                self._capture_rock_state_before(camera)
                self._transition_to(GameState.DELIVERY_IN_PROGRESS, timestamp)
                self._log_event("delivery_started", {"camera": camera, "method": "delivery_class"})
            elif self.use_motion_detection:
                # Motion-based throw detection (fallback when delivery class unavailable)
                throw_started, reason = self.motion_detector.detect_throw_start(
                    rocks, timestamp, delivery_active
                )
                if throw_started:
                    self._capture_rock_state_before(camera)
                    self._transition_to(GameState.ROCK_IN_FLIGHT, timestamp)
                    self._log_event("throw_started", {"camera": camera, "method": "motion", "reason": reason})

        elif self.state == GameState.DELIVERY_IN_PROGRESS:
            if delivery_ended:
                self._transition_to(GameState.ROCK_IN_FLIGHT, timestamp)
                self._log_event("throw_released", {"camera": camera})
            elif not delivery_active and (timestamp - self.state_entered_time) > 3.0:
                # Timeout - assume throw happened
                self._transition_to(GameState.ROCK_IN_FLIGHT, timestamp)
                self._log_event("throw_released_timeout", {"camera": camera})

        elif self.state == GameState.ROCK_IN_FLIGHT:
            moving = tracker.get_moving_rocks()
            elapsed = timestamp - self.state_entered_time

            # Check for throw completion via motion detector (fallback)
            throw_complete = False
            if self.use_motion_detection:
                throw_complete = self.motion_detector.detect_throw_complete(rocks, timestamp)

            # Flight timeout takes priority
            if elapsed > 3.0 or throw_complete:
                # After 3 seconds or motion settled, assume rocks are settling
                self._transition_to(GameState.ROCKS_SETTLING, timestamp)
                self._log_event("rocks_settling", {"camera": camera, "elapsed": elapsed, "motion_complete": throw_complete})
            elif len(moving) == 0 and elapsed < 1.0:
                # No rocks moving very early - probably false detection
                # Reset motion detector and return to IDLE
                if self.use_motion_detection:
                    self.motion_detector.reset()
                self._transition_to(GameState.IDLE, timestamp)
                self._log_event("false_throw", {"camera": camera, "reason": "no_motion"})

        elif self.state == GameState.ROCKS_SETTLING:
            moving = tracker.get_moving_rocks()

            # Check settling via motion detector or traditional method
            all_settled = len(moving) == 0
            if self.use_motion_detection:
                all_settled = self.motion_detector.detect_throw_complete(rocks, timestamp, min_settle_frames=3)

            if all_settled or (timestamp - self.state_entered_time) > 5.0:
                # All rocks settled or timeout
                self._transition_to(GameState.THROW_COMPLETE, timestamp)
                self._log_event("rocks_settled", {"camera": camera, "moving": len(moving)})
                if self.use_motion_detection:
                    self.motion_detector.end_throw()

            elif (timestamp - self.state_entered_time) > 10.0:
                # Extended timeout - force complete
                self._transition_to(GameState.THROW_COMPLETE, timestamp)
                self._log_event("settling_timeout", {"camera": camera})
                if self.use_motion_detection:
                    self.motion_detector.end_throw()

        elif self.state == GameState.THROW_COMPLETE:
            # Record throw
            self.throws[self.possession] += 1
            self.total_throws += 1
            self.last_throw_time = timestamp
            self.last_activity_time = timestamp
            
            # Classify the shot
            shot_result = self._classify_shot(camera)
            self.last_shot_type = shot_result.shot_type.value if shot_result else None
            shot_str = format_shot_result(shot_result) if shot_result else "unknown"

            self._log_event("throw_complete", {
                "team": self.possession,
                "throws_red": self.throws["team_red"],
                "throws_yellow": self.throws["team_yellow"],
                "total": self.total_throws,
                "shot_type": self.last_shot_type,
                "shot_details": shot_result.details if shot_result else {}
            })
            
            # Record shot in history
            if shot_result:
                self.shot_history.append({
                    "end": self.current_end,
                    "throw": self.total_throws,
                    "team": self.possession,
                    "shot_type": shot_result.shot_type.value,
                    "confidence": shot_result.confidence,
                    "details": shot_result.details
                })

            # Check for end completion
            if self.total_throws >= 16:
                self._transition_to(GameState.END_COMPLETE, timestamp)
            else:
                # Switch possession
                self.possession = "team_yellow" if self.possession == "team_red" else "team_red"
                self._transition_to(GameState.IDLE, timestamp)

        elif self.state == GameState.END_COMPLETE:
            # Calculate score
            score = self._calculate_score(camera)
            self.end_scores.append(score)
            self.scores["team_red"] += score.red
            self.scores["team_yellow"] += score.yellow

            # Update hammer (opposite of scoring team)
            if score.red > 0:
                self.hammer = "team_yellow"
            elif score.yellow > 0:
                self.hammer = "team_red"
            # If blank end, hammer stays with team that had it

            self._log_event("end_complete", {
                "end": self.current_end,
                "red_score": score.red,
                "yellow_score": score.yellow,
                "total_red": self.scores["team_red"],
                "total_yellow": self.scores["team_yellow"],
                "next_hammer": self.hammer
            })

            # Reset for next end
            self.current_end += 1
            self.throws = {"team_red": 0, "team_yellow": 0}
            self.total_throws = 0
            self.last_activity_time = 0.0  # Reset activity timer
            self.possession = "team_red" if self.hammer == "team_yellow" else "team_yellow"

            # Clear rock tracking
            self.near_tracker.clear()
            self.far_tracker.clear()
            
            # Reset motion detector for new end
            if self.use_motion_detection:
                self.motion_detector.reset()

            self._transition_to(GameState.IDLE, timestamp)

    def _transition_to(self, new_state: GameState, timestamp: float):
        """Transition to a new state."""
        self.state = new_state
        self.state_entered_time = timestamp
    
    def _capture_rock_state_before(self, camera: str):
        """Capture current rock state before a throw for classification."""
        tracker = self._get_active_tracker(camera)
        rocks = tracker.get_all_rocks()
        
        self.rock_state_before_throw = [
            RockState(x=r.x, y=r.y, color=r.color)
            for r in rocks
        ]
    
    def _classify_shot(self, camera: str):
        """Classify the shot based on before/after rock states."""
        tracker = self._get_active_tracker(camera)
        rocks_after = tracker.get_all_rocks()
        
        rock_state_after = [
            RockState(x=r.x, y=r.y, color=r.color)
            for r in rocks_after
        ]
        
        # Get button position for this camera
        button = self.calibration.get(camera, {}).get("button")
        
        try:
            result = self.shot_classifier.classify_shot(
                before_rocks=self.rock_state_before_throw,
                after_rocks=rock_state_after,
                throwing_team=self.possession,
                button=tuple(button) if button else None
            )
            return result
        except Exception as e:
            self._log_event("shot_classify_error", {"error": str(e)})
            return None

    def get_state(self) -> dict:
        """Get current game state as dict."""
        return {
            "state": self.state.value,
            "end": self.current_end,
            "active_camera": self.get_active_camera_for_end(),
            "hammer": self.hammer,
            "possession": self.possession,
            "scores": self.scores,
            "throws": self.throws,
            "total_throws": self.total_throws,
            "near_rocks": len(self.near_tracker.get_all_rocks()),
            "far_rocks": len(self.far_tracker.get_all_rocks()),
            "last_update": self.last_update
        }

    def get_events(self, since: float = 0) -> List[dict]:
        """Get events since a timestamp."""
        return [e for e in self.events if e["time"] > since]
    
    def get_trajectory_predictions(self, camera: str = "near") -> List[dict]:
        """
        Get trajectory predictions for all moving rocks.
        
        Args:
            camera: Which camera ("near" or "far")
        
        Returns:
            List of prediction dicts with rock_id, predicted position, confidence
        """
        tracker = self._get_active_tracker(camera)
        predictions = []
        
        # Get moving rocks
        moving_ids = self.trajectory_predictor.get_moving_rocks(threshold=10.0)
        
        for rock_id in moving_ids:
            pred = self.trajectory_predictor.predict_stop(rock_id)
            if pred:
                # Get rock color
                rock = tracker.rocks.get(rock_id)
                color = rock.color if rock else "unknown"
                
                predictions.append({
                    "rock_id": rock_id,
                    "color": color,
                    "current_position": (rock.x, rock.y) if rock else None,
                    "predicted_stop": {
                        "x": pred.x,
                        "y": pred.y,
                        "confidence": pred.confidence,
                        "time_to_stop": pred.estimated_stop_time,
                        "distance": pred.distance_to_travel
                    }
                })
        
        return predictions


    def get_dashboard_data(self) -> dict:
        """Get data in dashboard-compatible format."""
        state = self.get_state()
        events = self.get_events()
        
        # Format events as readable log
        debug_logs = []
        for e in events[-10:]:  # Last 10 events
            event_type = e.get("event", "unknown")
            details = e.get("details", {})
            if event_type == "delivery_started":
                debug_logs.append(f"Delivery started ({e['state']})")
            elif event_type == "throw_complete":
                team = details.get("team", "unknown")
                total = details.get("total", 0)
                debug_logs.append(f"Throw complete: {team}, total {total}")
            elif event_type == "rocks_settled":
                moving = details.get("moving", 0)
                debug_logs.append(f"Rocks settled ({moving} moving)")
            elif event_type == "end_complete":
                end = details.get("end", 0)
                red = details.get("red_score", 0)
                yellow = details.get("yellow_score", 0)
                debug_logs.append(f"End {end} complete: Red {red} - Yellow {yellow}")
            elif event_type == "inactivity_timeout":
                throws = details.get("throws", 0)
                debug_logs.append(f"Inactivity timeout ({throws} throws)")
            else:
                debug_logs.append(f"{event_type}")
        
        # Extract button positions for dashboard
        cal = self.calibration
        near_button = cal.get("near", {}).get("button")
        far_button = cal.get("far", {}).get("button")
        near_house = cal.get("near", {}).get("house_size") or cal.get("near", {}).get("house_size_estimate")
        far_house = cal.get("far", {}).get("house_size") or cal.get("far", {}).get("house_size_estimate")
        
        # Get last score info
        last_score = "No end completed yet"
        if self.end_scores:
            last = self.end_scores[-1]
            last_score = f"End {last.end}: Red {last.red} - Yellow {last.yellow}"
        
        return {
            "game_state": {
                "possession": state["possession"],
                "next_shooter": None,
                "score": state["scores"],
                "end": state["end"],
                "state": state["state"],
                "throws": state["throws"],
                "total_throws": state["total_throws"]
            },
            "locked_button": {
                "near": near_button,
                "far": far_button
            },
            "locked_house_size": {
                "near": near_house,
                "far": far_house
            },
            "current_raw_detections": self.last_detections,
            "wide_data": {
                "wide_rocks": [],
                "deliveries": False,
                "video_timestamp": "N/A"
            },
            "system_status": {
                "last_score": last_score,
                "fps": 0.0,
                "model": "fcc-curling-rock-detection/17"
            },
            "trajectory_predictions": self.get_trajectory_predictions("near"),
            "debug_logs": debug_logs,
            "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_update": state["last_update"]
        }

def load_calibration(calibration_file: str) -> dict:
    """Load calibration from file."""
    with open(calibration_file, "r") as f:
        return json.load(f)


def main():
    """Test the game tracker with simulated detections."""
    print("Game Tracker Test")
    print("=" * 60)

    # Load calibration
    calibration = {
        "near": {"button": (207, 375), "house_size": 400},
        "far": {"button": (222, 374), "house_size": 400}
    }

    config = {}

    tracker = GameTracker(calibration, config)

    print(f"Initial state: {tracker.get_state()}")
    print()

    # Simulate some detections
    test_detections = [
        {"class": "curling delivery", "x": 200, "y": 600, "confidence": 0.9},
    ]

    print("Simulating delivery...")
    tracker.process_detections(test_detections, "near", time.time())
    print(f"State: {tracker.get_state()}")

    # Delivery ends
    time.sleep(0.5)
    tracker.process_detections([], "near", time.time())
    print(f"After delivery ends: {tracker.get_state()}")

    # Rock in flight
    time.sleep(1)
    rock_detections = [
        {"class": "red-rock", "x": 210, "y": 400, "confidence": 0.95},
    ]
    tracker.process_detections(rock_detections, "near", time.time())
    print(f"With rock: {tracker.get_state()}")

    print()
    print("Events:")
    for event in tracker.get_events():
        print(f"  {event}")


if __name__ == "__main__":
    main()