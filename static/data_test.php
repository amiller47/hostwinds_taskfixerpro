<?php
/**
 * Simple write test - writes to data directory
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$test_data = [
    'status' => 'ok',
    'timestamp' => date('c'),
    'message' => 'PHP write test successful'
];

$data_dir = __DIR__ . '/data/';
$data_file = $data_dir . 'php_test.json';

// Ensure data directory exists
if (!is_dir($data_dir)) {
    mkdir($data_dir, 0755, true);
}

$written = file_put_contents($data_file, json_encode($test_data, JSON_PRETTY_PRINT));

if ($written === false) {
    echo json_encode(['error' => 'Failed to write', 'dir' => $data_dir]);
} else {
    echo json_encode([
        'status' => 'ok',
        'bytes_written' => $written,
        'file' => $data_file,
        'data' => $test_data
    ]);
}