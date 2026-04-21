#!/bin/bash
# Test dashboard server with correct routes

cd /home/curl/curling_vision
source /home/curl/timer_env/bin/activate

echo "=== Dashboard Server Test ==="

# Start server in background
python3 scripts/dashboard_server.py &
SERVER_PID=$!
sleep 3

# Test endpoints
echo ""
echo "Testing /health..."
curl -s http://localhost:5000/health | python3 -m json.tool

echo ""
echo "Testing /curling_data.json..."
curl -s http://localhost:5000/curling_data.json | python3 -m json.tool 2>/dev/null | head -30

echo ""
echo "Testing /coach_api/games..."
curl -s http://localhost:5000/coach_api/games | python3 -m json.tool 2>/dev/null | head -20

echo ""
echo "Testing /bingo_api/card (generates new card)..."
curl -s http://localhost:5000/bingo_api/card | python3 -m json.tool 2>/dev/null | head -20

echo ""
echo "Testing /bingo_api/events..."
curl -s http://localhost:5000/bingo_api/events | python3 -m json.tool 2>/dev/null

echo ""
echo "Testing /shot_api/suggest (POST)..."
curl -s -X POST http://localhost:5000/shot_api/suggest \
  -H "Content-Type: application/json" \
  -d '{"rocks_red": 2, "rocks_yellow": 3, "hammer": "red"}' | python3 -m json.tool 2>/dev/null

# Stop server
kill $SERVER_PID 2>/dev/null

echo ""
echo "=== Dashboard Test Complete ==="