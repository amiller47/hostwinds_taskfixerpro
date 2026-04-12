#!/bin/bash
# Test various video sources
source /home/curl/timer_env/bin/activate
cd /home/curl/curling_vision

echo "Testing video source handler..."
echo ""

echo "1. Local file:"
python3 scripts/video_source.py /home/curl/Videos/sheet5NearCrop.mp4 2>&1 | head -8
echo ""

echo "2. YouTube (requires internet):"
python3 scripts/video_source.py "https://www.youtube.com/watch?v=jNQXAC9IVRw" 2>&1 | head -12
echo ""

echo "3. Check for USB cameras:"
cd /home/curl/curling_vision/scripts && python3 -c "from video_source import list_usb_cameras; print(f'Available: {list_usb_cameras()}')"
echo ""

echo "Done!"