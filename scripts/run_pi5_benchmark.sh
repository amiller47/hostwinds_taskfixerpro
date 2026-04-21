#!/bin/bash
# Pi 5 Benchmark and Testing Script
# Runs comprehensive tests on the new hardware

cd /home/curl/curling_vision
source /home/curl/timer_env/bin/activate

echo "=============================================="
echo "Pi 5 Curling Vision Benchmark"
echo "=============================================="
echo ""

# Check hardware
echo "=== Hardware ==="
echo "RAM: $(free -h | grep Mem | awk '{print $2}')"
echo "CPU: $(cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d: -f2 | xargs)"
echo "Disk: $(df -h / | tail -1 | awk '{print $4}')"
echo ""

# Test 1: Single camera detection speed
echo "=== Test 1: Single Camera Detection Speed ==="
python3 -c "
import time
import cv2
from inference import get_model
import json

with open('/home/curl/curling_config.json') as f:
    config = json.load(f)

model = get_model(config['model_id'], api_key=config['api_key'])

cap = cv2.VideoCapture('/home/curl/Videos/curling/cam2_20260330_194005.mp4')
times = []
for i in range(60):
    ret, frame = cap.read()
    if not ret:
        break
    start = time.time()
    results = model.infer(frame, confidence=0.5)
    times.append(time.time() - start)
cap.release()

print(f'Frames: {len(times)}')
print(f'Avg: {sum(times)/len(times)*1000:.1f}ms ({1/(sum(times)/len(times)):.1f} FPS)')
print(f'Min: {min(times)*1000:.1f}ms ({1/min(times):.1f} FPS)')
print(f'Max: {max(times)*1000:.1f}ms ({1/max(times):.1f} FPS)')
"
echo ""

# Test 2: Multi-camera simulation
echo "=== Test 2: Multi-Camera Throughput ==="
python3 -c "
import time
import cv2
from inference import get_model
import json
import threading
import queue

with open('/home/curl/curling_config.json') as f:
    config = json.load(f)

model = get_model(config['model_id'], api_key=config['api_key'])

# Load frames from both cameras
frames_near = []
frames_far = []

cap_near = cv2.VideoCapture('/home/curl/Videos/curling/cam2_20260330_194005.mp4')
cap_far = cv2.VideoCapture('/home/curl/Videos/curling/cam1_20260330_194005.mp4')

for i in range(30):
    ret, frame = cap_near.read()
    if ret:
        frames_near.append(frame)
    ret, frame = cap_far.read()
    if ret:
        frames_far.append(frame)

cap_near.release()
cap_far.release()

print(f'Loaded {len(frames_near)} near frames, {len(frames_far)} far frames')

# Process alternating
start = time.time()
for i in range(min(len(frames_near), len(frames_far))):
    model.infer(frames_near[i], confidence=0.5)
    model.infer(frames_far[i], confidence=0.5)
total = time.time() - start

frames_processed = min(len(frames_near), len(frames_far)) * 2
print(f'Processed {frames_processed} frames in {total:.2f}s')
print(f'Throughput: {frames_processed/total:.1f} FPS equivalent')
print(f'Per-camera: {frames_processed/total/2:.1f} FPS each')
"
echo ""

# Test 3: Game state machine
echo "=== Test 3: Game State Machine ==="
cd /home/curl/curling_vision/scripts
python3 -c "
import sys
sys.path.insert(0, '.')
from game_tracker import GameTracker

tracker = GameTracker()
print('GameTracker initialized successfully')
print(f'Initial state: {tracker.state}')
print(f'Initial possession: {tracker.possession}')
"
echo ""

# Test 4: Dashboard server startup
echo "=== Test 4: Dashboard Server Check ==="
if pgrep -f dashboard_server > /dev/null; then
    echo 'Dashboard already running'
    curl -s http://localhost:5000/health || echo 'Health check failed'
else
    echo 'Dashboard not running (will need manual start)'
fi
echo ""

# Test 5: Memory check for multi-model
echo "=== Test 5: Memory Footprint ==="
python3 -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Python process memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')

# Check system memory
mem = psutil.virtual_memory()
print(f'Total RAM: {mem.total / 1024 / 1024 / 1024:.1f} GB')
print(f'Available: {mem.available / 1024 / 1024 / 1024:.1f} GB')
print(f'Used: {mem.percent}%')
"
echo ""

echo "=============================================="
echo "Benchmark Complete"
echo "=============================================="