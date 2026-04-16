#!/usr/bin/env python3
"""
Rock Trajectory Prediction
Predicts where a moving rock will stop based on velocity, rotation, and ice conditions.

Physics Model:
- Deceleration due to ice friction (configurable per sheet)
- Curl effect from rotation (rocks curl ~4 feet over full sheet)
- Velocity decay over time
"""

import math
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from collections import deque


@dataclass
class TrajectoryPoint:
    """A point in the predicted trajectory."""
    x: float
    y: float
    t: float  # time in seconds from now
    confidence: float


@dataclass
class PredictedPosition:
    """Final predicted position where rock will stop."""
    x: float
    y: float
    confidence: float
    estimated_stop_time: float  # seconds until stop
    distance_to_travel: float  # total distance in pixels


@dataclass
class IceConditions:
    """Ice conditions affecting rock behavior."""
    friction_coefficient: float = 0.015  # Higher = more friction = stops sooner
    curl_per_foot: float = 0.25  # Inches of curl per foot of travel
    sheet_speed: float = 1.0  # 1.0 = normal, 1.1 = fast ice, 0.9 = slow ice
    
    @classmethod
    def default(cls) -> "IceConditions":
        """Default ice conditions."""
        return cls()
    
    @classmethod
    def fast_ice(cls) -> "IceConditions":
        """Fast ice (less friction)."""
        return cls(friction_coefficient=0.012, sheet_speed=1.15)
    
    @classmethod
    def slow_ice(cls) -> "IceConditions":
        """Slow/heavy ice (more friction)."""
        return cls(friction_coefficient=0.018, sheet_speed=0.85)
    
    @classmethod
    def from_observations(cls, observations: List[dict]) -> "IceConditions":
        """
        Estimate ice conditions from observed rock trajectories.
        
        Args:
            observations: List of rock trajectory observations with start/end velocities
        
        Returns:
            Estimated ice conditions
        """
        if len(observations) < 3:
            return cls.default()
        
        # Calculate average friction from observations
        # friction = v_initial^2 / (2 * distance)
        frictions = []
        for obs in observations:
            v0 = obs.get("initial_velocity", 0)
            d = obs.get("distance_traveled", 0)
            if d > 0 and v0 > 0:
                f = (v0 ** 2) / (2 * d)
                frictions.append(f)
        
        if frictions:
            avg_friction = sum(frictions) / len(frictions)
            return cls(friction_coefficient=avg_friction)
        
        return cls.default()


class TrajectoryPredictor:
    """
    Predicts rock stopping position based on velocity and ice conditions.
    
    Uses physics model:
    - Velocity decays due to friction: v(t) = v0 * exp(-k*t)
    - Position: x(t) = x0 + integral(v(t))
    - Curl: rocks curl perpendicular to direction of travel
    """
    
    # Conversion: pixels to feet (approximate for 720p)
    # Standard curling sheet: ~150 feet long, ~14 feet wide
    # At 720p, house is ~748px diameter, which is ~14 feet
    # So roughly 50-55 pixels per foot
    PIXELS_PER_FOOT = 53.0
    
    # Rock diameter in pixels (used for collision detection)
    ROCK_RADIUS_PX = 35.0
    
    # Time step for simulation (seconds)
    DT = 0.05
    
    def __init__(
        self,
        ice_conditions: IceConditions = None,
        frame_rate: float = 6.0,
        history_length: int = 10
    ):
        """
        Initialize trajectory predictor.
        
        Args:
            ice_conditions: Ice conditions (friction, curl, speed)
            frame_rate: Expected frame rate for velocity estimation
            history_length: Number of frames to keep for velocity smoothing
        """
        self.ice = ice_conditions or IceConditions.default()
        self.frame_rate = frame_rate
        self.frame_interval = 1.0 / frame_rate
        
        # Track multiple rocks
        self.rock_histories: Dict[int, deque] = {}  # rock_id -> [(x, y, t)]
        self.max_history = history_length
        
        # Observed trajectories for ice learning
        self.trajectory_observations: List[dict] = []
        self.max_observations = 50
        
    def update_rock(
        self,
        rock_id: int,
        x: float,
        y: float,
        timestamp: float = None
    ) -> Optional[Tuple[float, float]]:
        """
        Update rock position and return velocity estimate.
        
        Args:
            rock_id: Unique rock identifier
            x, y: Current position
            timestamp: Current time (defaults to time.time())
        
        Returns:
            (vx, vy) velocity estimate, or None if not enough history
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Initialize history for new rock
        if rock_id not in self.rock_histories:
            self.rock_histories[rock_id] = deque(maxlen=self.max_history)
        
        history = self.rock_histories[rock_id]
        
        # Add current position
        history.append((x, y, timestamp))
        
        # Need at least 2 frames for velocity
        if len(history) < 2:
            return None
        
        # Calculate velocity from last 2 positions
        x1, y1, t1 = history[-2]
        x2, y2, t2 = history[-1]
        
        dt = t2 - t1
        if dt <= 0:
            return None
        
        vx = (x2 - x1) / dt
        vy = (y2 - t1) / dt
        
        return (vx, vy)
    
    def get_smoothed_velocity(
        self,
        rock_id: int,
        min_frames: int = 3
    ) -> Optional[Tuple[float, float, float]]:
        """
        Get smoothed velocity over multiple frames.
        
        Args:
            rock_id: Rock to get velocity for
            min_frames: Minimum frames needed for smoothing
        
        Returns:
            (vx, vy, speed) smoothed velocity, or None
        """
        if rock_id not in self.rock_histories:
            return None
        
        history = list(self.rock_histories[rock_id])
        
        if len(history) < min_frames:
            return None
        
        # Linear regression over recent positions
        # Simple approach: average velocity over last N frames
        recent = history[-min_frames:]
        
        vx_sum = 0.0
        vy_sum = 0.0
        count = 0
        
        for i in range(1, len(recent)):
            x1, y1, t1 = recent[i-1]
            x2, y2, t2 = recent[i]
            
            dt = t2 - t1
            if dt > 0:
                vx_sum += (x2 - x1) / dt
                vy_sum += (y2 - y1) / dt
                count += 1
        
        if count == 0:
            return None
        
        vx = vx_sum / count
        vy = vy_sum / count
        speed = math.sqrt(vx**2 + vy**2)
        
        return (vx, vy, speed)
    
    def predict_stop(
        self,
        rock_id: int,
        current_x: float = None,
        current_y: float = None,
        rotation: str = "clockwise"  # or "counter-clockwise" or "unknown"
    ) -> Optional[PredictedPosition]:
        """
        Predict where a rock will stop.
        
        Args:
            rock_id: Rock to predict
            current_x, y: Current position (uses last update if None)
            rotation: Rock rotation direction (affects curl)
        
        Returns:
            PredictedPosition with stopping location, or None if rock is stopped
        """
        # Get smoothed velocity
        vel = self.get_smoothed_velocity(rock_id)
        
        if vel is None:
            return None
        
        vx, vy, speed = vel
        
        # If rock is essentially stopped, no prediction needed
        # Threshold: < 5 px/sec (very slow)
        if speed < 5.0:
            return None
        
        # Get current position
        if current_x is None or current_y is None:
            history = list(self.rock_histories.get(rock_id, []))
            if not history:
                return None
            current_x, current_y, _ = history[-1]
        
        # Run physics simulation
        return self._simulate_trajectory(
            current_x, current_y, vx, vy, rotation
        )
    
    def _simulate_trajectory(
        self,
        x0: float,
        y0: float,
        vx: float,
        vy: float,
        rotation: str
    ) -> PredictedPosition:
        """
        Simulate rock trajectory to predict stopping position.
        
        Physics:
        1. Deceleration: dv/dt = -k * v (friction proportional to velocity)
        2. Curl: perpendicular drift based on rotation
        3. Stop when velocity < threshold
        """
        x, y = x0, y0
        v = math.sqrt(vx**2 + vy**2)
        
        # Direction unit vector
        if v > 0:
            dir_x = vx / v
            dir_y = vy / v
        else:
            return PredictedPosition(
                x=x0, y=y0,
                confidence=1.0,
                estimated_stop_time=0.0,
                distance_to_travel=0.0
            )
        
        # Perpendicular direction for curl
        # Curl is perpendicular to direction of travel
        perp_x = -dir_y  # 90 degrees clockwise
        perp_y = dir_x
        
        # Determine curl direction
        if rotation == "clockwise":
            curl_sign = 1.0  # Rock curls to the right (from thrower's perspective)
        elif rotation == "counter-clockwise":
            curl_sign = -1.0  # Rock curls to the left
        else:
            curl_sign = 0.0  # Unknown rotation, no curl prediction
        
        # Friction coefficient
        k = self.ice.friction_coefficient * 10  # Scaled for pixel velocities
        
        # Simulation parameters
        total_distance = 0.0
        total_time = 0.0
        stop_threshold = 3.0  # Stop when v < 3 px/sec
        
        max_iterations = 500  # Safety limit
        iterations = 0
        
        while v > stop_threshold and iterations < max_iterations:
            # Time step
            dt = self.DT
            iterations += 1
            
            # Distance traveled this step
            dist = v * dt
            total_distance += dist
            total_time += dt
            
            # Update position (in direction of travel)
            x += dir_x * dist
            y += dir_y * dist
            
            # Apply curl
            # Curl per foot of travel
            curl_this_step = (
                self.ice.curl_per_foot 
                * (dist / self.PIXELS_PER_FOOT) 
                * self.PIXELS_PER_FOOT
            )  # Convert to pixels
            
            x += perp_x * curl_sign * curl_this_step
            y += perp_y * curl_sign * curl_this_step
            
            # Update velocity (deceleration from friction)
            # dv/dt = -k * v  =>  v(t) = v0 * exp(-k*t)
            v = v * math.exp(-k * dt)
            dir_x = vx / math.sqrt(vx**2 + vy**2) if v > 0 else dir_x
            dir_y = vy / math.sqrt(vx**2 + vy**2) if v > 0 else dir_y
        
        # Confidence based on initial velocity certainty
        # Higher speed = more confident the rock is actually moving
        initial_speed = math.sqrt(vx**2 + vy**2)
        confidence = min(1.0, initial_speed / 100.0)  # Max confidence at 100 px/sec
        
        return PredictedPosition(
            x=x,
            y=y,
            confidence=confidence,
            estimated_stop_time=total_time,
            distance_to_travel=total_distance
        )
    
    def predict_trajectory(
        self,
        rock_id: int,
        num_points: int = 10,
        rotation: str = "unknown"
    ) -> List[TrajectoryPoint]:
        """
        Generate predicted trajectory points for visualization.
        
        Args:
            rock_id: Rock to predict
            num_points: Number of points to generate
            rotation: Rock rotation direction
        
        Returns:
            List of TrajectoryPoint objects
        """
        vel = self.get_smoothed_velocity(rock_id)
        
        if vel is None:
            return []
        
        vx, vy, speed = vel
        
        if speed < 5.0:
            return []
        
        history = list(self.rock_histories.get(rock_id, []))
        if not history:
            return []
        
        x0, y0, _ = history[-1]
        
        # Run mini-simulations at intervals
        points = []
        
        # Time intervals for prediction points
        # Total prediction time based on initial speed
        total_time = 3.0  # Predict up to 3 seconds ahead
        dt = total_time / num_points
        
        x, y = x0, y0
        v = speed
        
        # Direction
        dir_x = vx / speed
        dir_y = vy / speed
        
        # Curl direction
        perp_x = -dir_y
        perp_y = dir_x
        curl_sign = 1.0 if rotation == "clockwise" else (-1.0 if rotation == "counter-clockwise" else 0.0)
        
        k = self.ice.friction_coefficient * 10
        
        for i in range(num_points):
            t = (i + 1) * dt
            
            # Position at time t
            # x(t) = x0 + (v0/k) * (1 - exp(-k*t))  (integral of exp decay)
            decay = 1 - math.exp(-k * t)
            distance = (v / k) * decay
            
            # Curl distance
            curl_dist = curl_sign * self.ice.curl_per_foot * (distance / self.PIXELS_PER_FOOT) * self.PIXELS_PER_FOOT
            
            pred_x = x0 + dir_x * distance + perp_x * curl_dist
            pred_y = y0 + dir_y * distance + perp_y * curl_dist
            
            # Confidence decreases with time
            conf = max(0.1, confidence := min(1.0, speed / 100.0) * (1 - t/total_time))
            
            points.append(TrajectoryPoint(
                x=pred_x,
                y=pred_y,
                t=t,
                confidence=conf
            ))
        
        return points
    
    def record_observation(
        self,
        rock_id: int,
        initial_velocity: float,
        final_velocity: float,
        distance_traveled: float
    ):
        """
        Record an observed trajectory for ice condition learning.
        
        Args:
            rock_id: Rock that was tracked
            initial_velocity: Starting velocity (px/sec)
            final_velocity: Ending velocity (usually ~0)
            distance_traveled: Total distance traveled
        """
        self.trajectory_observations.append({
            "rock_id": rock_id,
            "initial_velocity": initial_velocity,
            "final_velocity": final_velocity,
            "distance_traveled": distance_traveled,
            "timestamp": time.time()
        })
        
        # Keep only recent observations
        if len(self.trajectory_observations) > self.max_observations:
            self.trajectory_observations = self.trajectory_observations[-self.max_observations:]
        
        # Update ice conditions estimate
        self.ice = IceConditions.from_observations(self.trajectory_observations)
    
    def clear_rock(self, rock_id: int):
        """Clear history for a rock (after it stops or is removed)."""
        if rock_id in self.rock_histories:
            del self.rock_histories[rock_id]
    
    def clear_all(self):
        """Clear all rock histories."""
        self.rock_histories.clear()
    
    def get_moving_rocks(self, threshold: float = 10.0) -> List[int]:
        """Get IDs of rocks that are currently moving."""
        moving = []
        for rock_id in self.rock_histories:
            vel = self.get_smoothed_velocity(rock_id)
            if vel and vel[2] > threshold:
                moving.append(rock_id)
        return moving


def format_prediction(pred: PredictedPosition) -> str:
    """Format prediction for display."""
    dist_feet = pred.distance_to_travel / TrajectoryPredictor.PIXELS_PER_FOOT
    time_str = f"{pred.estimated_stop_time:.1f}s" if pred.estimated_stop_time < 10 else f"{pred.estimated_stop_time/60:.1f}m"
    conf_pct = f"{pred.confidence * 100:.0f}%"
    
    return f"Stop: ({pred.x:.0f}, {pred.y:.0f}) | {dist_feet:.1f}ft in {time_str} [{conf_pct}]"


# Test / demo
if __name__ == "__main__":
    print("Trajectory Predictor Test")
    print("=" * 60)
    
    predictor = TrajectoryPredictor(frame_rate=6.0)
    
    # Simulate a rock moving
    rock_id = 1
    
    # Initial position and velocity
    # Rock moving at ~100 px/sec toward the house
    positions = [
        (100, 200, 0.0),
        (115, 201, 0.167),  # ~100 px/sec
        (130, 202, 0.333),
        (145, 203, 0.500),
        (160, 204, 0.667),
    ]
    
    print("\nSimulating rock movement...")
    for x, y, t in positions:
        predictor.update_rock(rock_id, x, y, t)
    
    # Predict where it will stop
    pred = predictor.predict_stop(rock_id, rotation="clockwise")
    
    if pred:
        print(f"\nCurrent position: ({positions[-1][0]}, {positions[-1][1]})")
        print(f"Predicted stop: {format_prediction(pred)}")
    else:
        print("Could not predict (rock may be stopped)")
    
    # Generate trajectory points
    trajectory = predictor.predict_trajectory(rock_id, num_points=10)
    
    print(f"\nTrajectory points:")
    for i, pt in enumerate(trajectory):
        print(f"  t={pt.t:.2f}s: ({pt.x:.0f}, {pt.y:.0f}) [{pt.confidence*100:.0f}%]")
    
    print("\n✅ Trajectory predictor ready for integration")