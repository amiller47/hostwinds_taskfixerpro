<?php
/**
 * Bingo API - Card Management Endpoint
 * Generate and manage bingo cards.
 *
 * Usage:
 *   GET /api/bingo_card.php         - Generate new card
 *   GET /api/bingo_card.php?id=X     - Get specific card
 *   POST /api/bingo_card.php?id=X    - Mark event on card
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST');

require_once __DIR__ . '/bingo_functions.php';

$method = $_SERVER['REQUEST_METHOD'];
$card_id = isset($_GET['id']) ? $_GET['id'] : null;

try {
    if ($method === 'GET') {
        if ($card_id) {
            // Get specific card
            $card = getBingoCard($card_id);
            if ($card) {
                echo json_encode($card, JSON_PRETTY_PRINT);
            } else {
                http_response_code(404);
                echo json_encode(['error' => 'Card not found'], JSON_PRETTY_PRINT);
            }
        } else {
            // Generate new card
            $card = generateBingoCard();
            echo json_encode($card, JSON_PRETTY_PRINT);
        }
    } elseif ($method === 'POST') {
        // Mark event on card
        $data = json_decode(file_get_contents('php://input'), true);
        if (!$card_id) {
            http_response_code(400);
            echo json_encode(['error' => 'Card ID required'], JSON_PRETTY_PRINT);
            exit;
        }
        $event_id = $data['event_id'] ?? null;
        if (!$event_id) {
            http_response_code(400);
            echo json_encode(['error' => 'Event ID required'], JSON_PRETTY_PRINT);
            exit;
        }
        $result = markBingoEvent($card_id, $event_id);
        echo json_encode($result, JSON_PRETTY_PRINT);
    } else {
        http_response_code(405);
        echo json_encode(['error' => 'Method not allowed'], JSON_PRETTY_PRINT);
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()], JSON_PRETTY_PRINT);
}