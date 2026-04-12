#!/usr/bin/env python3
"""
Curling Bingo — Gamification for spectators.

Generates bingo cards with curling events and tracks them during a game.
"""

import json
import random
import sqlite3
from datetime import datetime
from pathlib import Path

# Database location
DB_PATH = Path(__file__).parent.parent / "data" / "games.db"

# Bingo events
BINGO_EVENTS = [
    # Rock positions
    {"id": "button", "name": "Rock on Button", "description": "A rock lands on the button", "difficulty": 2},
    {"id": "biting_12", "name": "Biting the 12-Foot", "description": "A rock is biting the 12-foot circle", "difficulty": 1},
    {"id": "in_house", "name": "In the House", "description": "A rock comes to rest in the house", "difficulty": 1},
    {"id": "guard", "name": "Guard Placed", "description": "A guard rock is placed", "difficulty": 1},
    {"id": "freeze", "name": "Freeze!", "description": "A freeze shot is made", "difficulty": 3},
    {"id": "tap_back", "name": "Tap Back", "description": "A rock is tapped back", "difficulty": 2},

    # Shot types
    {"id": "takeout", "name": "Takeout", "description": "A rock is removed from play", "difficulty": 1},
    {"id": "draw", "name": "Draw Shot", "description": "A draw shot is made", "difficulty": 1},
    {"id": "hit_roll", "name": "Hit and Roll", "description": "A hit and roll shot", "difficulty": 2},
    {"id": "raise", "name": "Raise", "description": "A raise shot is made", "difficulty": 2},
    {"id": "double", "name": "Double Takeout", "description": "Two rocks removed with one shot", "difficulty": 3},

    # Game events
    {"id": "blank_end", "name": "Blank End", "description": "An end with no points scored", "difficulty": 2},
    {"id": "score_2", "name": "Two Points!", "description": "A team scores 2 points", "difficulty": 2},
    {"id": "score_3", "name": "Three Points!", "description": "A team scores 3+ points", "difficulty": 3},
    {"id": "steal", "name": "Steal!", "description": "Non-hammer team scores", "difficulty": 3},
    {"id": "hammer_point", "name": "Hammer Scores", "description": "Hammer team scores", "difficulty": 1},
    {"id": "perfect_draw", "name": "Perfect Draw", "description": "A rock lands within 6 inches of button", "difficulty": 4},

    # Rare events
    {"id": "burned_rock", "name": "Burned Rock", "description": "A rock is burned (touched by sweeper)", "difficulty": 4},
    {"id": "hog_line", "name": "Hog Line Violation", "description": "A rock crosses hog line before release", "difficulty": 5},
    {"id": "measure", "name": "Measure Required", "description": "Rocks are too close to call visually", "difficulty": 3},
    {"id": "timeout", "name": "Timeout Called", "description": "A team calls a timeout", "difficulty": 2},

    # Fun events
    {"id": "sweep_hard", "name": "Sweep Hard!", "description": "Sweepers sprint to keep a rock in", "difficulty": 1},
    {"id": "nice_shot", "name": "\"Nice Shot!\"", "description": "Someone says \"Nice shot!\"", "difficulty": 1},
    {"id": "broom_stack", "name": "Broom Stack", "description": "Teams broom stack after the game", "difficulty": 1},
]


class BingoCard:
    """A single bingo card."""

    def __init__(self, card_id: str, events: list):
        self.card_id = card_id
        self.events = events  # 5x5 grid (center is FREE)
        self.marked = [[False] * 5 for _ in range(5)]
        self.marked[2][2] = True  # FREE space

    def to_dict(self):
        return {
            "card_id": self.card_id,
            "events": [[e["id"] if e else "FREE" for e in row] for row in self.events],
            "marked": self.marked
        }


class BingoGame:
    """Manages bingo cards and tracks events."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.events_occurred = set()
        self.cards = {}

    def generate_card(self, difficulty_range=(1, 3)) -> BingoCard:
        """Generate a random bingo card."""
        # Filter events by difficulty
        eligible = [e for e in BINGO_EVENTS
                    if difficulty_range[0] <= e["difficulty"] <= difficulty_range[1]]

        # Need 24 events (25 minus FREE)
        selected = random.sample(eligible, min(24, len(eligible)))

        # Pad with any events if not enough
        if len(selected) < 24:
            remaining = [e for e in BINGO_EVENTS if e not in selected]
            selected.extend(random.sample(remaining, 24 - len(selected)))

        # Shuffle and arrange in 5x5 grid
        random.shuffle(selected)
        grid = []
        idx = 0
        for row in range(5):
            row_events = []
            for col in range(5):
                if row == 2 and col == 2:
                    row_events.append(None)  # FREE space
                else:
                    row_events.append(selected[idx])
                    idx += 1
            grid.append(row_events)

        card_id = f"BINGO-{random.randint(10000, 99999)}"
        card = BingoCard(card_id, grid)
        self.cards[card_id] = card
        return card

    def mark_event(self, event_id: str) -> list:
        """Mark an event on all cards. Returns list of winning cards."""
        self.events_occurred.add(event_id)
        winners = []

        for card_id, card in self.cards.items():
            for row in range(5):
                for col in range(5):
                    event = card.events[row][col]
                    if event and event["id"] == event_id:
                        card.marked[row][col] = True

            # Check for win
            if self._check_win(card):
                winners.append(card_id)

        return winners

    def _check_win(self, card: BingoCard) -> bool:
        """Check if card has a bingo."""
        # Check rows
        for row in card.marked:
            if all(row):
                return True

        # Check columns
        for col in range(5):
            if all(card.marked[row][col] for row in range(5)):
                return True

        # Check diagonals
        if all(card.marked[i][i] for i in range(5)):
            return True
        if all(card.marked[i][4-i] for i in range(5)):
            return True

        return False

    def get_card_status(self, card_id: str) -> dict:
        """Get status of a specific card."""
        if card_id not in self.cards:
            return {"error": "Card not found"}

        card = self.cards[card_id]
        return {
            "card_id": card_id,
            "events": [[e["name"] if e else "FREE" for e in row] for row in card.events],
            "marked": card.marked,
            "events_occurred": list(self.events_occurred),
            "has_bingo": self._check_win(card)
        }


def demo():
    """Demo the bingo system."""
    print("=" * 60)
    print("CURLING BINGO - DEMO")
    print("=" * 60)

    game = BingoGame()

    # Generate 3 cards
    print("\nGenerating 3 bingo cards...")
    for i in range(3):
        card = game.generate_card()
        print(f"\nCard {i+1}: {card.card_id}")
        print("-" * 40)
        for row in card.events:
            print(" | ".join(e["name"][:12].ljust(12) if e else "    FREE    " for e in row))

    # Mark some events
    print("\n" + "=" * 60)
    print("Simulating game events...")
    print("=" * 60)

    events_to_mark = ["takeout", "draw", "guard", "in_house", "button"]
    for event_id in events_to_mark:
        print(f"\nEvent: {event_id}")
        winners = game.mark_event(event_id)
        if winners:
            print(f"BINGO! Winners: {winners}")

    # Check card status
    print("\n" + "=" * 60)
    print("Card 1 Status:")
    print("=" * 60)
    card_id = list(game.cards.keys())[0]
    status = game.get_card_status(card_id)
    print(f"Card ID: {status['card_id']}")
    print(f"Has Bingo: {status['has_bingo']}")
    print(f"Events Marked: {len(status['events_occurred'])}")

    print("\n" + "=" * 60)
    print("Available Bingo Events:")
    print("=" * 60)
    for event in BINGO_EVENTS:
        print(f"  {event['id']:15} - {event['name']}")


if __name__ == "__main__":
    demo()