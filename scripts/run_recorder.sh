#!/bin/bash
source /home/curl/timer_env/bin/activate
cd /home/curl/curling_vision
python3 scripts/game_recorder.py "$@"