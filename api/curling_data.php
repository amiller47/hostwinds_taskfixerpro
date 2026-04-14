<?php
/**
 * Curling Dashboard API - Game State Endpoint
 * Serves current game state as JSON for the dashboard.
 *
 * Usage: GET /api/curling_data.php
 * Returns: JSON game state
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$data_file = __DIR__ . '/../data/dashboard_data.json';

// Default state if no data file exists
$default_state = [
    'game_state' => [
        'possession' => 'team_red',
        'next_shooter' => null,
        'score' => ['team_red' => 0, 'team_yellow' => 0],
        'end' => 1,
        'state' => 'idle',
        'throws' => ['team_red' => 0, 'team_yellow' => 0],
        'total_throws' => 0
    ],
    'locked_button' => ['far' => null, 'near' => null],
    'locked_house_size' => ['far' => null, 'near' => null],
    'current_raw_detections' => ['far' => [], 'near' => []],
    'wide_data' => [
        'wide_rocks' => [],
        'deliveries' => false,
        'video_timestamp' => 'N/A'
    ],
    'system_status' => [
        'last_score' => 'No end completed yet',
        'fps' => 0.0,
        'model' => 'fcc-curling-rock-detection/17'
    ],
    'debug_logs' => [],
    'received_at' => date('Y-m-d H:i:s'),
    'last_update' => time()
];

if (file_exists($data_file)) {
    $json = file_get_contents($data_file);
    $state = json_decode($json, true);
    if ($state) {
        $state['received_at'] = date('Y-m-d H:i:s');
        echo json_encode($state, JSON_PRETTY_PRINT);
    } else {
        echo json_encode($default_state, JSON_PRETTY_PRINT);
    }
} else {
    echo json_encode($default_state, JSON_PRETTY_PRINT);
}