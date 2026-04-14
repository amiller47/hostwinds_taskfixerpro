<?php
/**
 * Health Check Endpoint
 * Returns server status and timestamp.
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

echo json_encode([
    'status' => 'ok',
    'timestamp' => time(),
    'server_time' => date('Y-m-d H:i:s')
], JSON_PRETTY_PRINT);