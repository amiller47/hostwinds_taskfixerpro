<?php
/**
 * Bingo Events API - Get events that have occurred
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Read occurred events from file (populated by realtime_dashboard.py)
$events_file = __DIR__ . '/data/bingo_events.json';

if (file_exists($events_file)) {
    $events = json_decode(file_get_contents($events_file), true);
    echo json_encode($events ?: [], JSON_PRETTY_PRINT);
} else {
    // Return empty array if no events file
    echo json_encode([], JSON_PRETTY_PRINT);
}