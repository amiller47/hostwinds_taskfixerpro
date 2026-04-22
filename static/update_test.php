<?php
// Simple PHP test - should output JSON
header('Content-Type: application/json');
echo json_encode(['status' => 'ok', 'message' => 'PHP is working']);