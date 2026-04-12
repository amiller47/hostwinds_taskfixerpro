# Game State Machine Design

## Overview

Track curling game flow through a finite state machine that processes
rock positions and delivery detections across frames.

## States

```
IDLE ─────────────────────────────────────────────────────────────┐
  │                                                                │
  │ Delivery class detected                                        │
  ▼                                                                │
DELIVERY_IN_PROGRESS ──────────────────────────────────────────┐  │
  │                                                             │  │
  │ Delivery class disappears + rock motion detected            │  │
  ▼                                                             │  │
ROCK_IN_FLIGHT ────────────────────────────────────────────────┐│  │
  │                                                             ││  │
  │ Rocks settling (velocity decreasing)                        ││  │
  ▼                                                             ││  │
ROCKS_SETTLING ───────────────────────────────────────────────┐││  │
  │                                                             │││  │
  │ All rocks stationary for N frames                           │││  │
  ▼                                                             │││  │
THROW_COMPLETE ────────────────────────────────────────────────┐│││  │
  │                                                             ││││  │
  │ Increment throw count, check for end completion            ││││  │
  │ If end complete → calculate score → END_COMPLETE            ││││  │
  │ Else → IDLE                                                 ││││  │
  ▼                                                             ││││  │
END_COMPLETE ◄──────────────────────────────────────────────────┘│││  │
  │                                                              │││  │
  │ Score calculated, hammer updated, next end begins          │││  │
  └──────────────────────────────────────────────────────────────┘││  │
                                                                  ││  │
  Throw complete, end not finished ◄──────────────────────────────┘│  │
                                                                   │  │
  Timeout/Reset ◄──────────────────────────────────────────────────┘  │
                                                                      │
  After throw complete (no end) ◄────────────────────────────────────┘
```

## Key Data Structures

### RockTracker
```python
class RockTracker:
    def __init__(self):
        self.rocks = {}  # id -> {x, y, vx, vy, last_seen, color}
        self.next_id = 0

    def update(self, detections):
        # Match detections to existing rocks by position
        # Update velocities
        # Mark unseen rocks as potentially removed

    def get_moving_rocks(self):
        # Return rocks with velocity > threshold

    def get_stationary_rocks(self):
        # Return rocks with velocity < threshold for N frames
```

### GameState
```python
class GameState:
    def __init__(self):
        self.state = "IDLE"
        self.end = 1
        self.hammer = "team_yellow"  # Who has hammer this end
        self.possession = "team_red"  # Who throws next
        self.scores = {"team_red": 0, "team_yellow": 0}
        self.throws = {"team_red": 0, "team_yellow": 0}
        self.total_throws = 0

        # Rock tracking
        self.near_tracker = RockTracker()
        self.far_tracker = RockTracker()

        # Delivery tracking
        self.delivery_position = None
        self.delivery_frame_count = 0

        # Timing
        self.last_delivery_time = 0
        self.last_motion_time = 0
        self.settling_start_time = 0
```

## Transition Logic

### IDLE → DELIVERY_IN_PROGRESS
- "curling delivery" class detected with confidence > 0.7
- Position is in expected delivery zone (hog line area)
- Not already in delivery

### DELIVERY_IN_PROGRESS → ROCK_IN_FLIGHT
- Delivery class disappears
- New rock motion detected (velocity spike)
- OR timeout (5 seconds) — assume throw happened

### ROCK_IN_FLIGHT → ROCKS_SETTLING
- Rocks detected with decreasing velocity
- No new high-velocity rocks

### ROCKS_SETTLING → THROW_COMPLETE
- All rocks stationary for 2+ seconds
- OR timeout (10 seconds) — force complete

### THROW_COMPLETE → IDLE or END_COMPLETE
- If total_throws >= 16: calculate score → END_COMPLETE
- Else: update possession → IDLE

### END_COMPLETE → IDLE
- Update scores
- Flip hammer
- Reset throws
- Increment end number

## Calibration Strategy

1. Load saved calibration from config
2. On startup, validate with 5 frames:
   - Button should be within 20px of saved position
   - Confidence should be > 85%
3. If validation fails, log warning but continue
4. No 20-sample calibration loop

## Integration Points

### Input
- Frame with detections from model
- Detection format: {class, x, y, confidence, width, height}

### Output
- Game state JSON for dashboard
- Rock positions for visualization
- Score updates for API push

### Cameras
- Near camera: tracks hog line + near house
- Far camera: tracks far house (if not blocked)
- Wide camera: tracks playing zone rocks

## Testing Strategy

1. Run on full game recording
2. Log state transitions
3. Compare detected throws to video timeline
4. Validate score at end of each end