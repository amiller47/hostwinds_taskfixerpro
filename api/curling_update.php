<?php
/**
 * Receive game state updates from the Pi and write to dashboard_data.json
 * 
 * This endpoint is called by realtime_dashboard.py with --upload flag
 * to push live game data to the Hostwinds server.
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Only accept POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

// Get JSON input
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if ($data === null) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON']);
    exit;
}

// Validate required fields (minimal check)
// Accept either top-level current_end or nested game_state.end
if (!isset($data['game_state'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing field: game_state']);
    exit;
}

// If current_end is not at top level, extract from game_state
if (!isset($data['current_end']) && isset($data['game_state']['end'])) {
    $data['current_end'] = $data['game_state']['end'];
}

// Write to data file
$data_dir = __DIR__ . '/../data/';
$data_file = $data_dir . 'dashboard_data.json';

// Ensure data directory exists
if (!is_dir($data_dir)) {
    mkdir($data_dir, 0755, true);
}

// Add timestamp
$data['last_update'] = date('c');
$data['source'] = 'pi_upload';

// Write the data
$written = file_put_contents($data_file, json_encode($data, JSON_PRETTY_PRINT));

if ($written === false) {
    http_response_code(500);
    echo json_encode(['error' => 'Failed to write data file']);
    exit;
}

// Success
echo json_encode([
    'status' => 'ok',
    'bytes_written' => $written,
    'timestamp' => date('c')
]);