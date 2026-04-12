#!/usr/bin/env python3
"""
AI Shot Calling Assistant — Suggests optimal shots based on house layout.

Uses simple heuristics for now, can be upgraded to ML later.
"""

import json
import math
from typing import Dict, List, Tuple, Optional

# Shot types with descriptions
SHOT_TYPES = {
    "draw": "Draw to a specific location",
    "guard": "Place a guard rock",
    "takeout": "Remove an opponent rock",
    "hit_and_roll": "Hit and roll into better position",
    "freeze": "Freeze onto an opponent rock",
    "tap_back": "Tap opponent rock back",
    "raise": "Raise a rock into the house",
    "peel": "Peel a guard",
    "blank": "Blank the end (throw through)",
    "promote": "Promote a rock deeper into house",
}


class ShotCaller:
    """Analyzes house layout and suggests optimal shots."""

    def __init__(self, calibration: dict = None):
        """Initialize with button position."""
        self.button = calibration.get("near", {}).get("button", (350, 700)) if calibration else (350, 700)
        self.house_radius = 375  # 12-foot radius in pixels

    def analyze_house(self, rocks: List[dict]) -> dict:
        """
        Analyze the current house state.

        Args:
            rocks: List of rock dicts with 'x', 'y', 'color'

        Returns:
            Analysis dict with counts, positions, scores
        """
        red_in_house = []
        yellow_in_house = []
        red_closest = None
        yellow_closest = None

        for rock in rocks:
            dist = self._distance_from_button(rock)
            is_red = rock.get("color") == "red" or "red" in rock.get("color", "")

            if dist < self.house_radius:
                if is_red:
                    red_in_house.append((rock, dist))
                    if red_closest is None or dist < red_closest[1]:
                        red_closest = (rock, dist)
                else:
                    yellow_in_house.append((rock, dist))
                    if yellow_closest is None or dist < yellow_closest[1]:
                        yellow_closest = (rock, dist)

        # Sort by distance
        red_in_house.sort(key=lambda x: x[1])
        yellow_in_house.sort(key=lambda x: x[1])

        # Calculate score (who has shot rock)
        score_red = 0
        score_yellow = 0

        if red_closest and yellow_closest:
            if red_closest[1] < yellow_closest[1]:
                # Red has shot rock
                score_red = 1 + sum(1 for r, d in red_in_house
                                   if d < next((d2 for y, d2 in yellow_in_house), float('inf')))
            else:
                # Yellow has shot rock
                score_yellow = 1 + sum(1 for y, d in yellow_in_house
                                       if d < next((d2 for r, d2 in red_in_house), float('inf')))
        elif red_closest:
            score_red = len(red_in_house)
        elif yellow_closest:
            score_yellow = len(yellow_in_house)

        return {
            "red_in_house": len(red_in_house),
            "yellow_in_house": len(yellow_in_house),
            "red_closest": red_closest[1] if red_closest else None,
            "yellow_closest": yellow_closest[1] if yellow_closest else None,
            "score_red": score_red,
            "score_yellow": score_yellow,
            "shot_rock": "red" if red_closest and (not yellow_closest or red_closest[1] < yellow_closest[1])
                         else "yellow" if yellow_closest else None
        }

    def suggest_shot(self, rocks: List[dict], team: str, hammer: str,
                     score_red: int = 0, score_yellow: int = 0,
                     end: int = 1, throws_remaining: int = 16) -> dict:
        """
        Suggest the optimal shot based on game situation.

        Args:
            rocks: Current rock positions
            team: Which team is throwing ('team_red' or 'team_yellow')
            hammer: Which team has hammer
            score_red: Red's score
            score_yellow: Yellow's score
            end: Current end number
            throws_remaining: Throws left in end

        Returns:
            Suggested shot with reasoning
        """
        analysis = self.analyze_house(rocks)

        is_red = "red" in team
        my_color = "red" if is_red else "yellow"
        opp_color = "yellow" if is_red else "red"

        my_score = score_red if is_red else score_yellow
        opp_score = score_yellow if is_red else score_red
        score_diff = my_score - opp_score

        my_in_house = analysis["red_in_house"] if is_red else analysis["yellow_in_house"]
        opp_in_house = analysis["yellow_in_house"] if is_red else analysis["red_in_house"]

        has_hammer = hammer == team

        # Decision tree for shot calling
        suggestions = []

        # 1. If opponent has rock on button and we have hammer -> draw to button
        if opp_in_house > 0 and has_hammer:
            opp_closest = analysis["yellow_closest"] if is_red else analysis["red_closest"]
            if opp_closest and opp_closest < 50:
                suggestions.append({
                    "shot": "draw",
                    "target": "button",
                    "confidence": 0.85,
                    "reasoning": f"Opponent has rock {opp_closest:.0f}px from button. Draw to push them back.",
                    "priority": 10
                })

        # 2. If we have rock closest -> guard it
        if analysis["shot_rock"] == my_color:
            suggestions.append({
                "shot": "guard",
                "target": "center",
                "confidence": 0.80,
                "reasoning": "You have shot rock. Guard it to protect your position.",
                "priority": 9
            })

        # 3. If opponent has multiple in house and we have hammer -> takeout
        if opp_in_house >= 2 and has_hammer:
            suggestions.append({
                "shot": "takeout",
                "target": "opponent_closest",
                "confidence": 0.75,
                "reasoning": f"Opponent has {opp_in_house} rocks in house. Remove shot rock.",
                "priority": 8
            })

        # 4. Early end, no rocks -> draw to button
        if throws_remaining > 12 and my_in_house == 0 and opp_in_house == 0:
            suggestions.append({
                "shot": "draw",
                "target": "button",
                "confidence": 0.70,
                "reasoning": "Empty house, early end. Establish position in the house.",
                "priority": 7
            })

        # 5. Behind in score late game -> aggressive draws
        if score_diff < -2 and end >= 6:
            suggestions.append({
                "shot": "draw",
                "target": "button",
                "confidence": 0.65,
                "reasoning": "Behind in score, need points. Draw for position.",
                "priority": 6
            })

        # 6. Ahead in score late game -> defensive guards
        if score_diff > 2 and end >= 6:
            suggestions.append({
                "shot": "guard",
                "target": "center",
                "confidence": 0.70,
                "reasoning": "Leading, protect your advantage with guards.",
                "priority": 6
            })

        # 7. Opponent has hammer, we have shot rock -> freeze
        if not has_hammer and analysis["shot_rock"] == my_color:
            suggestions.append({
                "shot": "freeze",
                "target": "opponent_rock",
                "confidence": 0.65,
                "reasoning": "Opponent has hammer. Freeze to their rock to force a difficult shot.",
                "priority": 7
            })

        # 8. Last rock of end with hammer -> draw for point
        if has_hammer and throws_remaining == 1:
            if opp_in_house == 0:
                suggestions.append({
                    "shot": "draw",
                    "target": "button",
                    "confidence": 0.95,
                    "reasoning": "Last rock, empty house. Draw to the button for 1 point.",
                    "priority": 10
                })
            else:
                suggestions.append({
                    "shot": "draw",
                    "target": "better_than_opponent",
                    "confidence": 0.85,
                    "reasoning": "Last rock with hammer. Draw to score your point.",
                    "priority": 10
                })

        # Sort by priority and confidence
        suggestions.sort(key=lambda x: x["priority"] + x["confidence"], reverse=True)

        # Return best suggestion (or default)
        if suggestions:
            return suggestions[0]
        else:
            return {
                "shot": "draw",
                "target": "house",
                "confidence": 0.50,
                "reasoning": "Standard draw to establish position.",
                "priority": 1
            }

    def _distance_from_button(self, rock: dict) -> float:
        """Calculate distance from button in pixels."""
        x = rock.get("x", 0)
        y = rock.get("y", 0)
        return math.sqrt((x - self.button[0])**2 + (y - self.button[1])**2)


def format_shot_call(suggestion: dict) -> str:
    """Format shot suggestion for display."""
    shot_type = suggestion.get("shot", "unknown")
    target = suggestion.get("target", "")
    confidence = suggestion.get("confidence", 0) * 100
    reasoning = suggestion.get("reasoning", "")

    shot_name = SHOT_TYPES.get(shot_type, shot_type)

    return f"""
🥌 AI SHOT CALL
━━━━━━━━━━━━━━━━━━━━━━━
Shot: {shot_name}
Target: {target.replace('_', ' ').title()}
Confidence: {confidence:.0f}%
━━━━━━━━━━━━━━━━━━━━━━━
Reasoning: {reasoning}
"""


def demo():
    """Demo the shot caller."""
    print("=" * 60)
    print("AI SHOT CALLING ASSISTANT - DEMO")
    print("=" * 60)

    caller = ShotCaller()

    # Scenario 1: Empty house, early end
    print("\n--- Scenario 1: Empty house, red throwing ---")
    rocks = []
    suggestion = caller.suggest_shot(rocks, "team_red", "team_yellow",
                                      score_red=0, score_yellow=0, end=1, throws_remaining=16)
    print(format_shot_call(suggestion))

    # Scenario 2: Opponent has rock on button
    print("\n--- Scenario 2: Yellow rock on button, red has hammer ---")
    rocks = [
        {"x": 350, "y": 695, "color": "yellow"}  # Yellow on button
    ]
    suggestion = caller.suggest_shot(rocks, "team_red", "team_red",
                                      score_red=0, score_yellow=1, end=3, throws_remaining=8)
    print(format_shot_call(suggestion))

    # Scenario 3: Red has shot rock, yellow throwing
    print("\n--- Scenario 3: Red has shot rock, yellow throwing ---")
    rocks = [
        {"x": 350, "y": 700, "color": "red"},   # Red on button
        {"x": 380, "y": 720, "color": "yellow"}  # Yellow 30px away
    ]
    suggestion = caller.suggest_shot(rocks, "team_yellow", "team_yellow",
                                      score_red=2, score_yellow=1, end=5, throws_remaining=4)
    print(format_shot_call(suggestion))

    # Scenario 4: Last rock with hammer
    print("\n--- Scenario 4: Last rock with hammer ---")
    rocks = [
        {"x": 360, "y": 710, "color": "yellow"}
    ]
    suggestion = caller.suggest_shot(rocks, "team_red", "team_red",
                                      score_red=3, score_yellow=4, end=8, throws_remaining=1)
    print(format_shot_call(suggestion))

    print("\nAnalysis complete.")


if __name__ == "__main__":
    demo()