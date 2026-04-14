<?php
/**
 * Bingo API - Events Occurred Endpoint
 * Get list of events that have occurred in the current game.
 *
 * Usage: GET /api/bingo_occurred.php
 * Returns: JSON array of occurred event IDs
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// For now, return events from the current game state
// In production, this would query the game tracker
$occurred_file = __DIR__ . '/../data/bingo_occurred.json';

if (file_exists($occurred_file)) {
    echo file_get_contents($occurred_file);
} else {
    // Default: no events occurred yet
    echo json_encode([
        'events' => [],
        'last_update' => time()
    ], JSON_PRETTY_PRINT);
}