#!/usr/bin/env python3
"""
Shot Classifier for Curling
Classifies shot types based on before/after rock positions.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum


class ShotType(Enum):
    """Types of curling shots."""
    DRAW = "draw"
    TAKEOUT = "takeout"
    GUARD = "guard"
    FREEZE = "freeze"
    RAISE = "raise"
    BLANK = "blank"
    UNKNOWN = "unknown"


@dataclass
class RockState:
    """Snapshot of rock state at a point in time."""
    x: float
    y: float
    color: str  # "red" or "yellow"
    
    def distance_from(self, other: "RockState") -> float:
        """Calculate distance to another rock."""
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5


@dataclass
class ShotResult:
    """Result of shot classification."""
    shot_type: ShotType
    confidence: float
    details: dict  # Additional info about the shot


class ShotClassifier:
    """
    Classifies curling shots based on rock state changes.
    
    Classification Logic:
    - DRAW: New rock appears in house (wasn't there before throw)
    - TAKEOUT: Opponent rock removed from house
    - GUARD: Rock placed outside house, near center line
    - FREEZE: Rock placed touching another rock in house
    - RAISE: Rock moved deeper into house by another rock
    - BLANK: Rock thrown through house (no rock remains)
    """
    
    # Distance thresholds (in pixels, calibrated for ~720p camera)
    HOUSE_RADIUS = 374  # ~748px house diameter / 2
    GUARD_ZONE_MAX = 50  # Max distance from house edge for guard (just in front)
    TOUCH_THRESHOLD = 30  # Distance to consider rocks "touching"
    CENTER_LINE_TOLERANCE = 100  # How far from center line is still a guard
    
    def __init__(self, house_radius: int = None, calibration: dict = None):
        """Initialize with optional calibration."""
        if calibration:
            self.HOUSE_RADIUS = calibration.get("house_size", 748) // 2
        
        if house_radius:
            self.HOUSE_RADIUS = house_radius
    
    def classify_shot(
        self,
        before_rocks: List[RockState],
        after_rocks: List[RockState],
        throwing_team: str,  # "team_red" or "team_yellow"
        button: Tuple[float, float] = None
    ) -> ShotResult:
        """
        Classify a shot based on before/after rock states.
        
        Args:
            before_rocks: Rock positions before the throw
            after_rocks: Rock positions after the throw
            throwing_team: Which team is throwing
            button: (x, y) position of button for distance calculations
        
        Returns:
            ShotResult with shot type and confidence
        """
        throwing_color = "red" if "red" in throwing_team else "yellow"
        
        # Find the new rock (the one that was just thrown)
        new_rock = self._find_new_rock(before_rocks, after_rocks, throwing_color)
        
        # Find removed rocks
        removed_rocks = self._find_removed_rocks(before_rocks, after_rocks)
        
        # Check for blank (no thrown rock found or not in house)
        if new_rock is None:
            return ShotResult(
                shot_type=ShotType.BLANK,
                confidence=0.8,
                details={"reason": "no_new_rock_detected"}
            )
        
        # Calculate distance from button if we have it
        dist_from_button = float("inf")
        if button:
            dist_from_button = ((new_rock.x - button[0])**2 + (new_rock.y - button[1])**2)**0.5
        
        # Check if in house
        in_house = dist_from_button < self.HOUSE_RADIUS
        
        if not in_house:
            # Could be guard or blank
            if self._is_guard_position(new_rock, button):
                return ShotResult(
                    shot_type=ShotType.GUARD,
                    confidence=0.7,
                    details={"distance_from_house": dist_from_button - self.HOUSE_RADIUS}
                )
            else:
                return ShotResult(
                    shot_type=ShotType.BLANK,
                    confidence=0.6,
                    details={"reason": "outside_house_not_guard"}
                )
        
        # Check for takeout (opponent rock removed)
        opponent_color = "yellow" if throwing_color == "red" else "red"
        opponent_removed = [r for r in removed_rocks if r.color == opponent_color]
        
        if opponent_removed:
            # Takeout or raise
            # Check if any of our rocks moved deeper (raise)
            our_moved = self._check_for_raise(before_rocks, after_rocks, throwing_color)
            
            if our_moved:
                return ShotResult(
                    shot_type=ShotType.RAISE,
                    confidence=0.7,
                    details={
                        "removed_count": len(opponent_removed),
                        "moved_count": len(our_moved)
                    }
                )
            else:
                return ShotResult(
                    shot_type=ShotType.TAKEOUT,
                    confidence=0.8,
                    details={"removed_count": len(opponent_removed)}
                )
        
        # Check for freeze (touching another rock in house)
        if self._is_freeze(new_rock, after_rocks):
            return ShotResult(
                shot_type=ShotType.FREEZE,
                confidence=0.7,
                details={"touching_count": len(self._get_touching_rocks(new_rock, after_rocks))}
            )
        
        # Default: draw
        return ShotResult(
            shot_type=ShotType.DRAW,
            confidence=0.8,
            details={"distance_from_button": dist_from_button}
        )
    
    def _find_new_rock(
        self,
        before: List[RockState],
        after: List[RockState],
        throwing_color: str
    ) -> Optional[RockState]:
        """Find the newly thrown rock."""
        # Look for rocks of throwing color that don't match before positions
        before_positions = {(r.x, r.y, r.color) for r in before}
        
        for rock in after:
            if rock.color != throwing_color:
                continue
            
            # Check if this rock existed before (within tolerance)
            is_new = True
            for b_rock in before:
                if b_rock.color == rock.color and rock.distance_from(b_rock) < 20:
                    is_new = False
                    break
            
            if is_new:
                return rock
        
        # If no new rock found, check if count increased
        before_count = len([r for r in before if r.color == throwing_color])
        after_count = len([r for r in after if r.color == throwing_color])
        
        if after_count > before_count:
            # Return the one furthest from button (most likely new)
            if after:
                return max(after, key=lambda r: r.x**2 + r.y**2)
        
        return None
    
    def _find_removed_rocks(
        self,
        before: List[RockState],
        after: List[RockState]
    ) -> List[RockState]:
        """Find rocks that were removed."""
        removed = []
        
        for b_rock in before:
            found = False
            for a_rock in after:
                if b_rock.color == a_rock.color and b_rock.distance_from(a_rock) < 20:
                    found = True
                    break
            
            if not found:
                removed.append(b_rock)
        
        return removed
    
    def _is_guard_position(
        self,
        rock: RockState,
        button: Tuple[float, float]
    ) -> bool:
        """Check if rock is in guard position."""
        if button is None:
            # Can't determine guard without button
            return False
        
        # Guard is just outside house but near center line
        dist_from_button = ((rock.x - button[0])**2 + (rock.y - button[1])**2)**0.5
        
        # Must be outside house but within guard zone (just in front)
        outside_house = dist_from_button > self.HOUSE_RADIUS
        near_house = dist_from_button < self.HOUSE_RADIUS + self.GUARD_ZONE_MAX
        
        if not (outside_house and near_house):
            return False
        
        # Near center line (x-coordinate close to button)
        if abs(rock.x - button[0]) < self.CENTER_LINE_TOLERANCE:
            return True
        
        return False
    
    def _is_freeze(
        self,
        rock: RockState,
        all_rocks: List[RockState]
    ) -> bool:
        """Check if rock is frozen to another rock."""
        touching = self._get_touching_rocks(rock, all_rocks)
        return len(touching) > 0
    
    def _get_touching_rocks(
        self,
        rock: RockState,
        all_rocks: List[RockState]
    ) -> List[RockState]:
        """Get rocks touching the given rock."""
        touching = []
        for other in all_rocks:
            if other is rock:
                continue
            if rock.distance_from(other) < self.TOUCH_THRESHOLD:
                touching.append(other)
        return touching
    
    def _check_for_raise(
        self,
        before: List[RockState],
        after: List[RockState],
        team_color: str
    ) -> List[RockState]:
        """Check if any of our rocks moved deeper into house."""
        moved = []
        
        for b_rock in before:
            if b_rock.color != team_color:
                continue
            
            # Find matching rock in after
            for a_rock in after:
                if a_rock.color == b_rock.color and b_rock.distance_from(a_rock) > 20:
                    # Rock moved significantly
                    moved.append(a_rock)
                    break
        
        return moved


def format_shot_result(result: ShotResult) -> str:
    """Format shot result for display."""
    shot_name = result.shot_type.value.upper()
    conf_pct = f"{result.confidence * 100:.0f}%"
    
    details_str = ""
    if result.details:
        parts = []
        for k, v in result.details.items():
            if isinstance(v, float):
                parts.append(f"{k}={v:.1f}")
            else:
                parts.append(f"{k}={v}")
        details_str = f" ({', '.join(parts)})"
    
    return f"{shot_name} [{conf_pct}]{details_str}"