#!/bin/bash
# Pi 5 Full Testing Suite
cd /home/curl/curling_vision
source /home/curl/timer_env/bin/activate

echo "=============================================="
echo "Pi 5 Full Test Suite"
echo "=============================================="

# Test 3: Game State Machine with proper init
echo ""
echo "=== Test 3: Game State Machine ==="
python3 -c "
import json
import sys
sys.path.insert(0, 'scripts')
from game_tracker import GameTracker

# Load calibration
with open('config/calibration.json') as f:
    calib = json.load(f)

# Create tracker
tracker = GameTracker(
    calibration=calib['calibration_sets']['rtsp'],
    config={'camera': 'near'}
)
print(f'GameTracker initialized')
print(f'State: {tracker.state}')
print(f'Possession: {tracker.possession}')
print(f'Throws: {tracker.throws}')
"

# Test 4: Detection accuracy on test video
echo ""
echo "=== Test 4: Detection Accuracy (100 frames) ==="
python3 -c "
import cv2
import json
from inference import get_model
from collections import Counter

with open('/home/curl/curling_config.json') as f:
    config = json.load(f)

model = get_model(config['model_id'], api_key=config['api_key'])

cap = cv2.VideoCapture('/home/curl/Videos/curling/cam2_20260330_194005.mp4')
detections = Counter()
confidences = {'button': [], 'red-rock': [], 'yellow-rock': [], 'house': [], 'curling delivery': []}

for i in range(100):
    ret, frame = cap.read()
    if not ret:
        break
    results = model.infer(frame, confidence=0.5)
    for pred in results:
        detections[pred.class_name] += 1
        if pred.class_name in confidences:
            confidences[pred.class_name].append(pred.confidence)

cap.release()

print(f'Processed 100 frames')
print(f'')
print('Detection counts:')
for cls, count in detections.most_common():
    avg_conf = sum(confidences.get(cls, [0])) / max(len(confidences.get(cls, [])), 1)
    print(f'  {cls}: {count} (avg conf: {avg_conf:.2f})')
"

# Test 5: Wide camera model
echo ""
echo "=== Test 5: Wide Camera Model ==="
python3 -c "
import cv2
import json
from inference import get_model
import time

with open('/home/curl/curling_config.json') as f:
    config = json.load(f)

print('Loading wide model...')
start = time.time()
wide_model = get_model(config['roboflow']['wide_model_id'], api_key=config['roboflow']['api_key'])
print(f'Model loaded in {time.time() - start:.2f}s')

cap = cv2.VideoCapture('/home/curl/Videos/curling/cam3_20260330_194005.mp4')

times = []
for i in range(30):
    ret, frame = cap.read()
    if not ret:
        break
    start = time.time()
    results = wide_model.infer(frame, confidence=0.5)
    times.append(time.time() - start)
cap.release()

print(f'Wide camera: {len(times)} frames')
print(f'Avg: {sum(times)/len(times)*1000:.1f}ms ({1/(sum(times)/len(times)):.1f} FPS)')
"

# Test 6: Multi-frame throughput with buffering
echo ""
echo "=== Test 6: Frame Buffering Performance ==="
python3 -c "
import cv2
import json
from inference import get_model
import time

with open('/home/curl/curling_config.json') as f:
    config = json.load(f)

model = get_model(config['model_id'], api_key=config['api_key'])

# Load all frames into memory first
cap = cv2.VideoCapture('/home/curl/Videos/curling/cam2_20260330_194005.mp4')
frames = []
while len(frames) < 300:
    ret, frame = cap.read()
    if not ret:
        break
    frames.append(frame)
cap.release()

print(f'Loaded {len(frames)} frames into memory')
print(f'Memory: ~{len(frames) * frames[0].nbytes / 1024 / 1024:.1f} MB for frame buffer')

# Process all frames
start = time.time()
for frame in frames:
    model.infer(frame, confidence=0.5)
total = time.time() - start

print(f'Processed {len(frames)} frames in {total:.2f}s')
print(f'Average: {total/len(frames)*1000:.1f}ms per frame')
print(f'Throughput: {len(frames)/total:.1f} FPS')
"

# Test 7: Check wide camera detection classes
echo ""
echo "=== Test 7: Wide Camera Detection Classes ==="
python3 -c "
import cv2
import json
from inference import get_model
from collections import Counter

with open('/home/curl/curling_config.json') as f:
    config = json.load(f)

wide_model = get_model(config['roboflow']['wide_model_id'], api_key=config['roboflow']['api_key'])

cap = cv2.VideoCapture('/home/curl/Videos/curling/cam3_20260330_194005.mp4')

detections = Counter()
for i in range(50):
    ret, frame = cap.read()
    if not ret:
        break
    results = wide_model.infer(frame, confidence=0.4)
    for pred in results:
        detections[pred.class_name] += 1
cap.release()

print('Wide camera detections (50 frames):')
for cls, count in detections.most_common():
    print(f'  {cls}: {count}')
"

echo ""
echo "=============================================="
echo "Full Test Complete"
echo "=============================================="