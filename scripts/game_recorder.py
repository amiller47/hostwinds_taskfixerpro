#!/usr/bin/env python3
"""
Coaching Review Tool — Record and browse game shots.

Creates a searchable database of shots with:
- Rock positions at each shot
- State changes (deliveries, throws)
- Results (score changes)
- Coach notes capability
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Database location
DB_PATH = Path(__file__).parent.parent / "data" / "games.db"

def init_database():
    """Initialize the coaching database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Games table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            sheet INTEGER NOT NULL,
            team_red TEXT,
            team_yellow TEXT,
            final_score_red INTEGER DEFAULT 0,
            final_score_yellow INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ends table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            end_number INTEGER NOT NULL,
            hammer_team TEXT NOT NULL,
            score_red INTEGER DEFAULT 0,
            score_yellow INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (game_id) REFERENCES games(id)
        )
    """)

    # Shots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            end_id INTEGER NOT NULL,
            shot_number INTEGER NOT NULL,
            team TEXT NOT NULL,
            shot_type TEXT,
            rock_positions TEXT,
            result TEXT,
            confidence REAL,
            video_timestamp REAL,
            notes TEXT,
            FOREIGN KEY (end_id) REFERENCES ends(id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_PATH}")


class GameRecorder:
    """Record game events for coaching review."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.current_game = None
        self.current_end = None

    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def start_game(self, sheet: int, team_red: str = "Red", team_yellow: str = "Yellow"):
        """Start a new game."""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO games (date, sheet, team_red, team_yellow)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d"), sheet, team_red, team_yellow))
        self.conn.commit()
        self.current_game = cursor.lastrowid
        self.current_end = None
        print(f"Started game {self.current_game}: {team_red} vs {team_yellow} on sheet {sheet}")
        return self.current_game

    def start_end(self, end_number: int, hammer_team: str):
        """Start a new end."""
        if not self.conn:
            self.connect()
        if not self.current_game:
            raise ValueError("No game started")

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ends (game_id, end_number, hammer_team)
            VALUES (?, ?, ?)
        """, (self.current_game, end_number, hammer_team))
        self.conn.commit()
        self.current_end = cursor.lastrowid
        print(f"Started end {end_number} (hammer: {hammer_team})")
        return self.current_end

    def record_shot(self, shot_number: int, team: str, rock_positions: list,
                    shot_type: str = None, result: str = None,
                    confidence: float = None, video_timestamp: float = None):
        """Record a single shot."""
        if not self.conn:
            self.connect()
        if not self.current_end:
            raise ValueError("No end started")

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO shots (end_id, shot_number, team, shot_type, rock_positions, result, confidence, video_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (self.current_end, shot_number, team, shot_type,
              json.dumps(rock_positions), result, confidence, video_timestamp))
        self.conn.commit()
        print(f"Recorded shot {shot_number}: {team} {shot_type or 'unknown'}")
        return cursor.lastrowid

    def end_game(self, score_red: int, score_yellow: int, notes: str = None):
        """Finalize the game."""
        if not self.conn:
            self.connect()
        if not self.current_game:
            raise ValueError("No game started")

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE games SET final_score_red = ?, final_score_yellow = ?, notes = ?
            WHERE id = ?
        """, (score_red, score_yellow, notes, self.current_game))
        self.conn.commit()
        print(f"Game ended: Red {score_red} - Yellow {score_yellow}")
        self.current_game = None
        self.current_end = None

    def get_game_summary(self, game_id: int = None) -> dict:
        """Get summary of a game."""
        if not self.conn:
            self.connect()

        game_id = game_id or self.current_game
        if not game_id:
            return None

        cursor = self.conn.cursor()

        # Get game info
        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        game = dict(cursor.fetchone())

        # Get ends
        cursor.execute("SELECT * FROM ends WHERE game_id = ? ORDER BY end_number", (game_id,))
        ends = [dict(row) for row in cursor.fetchall()]

        # Get shots for each end
        for end in ends:
            cursor.execute("SELECT * FROM shots WHERE end_id = ? ORDER BY shot_number", (end['id'],))
            end['shots'] = [dict(row) for row in cursor.fetchall()]

        game['ends'] = ends
        return game

    def search_shots(self, team: str = None, shot_type: str = None,
                     result: str = None) -> list:
        """Search for shots matching criteria."""
        if not self.conn:
            self.connect()

        query = """
            SELECT s.*, e.end_number, e.game_id
            FROM shots s
            JOIN ends e ON s.end_id = e.id
            WHERE 1=1
        """
        params = []

        if team:
            query += " AND s.team = ?"
            params.append(team)
        if shot_type:
            query += " AND s.shot_type = ?"
            params.append(shot_type)
        if result:
            query += " AND s.result = ?"
            params.append(result)

        query += " ORDER BY e.game_id, e.end_number, s.shot_number"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def demo():
    """Demo the game recorder."""
    print("=" * 60)
    print("COACHING REVIEW TOOL - DEMO")
    print("=" * 60)

    # Initialize database
    init_database()

    # Create recorder
    recorder = GameRecorder()

    # Start a game
    game_id = recorder.start_game(sheet=5, team_red="Fairbanks CC", team_yellow="Anchorage CC")

    # Record end 1
    recorder.start_end(1, hammer_team="team_yellow")

    # Record some shots
    recorder.record_shot(1, "team_red", [{"x": 350, "y": 700, "color": "red"}],
                        shot_type="draw", result="made", confidence=0.92, video_timestamp=15.3)
    recorder.record_shot(2, "team_yellow", [{"x": 350, "y": 695, "color": "red"},
                                            {"x": 355, "y": 700, "color": "yellow"}],
                        shot_type="draw", result="made", confidence=0.88, video_timestamp=42.7)

    # Get summary
    print("\n" + "=" * 60)
    print("GAME SUMMARY")
    print("=" * 60)
    summary = recorder.get_game_summary()
    print(json.dumps(summary, indent=2, default=str))

    # Search for shots
    print("\n" + "=" * 60)
    print("SEARCH: All draw shots")
    print("=" * 60)
    draws = recorder.search_shots(shot_type="draw")
    for shot in draws:
        print(f"End {shot['end_number']}, Shot {shot['shot_number']}: {shot['team']} - {shot['shot_type']}")

    recorder.close()


if __name__ == "__main__":
    demo()