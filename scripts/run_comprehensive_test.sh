#!/bin/bash
# Comprehensive Pi 5 Test Summary

cd /home/curl/curling_vision
source /home/curl/timer_env/bin/activate

echo "=============================================="
echo "Pi 5 Comprehensive Test Summary"
echo "=============================================="
echo ""

echo "=== 1. Hardware ==="
echo "RAM: $(free -h | grep Mem | awk '{print $2}')"
echo "CPU cores: $(nproc)"
echo "Disk available: $(df -h / | tail -1 | awk '{print $4}')"
echo ""

echo "=== 2. Inference Speed ==="
python3 -c "
import cv2
import json
import time
from inference import get_model

with open('/home/curl/curling_config.json') as f:
    config = json.load(f)

model = get_model(config['model_id'], api_key=config['api_key'])
cap = cv2.VideoCapture('/home/curl/Videos/curling/cam2_20260330_194005.mp4')

times = []
for i in range(30):
    ret, frame = cap.read()
    if not ret: break
    start = time.time()
    model.infer(frame, confidence=0.5)
    times.append(time.time() - start)
cap.release()

print(f'Near camera: {len(times)} frames')
print(f'Average: {sum(times)/len(times)*1000:.1f}ms ({1/(sum(times)/len(times)):.1f} FPS)')
"

echo ""
echo "=== 3. Wide Camera Model ==="
python3 -c "
import cv2
import json
import time
from inference import get_model

with open('/home/curl/curling_config.json') as f:
    config = json.load(f)

wide_model = get_model(config['roboflow']['wide_model_id'], api_key=config['roboflow']['api_key'])
cap = cv2.VideoCapture('/home/curl/Videos/curling/cam3_20260330_194005.mp4')

times = []
for i in range(20):
    ret, frame = cap.read()
    if not ret: break
    start = time.time()
    wide_model.infer(frame, confidence=0.5)
    times.append(time.time() - start)
cap.release()

print(f'Wide camera: {len(times)} frames')
print(f'Average: {sum(times)/len(times)*1000:.1f}ms ({1/(sum(times)/len(times)):.1f} FPS)')
"

echo ""
echo "=== 4. Detection Accuracy ==="
python3 -c "
import cv2
import json
from inference import get_model

with open('/home/curl/curling_config.json') as f:
    config = json.load(f)

model = get_model(config['model_id'], api_key=config['api_key'])
cap = cv2.VideoCapture('/home/curl/Videos/curling/cam2_20260330_194005.mp4')

counts = {'Button': 0, 'house': 0, 'red-rock': 0, 'yellow-rock': 0}
for i in range(50):
    ret, frame = cap.read()
    if not ret: break
    results = model.infer(frame, confidence=0.5)
    if results and len(results) > 0:
        for pred in results[0].predictions:
            if pred.class_name in counts:
                counts[pred.class_name] += 1
cap.release()

print('Detections in 50 frames:')
for cls, count in counts.items():
    print(f'  {cls}: {count}')
"

echo ""
echo "=== 5. Dashboard Server ==="
python3 scripts/dashboard_server.py &
SERVER_PID=$!
sleep 2

curl -s http://localhost:5000/health > /dev/null && echo "Health check: PASS" || echo "Health check: FAIL"
curl -s http://localhost:5000/curling_data.json > /dev/null && echo "Data endpoint: PASS" || echo "Data endpoint: FAIL"
curl -s http://localhost:5000/coach_api/games > /dev/null && echo "Coach API: PASS" || echo "Coach API: FAIL"
curl -s http://localhost:5000/bingo_api/events > /dev/null && echo "Bingo API: PASS" || echo "Bingo API: FAIL"

kill $SERVER_PID 2>/dev/null

echo ""
echo "=== 6. Memory Usage ==="
python3 -c "
import psutil
mem = psutil.virtual_memory()
print(f'Total: {mem.total / 1024**3:.1f} GB')
print(f'Available: {mem.available / 1024**3:.1f} GB')
print(f'Used: {mem.percent}%')
"

echo ""
echo "=============================================="
echo "Test Complete"
echo "=============================================="