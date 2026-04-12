#!/usr/bin/env python3
"""
Bingo event detector — Detects bingo events from game state changes.
"""

# Events we can detect from game tracker state
DETECTABLE_EVENTS = {
    # Rock position events (from detections)
    "button": "rock_on_button",
    "biting_12": "rock_biting_12",
    "in_house": "rock_in_house",
    "guard": "guard_placed",
    "freeze": "freeze_shot",
    "takeout": "takeout",
    "draw": "draw_shot",

    # Game events (from state changes)
    "blank_end": "blank_end",
    "score_2": "score_2_or_more",
    "score_3": "score_3_or_more",
    "steal": "steal",
    "hammer_point": "hammer_scores",
}


def detect_bingo_events(old_state, new_state, detections):
    """
    Detect bingo events from state changes and detections.

    Args:
        old_state: Previous game state
        new_state: Current game state
        detections: Current frame detections

    Returns:
        List of event IDs that occurred
    """
    events = []

    # From state changes
    if old_state and new_state:
        # Score events
        old_score = old_state.get("scores", {"team_red": 0, "team_yellow": 0})
        new_score = new_state.get("scores", {"team_red": 0, "team_yellow": 0})

        old_total = old_score.get("team_red", 0) + old_score.get("team_yellow", 0)
        new_total = new_score.get("team_red", 0) + new_score.get("team_yellow", 0)

        if new_total > old_total:
            # Points were scored
            red_diff = new_score.get("team_red", 0) - old_score.get("team_red", 0)
            yellow_diff = new_score.get("team_yellow", 0) - old_score.get("team_yellow", 0)

            hammer = new_state.get("hammer", "team_red")

            if red_diff > 0:
                points = red_diff
                scoring_team = "team_red"
            else:
                points = yellow_diff
                scoring_team = "team_yellow"

            # Steal?
            if scoring_team != hammer:
                events.append("steal")
            else:
                events.append("hammer_point")

            # Score magnitude
            if points >= 3:
                events.append("score_3")
            elif points >= 2:
                events.append("score_2")

        # Blank end?
        if old_state.get("state") == "throw_complete" and new_state.get("state") == "idle":
            throws = new_state.get("total_throws", 0)
            if throws == 0 or (new_total == old_total):
                events.append("blank_end")

    # From detections
    if detections:
        rocks_in_house = 0
        rocks_on_button = 0
        rocks_biting_12 = 0
        guards = 0

        button = (350, 700)  # Default, should use calibration

        for det in detections:
            cls = det.get("class", "")
            x, y = det.get("x", 0), det.get("y", 0)
            conf = det.get("confidence", 0)

            if "rock" in cls:
                # Distance from button
                dist = ((x - button[0])**2 + (y - button[1])**2)**0.5

                # House size estimate
                house_radius = 375  # 12-foot in pixels

                if dist < 15:  # On button
                    rocks_on_button += 1
                    events.append("button")
                elif dist < 60:  # 4-foot
                    events.append("in_house")
                elif dist < 120:  # 8-foot
                    events.append("in_house")
                elif dist < house_radius:  # 12-foot
                    events.append("biting_12")
                    events.append("in_house")

            if cls == "guard":
                events.append("guard")

            if cls == "curling delivery":
                events.append("draw")

    # Remove duplicates
    return list(set(events))


def get_bingo_summary(events):
    """Get human-readable summary of bingo events."""
    event_names = {e["id"]: e["name"] for e in BINGO_EVENTS}

    # Import here to avoid circular
    from bingo import BINGO_EVENTS

    summary = []
    for event_id in events:
        summary.append({
            "id": event_id,
            "name": event_names.get(event_id, event_id),
            "timestamp": time.time()
        })
    return summary


if __name__ == "__main__":
    # Test
    from bingo import BINGO_EVENTS
    print("Detectable bingo events:")
    for event_id, method in DETECTABLE_EVENTS.items():
        event_name = next((e["name"] for e in BINGO_EVENTS if e["id"] == event_id), event_id)
        print(f"  {event_id:15} -> {event_name}")