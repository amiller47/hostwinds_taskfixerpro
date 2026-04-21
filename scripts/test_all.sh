#!/bin/bash
# Full test of dashboard and web UIs

cd /home/curl/curling_vision
source /home/curl/timer_env/bin/activate

echo "=== Web UI Test ==="

python3 scripts/dashboard_server.py &
SERVER_PID=$!
sleep 3

echo ""
echo "Main dashboard (/) - checking for HTML..."
curl -s http://localhost:5000/ | grep -E "<title>|<h1>" | head -3

echo ""
echo "Coach page (/coach)..."
curl -s http://localhost:5000/coach | grep -E "<title>|<h1>" | head -3

echo ""
echo "Bingo page (/bingo)..."
curl -s http://localhost:5000/bingo | grep -E "<title>|<h1>" | head -3

echo ""
echo "Shot calling page (/shot)..."
curl -s http://localhost:5000/shot | grep -E "<title>|<h1>" | head -3

kill $SERVER_PID 2>/dev/null

echo ""
echo "=== Web UI Test Complete ==="