#!/bin/bash
# Test dashboard server

cd /home/curl/curling_vision
source /home/curl/timer_env/bin/activate

echo "=== Dashboard Server Test ==="

# Start server in background
python3 scripts/dashboard_server.py &
SERVER_PID=$!
sleep 3

# Test endpoints
echo ""
echo "Testing health endpoint..."
curl -s http://localhost:5000/health | python3 -m json.tool

echo ""
echo "Testing game state endpoint..."
curl -s http://localhost:5000/api/game_state | python3 -m json.tool 2>/dev/null | head -30

echo ""
echo "Testing games endpoint..."
curl -s http://localhost:5000/api/games | python3 -m json.tool 2>/dev/null | head -20

echo ""
echo "Testing shot suggest endpoint..."
curl -s "http://localhost:5000/api/shot/suggest?rocks_red=2&rocks_yellow=3&hammer=red" | python3 -m json.tool 2>/dev/null

# Stop server
kill $SERVER_PID 2>/dev/null

echo ""
echo "=== Dashboard Test Complete ==="