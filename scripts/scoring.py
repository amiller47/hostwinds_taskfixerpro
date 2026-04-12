#!/usr/bin/env python3
"""
Score calculation module for curling vision.
Calculates which rocks are in the house and scoring.
"""

import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class Rock:
    x: float
    y: float
    color: str  # "red" or "yellow"
    confidence: float = 1.0
    distance: float = 0.0  # Distance from button


@dataclass
class HouseState:
    """State of rocks in the house."""
    red_rocks: List[Rock]
    yellow_rocks: List[Rock]
    scoring_team: Optional[str]  # "red", "yellow", or None (blank)
    points: int
    closest_rock_distance: float


def calculate_house_state(
    rocks: List[Rock],
    button_x: float,
    button_y: float,
    house_radius: float,
    rock_radius: float = 15.0
) -> HouseState:
    """
    Calculate the state of rocks in the house.

    Args:
        rocks: List of detected rocks
        button_x, button_y: Button position in pixels
        house_radius: House radius in pixels
        rock_radius: Rock radius in pixels (for overlap detection)

    Returns:
        HouseState with scoring information
    """
    # Calculate distance from button for each rock
    for rock in rocks:
        rock.distance = math.sqrt((rock.x - button_x)**2 + (rock.y - button_y)**2)

    # Filter rocks in the house
    in_house = [r for r in rocks if r.distance <= house_radius]

    # Separate by color
    red_in_house = [r for r in in_house if r.color == "red"]
    yellow_in_house = [r for r in in_house if r.color == "yellow"]

    # Sort by distance
    all_in_house = sorted(in_house, key=lambda r: r.distance)

    # Determine scoring
    if not all_in_house:
        return HouseState(
            red_rocks=red_in_house,
            yellow_rocks=yellow_in_house,
            scoring_team=None,
            points=0,
            closest_rock_distance=float('inf')
        )

    # Closest rock determines scoring team
    closest_rock = all_in_house[0]
    scoring_team = closest_rock.color

    # Count scoring rocks (closest rocks of scoring team until opponent rock)
    points = 0
    for rock in all_in_house:
        if rock.color == scoring_team:
            points += 1
        else:
            # First opponent rock ends scoring
            break

    return HouseState(
        red_rocks=red_in_house,
        yellow_rocks=yellow_in_house,
        scoring_team=scoring_team,
        points=points,
        closest_rock_distance=closest_rock.distance
    )


def visualize_house_state(house_state: HouseState, width: int = 400, height: int = 400) -> str:
    """
    Create ASCII visualization of house state.

    Args:
        house_state: Current house state
        width, height: Canvas dimensions (for scaling)

    Returns:
        ASCII art string
    """
    lines = []
    lines.append("  HOUSE STATE")
    lines.append("  " + "-" * 30)

    if house_state.scoring_team == "red":
        lines.append(f"  Scoring: RED {house_state.points}")
    elif house_state.scoring_team == "yellow":
        lines.append(f"  Scoring: YELLOW {house_state.points}")
    else:
        lines.append("  No rocks in house (blank)")

    lines.append("")
    lines.append(f"  Red rocks in house: {len(house_state.red_rocks)}")
    lines.append(f"  Yellow rocks in house: {len(house_state.yellow_rocks)}")

    if house_state.closest_rock_distance < float('inf'):
        lines.append(f"  Closest rock: {house_state.closest_rock_distance:.1f}px")

    # Distance list
    all_rocks = house_state.red_rocks + house_state.yellow_rocks
    if all_rocks:
        all_rocks.sort(key=lambda r: r.distance)
        lines.append("")
        lines.append("  Rocks by distance:")
        for i, rock in enumerate(all_rocks[:8]):  # Show top 8
            color_char = "R" if rock.color == "red" else "Y"
            lines.append(f"    {i+1}. {color_char} @ {rock.distance:.0f}px")

    return "\n".join(lines)


def calculate_score_from_detections(
    detections: List[dict],
    button_x: float,
    button_y: float,
    house_radius: float
) -> HouseState:
    """
    Convenience function to calculate score from raw detections.

    Args:
        detections: List of detection dicts with 'class', 'x', 'y', 'confidence'
        button_x, button_y: Button position
        house_radius: House radius in pixels

    Returns:
        HouseState with scoring information
    """
    rocks = []
    for det in detections:
        class_name = det.get("class") or det.get("name", "")
        if "red" in class_name.lower():
            color = "red"
        elif "yellow" in class_name.lower():
            color = "yellow"
        else:
            continue

        rocks.append(Rock(
            x=det.get("x", 0),
            y=det.get("y", 0),
            color=color,
            confidence=det.get("confidence", 1.0)
        ))

    return calculate_house_state(rocks, button_x, button_y, house_radius)


if __name__ == "__main__":
    # Test with sample data
    test_rocks = [
        Rock(x=210, y=375, color="red", distance=0),  # On button
        Rock(x=230, y=380, color="red"),
        Rock(x=250, y=390, color="yellow"),
        Rock(x=270, y=400, color="red"),
        Rock(x=290, y=410, color="yellow"),
        Rock(x=500, y=500, color="red"),  # Outside house
    ]

    button = (220, 375)
    house_radius = 200

    state = calculate_house_state(test_rocks, button[0], button[1], house_radius)
    print(visualize_house_state(state))