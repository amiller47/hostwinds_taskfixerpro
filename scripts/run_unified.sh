#!/bin/bash
source /home/curl/timer_env/bin/activate
cd /home/curl/curling_vision/scripts
python3 unified_processor.py "$@"