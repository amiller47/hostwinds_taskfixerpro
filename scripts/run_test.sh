#!/bin/bash
# Run curling detection test
source /home/curl/timer_env/bin/activate
cd /home/curl/curling_vision/scripts
python3 test_detections.py "$@"