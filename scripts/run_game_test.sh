#!/bin/bash
# Run game flow tracking test
source /home/curl/timer_env/bin/activate
cd /home/curl/curling_vision/scripts
python3 test_game_flow.py "$@"