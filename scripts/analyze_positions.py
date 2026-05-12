#!/usr/bin/env python3
"""Analyze rock positions relative to button and house"""
import json
import sys

def analyze_detections(data_file='dashboard_data.json'):
    with open(data_file) as f:
        data = json.load(f)
    
    far_dets = data.get('current_raw_detections', {}).get('far', [])
    near_dets = data.get('current_raw_detections', {}).get('near', [])
    
    far_button = data.get('locked_button', {}).get('far', [360, 596])
    near_button = data.get('locked_button', {}).get('near', [349, 697])
    far_house = data.get('locked_house_size', {}).get('far', 540)
    near_house = data.get('locked_house_size', {}).get('near', 540)
    
    print(f"=== FAR CAMERA ===")
    print(f"Button: {far_button}")
    print(f"House size: {far_house}px")
    print(f"House Y range: {far_button[1] - far_house//2} to {far_button[1] + far_house//2}")
    print()
    
    # Count rocks in house vs out
    rocks_in_house = []
    rocks_out = []
    
    for det in far_dets:
        name, x, y, conf = det
        if 'rock' in name.lower():
            y_min = far_button[1] - far_house//2
            y_max = far_button[1] + far_house//2
            if y_min <= y <= y_max:
                rocks_in_house.append((name, x, y, conf))
            else:
                rocks_out.append((name, x, y, conf))
    
    print(f"Rocks in house: {len(rocks_in_house)}")
    for r in rocks_in_house:
        print(f"  {r[0]}: ({r[1]:.0f}, {r[2]:.0f}) conf={r[3]:.2f}")
    
    print(f"\nRocks outside house: {len(rocks_out)}")
    for r in rocks_out[:20]:  # Show first 20
        print(f"  {r[0]}: ({r[1]:.0f}, {r[2]:.0f}) conf={r[3]:.2f}")
    
    # Group by Y position ranges
    y_ranges = {
        'hack (Y>1000)': 0,
        'house (Y 200-1000)': 0,
        'above house (Y<200)': 0
    }
    
    for det in far_dets:
        name, x, y, conf = det
        if 'rock' in name.lower():
            if y > 1000:
                y_ranges['hack (Y>1000)'] += 1
            elif y >= 200:
                y_ranges['house (Y 200-1000)'] += 1
            else:
                y_ranges['above house (Y<200)'] += 1
    
    print(f"\nRocks by Y position:")
    for range_name, count in y_ranges.items():
        print(f"  {range_name}: {count}")
    
    print(f"\n=== NEAR CAMERA ===")
    print(f"Button: {near_button}")
    print(f"House size: {near_house}px")
    print(f"Detections: {len(near_dets)}")
    
    for det in near_dets[:10]:
        print(f"  {det}")

if __name__ == '__main__':
    analyze_detections()