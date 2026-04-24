<?php
/**
 * Snapshot Upload API - Receive frame snapshots from Pi
 * Saves as snapshot_0.jpg (or snapshot_1.jpg for wide camera)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$data_dir = __DIR__ . '/data';
if (!is_dir($data_dir)) {
    mkdir($data_dir, 0755, true);
}

if (!isset($_FILES['snapshot'])) {
    http_response_code(400);
    echo json_encode(['error' => 'No snapshot file provided'], JSON_PRETTY_PRINT);
    exit;
}

$file = $_FILES['snapshot'];
$filename = basename($file['name']);
$safe_filename = preg_replace('/[^a-zA-Z0-9_\-\.]/', '', $filename);

// Only allow snapshot_0.jpg, snapshot_1.jpg, etc.
if (!preg_match('/^snapshot_[0-9]+\.jpg$/', $safe_filename)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid filename'], JSON_PRETTY_PRINT);
    exit;
}

$destination = $data_dir . '/' . $safe_filename;

if (move_uploaded_file($file['tmp_name'], $destination)) {
    echo json_encode([
        'success' => true,
        'filename' => $safe_filename,
        'path' => '/curling/data/' . $safe_filename,
        'size' => filesize($destination),
        'timestamp' => date('Y-m-d H:i:s')
    ], JSON_PRETTY_PRINT);
} else {
    http_response_code(500);
    echo json_encode(['error' => 'Failed to save snapshot'], JSON_PRETTY_PRINT);
}