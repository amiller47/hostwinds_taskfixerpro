#!/bin/bash
pkill -f dashboard_server.py 2>/dev/null
sleep 1
cd /home/curl/curling_vision
python3 scripts/dashboard_server.py