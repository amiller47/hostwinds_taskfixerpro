#!/usr/bin/env python3
"""
Dashboard Server - Serves game state as JSON for the web dashboard.
Compatible with the existing PHP dashboard format.

Run: python3 dashboard_server.py
Dashboard: http://localhost:5000/
"""

import json
import os
import time
import sqlite3
from flask import Flask, jsonify, send_from_directory, request
from pathlib import Path

app = Flask(__name__)

# Import bingo
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bingo import BingoGame, BINGO_EVENTS
from shot_caller import ShotCaller

# Global bingo game instance
_bingo_game = BingoGame()

# Data file for dashboard
DASHBOARD_DATA = Path(__file__).parent.parent / "dashboard_data.json"
DB_PATH = Path(__file__).parent.parent / "data" / "games.db"

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_game_state():
    """Load the latest game state from the tracker."""
    if DASHBOARD_DATA.exists():
        with open(DASHBOARD_DATA) as f:
            return json.load(f)
    return get_default_state()

def get_default_state():
    """Default game state."""
    return {
        "game_state": {
            "possession": "team_red",
            "next_shooter": None,
            "score": {"team_red": 0, "team_yellow": 0},
            "end": 1,
            "state": "idle",
            "throws": {"team_red": 0, "team_yellow": 0},
            "total_throws": 0
        },
        "locked_button": {"far": None, "near": None},
        "locked_house_size": {"far": None, "near": None},
        "current_raw_detections": {"far": [], "near": []},
        "wide_data": {
            "wide_rocks": [],
            "deliveries": False,
            "video_timestamp": "N/A"
        },
        "system_status": {
            "last_score": "No end completed yet",
            "fps": 0.0,
            "model": "fcc-curling-rock-detection/17"
        },
        "debug_logs": [],
        "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_update": time.time()
    }

@app.route('/')
def index():
    """Serve dashboard HTML."""
    return send_from_directory(Path(__file__).parent.parent / "static", "index.html")

@app.route('/curling_data.json')
def curling_data():
    """Serve game state as JSON (same format as PHP dashboard)."""
    state = load_game_state()
    state["received_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(state)

@app.route('/health')
def health():
    """Health check."""
    return jsonify({"status": "ok", "timestamp": time.time()})

# =========================================
# Coaching Review API
# =========================================

@app.route('/coach_api/games')
def get_games():
    """Get list of games with their ends and shots."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get games
        cursor.execute("""
            SELECT * FROM games 
            ORDER BY date DESC, created_at DESC
            LIMIT 50
        """)
        games = [dict(row) for row in cursor.fetchall()]
        
        # Get ends for each game
        for game in games:
            cursor.execute("""
                SELECT * FROM ends 
                WHERE game_id = ? 
                ORDER BY end_number
            """, (game['id'],))
            game['ends'] = [dict(row) for row in cursor.fetchall()]
            
            # Get shots for each end
            for end in game['ends']:
                cursor.execute("""
                    SELECT * FROM shots 
                    WHERE end_id = ? 
                    ORDER BY shot_number
                """, (end['id'],))
                end['shots'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(games)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/coach_api/shots')
def get_shots():
    """Search shots by team, type, result."""
    team = request.args.get('team')
    shot_type = request.args.get('shot_type')
    result = request.args.get('result')
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
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
        
        query += " ORDER BY e.game_id, e.end_number, s.shot_number LIMIT 100"
        
        cursor.execute(query, params)
        shots = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(shots)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/coach')
def coaching_review():
    """Coaching review page."""
    return send_from_directory(Path(__file__).parent.parent / "static", "coach.html")

# =========================================
# Bingo API
# =========================================

@app.route('/bingo_api/card')
def generate_bingo_card():
    """Generate a new bingo card."""
    card = _bingo_game.generate_card()
    return jsonify(card.to_dict())

@app.route('/bingo_api/card/<card_id>')
def get_bingo_card_status(card_id):
    """Get status of a bingo card."""
    status = _bingo_game.get_card_status(card_id)
    return jsonify(status)

@app.route('/bingo_api/events')
def get_bingo_events():
    """Get list of all possible bingo events."""
    return jsonify(BINGO_EVENTS)

@app.route('/bingo_api/occurred')
def get_occurred_events():
    """Get events that have occurred in current game."""
    return jsonify(list(_bingo_game.events_occurred))

@app.route('/bingo')
def bingo_page():
    """Bingo page."""
    return send_from_directory(Path(__file__).parent.parent / "static", "bingo.html")

# =========================================
# Shot Calling API
# =========================================

_shot_caller = ShotCaller()

@app.route('/shot_api/suggest', methods=['POST'])
def suggest_shot():
    """Suggest optimal shot based on house state."""
    data = request.get_json()
    
    rocks = data.get('rocks', [])
    team = data.get('team', 'team_red')
    hammer = data.get('hammer', 'team_yellow')
    score_red = data.get('score_red', 0)
    score_yellow = data.get('score_yellow', 0)
    end = data.get('end', 1)
    throws_remaining = data.get('throws_remaining', 16)
    
    suggestion = _shot_caller.suggest_shot(
        rocks, team, hammer, score_red, score_yellow, end, throws_remaining
    )
    
    return jsonify(suggestion)

@app.route('/shot_api/analyze', methods=['POST'])
def analyze_house():
    """Analyze house state."""
    data = request.get_json()
    rocks = data.get('rocks', [])
    
    analysis = _shot_caller.analyze_house(rocks)
    return jsonify(analysis)

@app.route('/shot')
def shot_page():
    """Shot calling page."""
    return send_from_directory(Path(__file__).parent.parent / "static", "shot.html")

def update_dashboard_data(game_state, detections=None, wide_data=None, debug_logs=None):
    """
    Update the dashboard data file.
    
    Call this from the game tracker to update the dashboard.
    
    Args:
        game_state: Dict with state, possession, score, throws, etc.
        detections: Dict with 'far' and 'near' detection lists
        wide_data: Dict with wide camera data
        debug_logs: List of debug messages
    """
    current = load_game_state()
    
    # Update game state
    if game_state:
        current["game_state"].update(game_state)
    
    # Update detections
    if detections:
        current["current_raw_detections"] = detections
    
    # Update wide data
    if wide_data:
        current["wide_data"] = wide_data
    
    # Update debug logs (keep last 20)
    if debug_logs:
        current["debug_logs"] = (debug_logs + current.get("debug_logs", []))[:20]
    
    current["received_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    current["last_update"] = time.time()
    
    with open(DASHBOARD_DATA, 'w') as f:
        json.dump(current, f, indent=2)
    
    return current

if __name__ == "__main__":
    # Create default data file if missing
    if not DASHBOARD_DATA.exists():
        with open(DASHBOARD_DATA, 'w') as f:
            json.dump(get_default_state(), f, indent=2)
        print(f"Created {DASHBOARD_DATA}")
    
    print("Dashboard server running at http://localhost:5000/")
    print("JSON data at http://localhost:5000/curling_data.json")
    app.run(host='0.0.0.0', port=5000, debug=False)