<?php
/**
 * Bingo Card API - Root directory version
 * 
 * Usage:
 *   GET /bingo_card.php         - Generate new card
 *   GET /bingo_card.php?id=X    - Get specific card
 *   POST /bingo_card.php?id=X   - Mark event on card
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Bingo events for curling
$BINGO_EVENTS = [
    'draw_to_button' => 'Draw to the button',
    'takeout' => 'Takeout',
    'guard' => 'Guard',
    'freeze' => 'Freeze',
    'raise' => 'Raise',
    'hit_and_roll' => 'Hit and roll',
    'double_takeout' => 'Double takeout',
    'peel' => 'Peel guard',
    'wick' => 'Wick / Wickback',
    'come_around' => 'Come around guard',
    'tap_back' => 'Tap back',
    'corner_freeze' => 'Corner freeze',
    'promote' => 'Promote rock',
    'clearing' => 'Clearing takeout',
    'blank_end' => 'Blank end',
    'score_two' => 'Score 2+ points',
    'steal' => 'Steal',
    'split' => 'Split the house',
    'center_guard' => 'Center guard',
    'corner_guard' => 'Corner guard',
    'in_house' => 'Rock in house',
    'biting_12' => 'Biting 12 oclock'
];

function generateBingoCard() {
    global $BINGO_EVENTS;
    
    $event_keys = array_keys($BINGO_EVENTS);
    shuffle($event_keys);
    
    $selected = array_slice($event_keys, 0, 24);
    
    $card = [
        'id' => uniqid('bingo_'),
        'created_at' => time(),
        'events' => []
    ];
    
    $idx = 0;
    for ($row = 0; $row < 5; $row++) {
        for ($col = 0; $col < 5; $col++) {
            $key = $row . '_' . $col;
            if ($row === 2 && $col === 2) {
                $card['events'][$key] = [
                    'id' => 'free',
                    'name' => 'FREE',
                    'marked' => true
                ];
            } else {
                $event_id = $selected[$idx];
                $card['events'][$key] = [
                    'id' => $event_id,
                    'name' => $BINGO_EVENTS[$event_id],
                    'marked' => false
                ];
                $idx++;
            }
        }
    }
    
    // Save card
    $cards_dir = __DIR__ . '/data/bingo_cards';
    if (!is_dir($cards_dir)) {
        mkdir($cards_dir, 0755, true);
    }
    file_put_contents($cards_dir . '/' . $card['id'] . '.json', json_encode($card));
    
    return $card;
}

function getBingoCard($card_id) {
    $cards_dir = __DIR__ . '/data/bingo_cards';
    $file = $cards_dir . '/' . $card_id . '.json';
    
    if (!file_exists($file)) {
        return null;
    }
    
    return json_decode(file_get_contents($file), true);
}

function markBingoEvent($card_id, $event_id) {
    $card = getBingoCard($card_id);
    if (!$card) {
        return ['error' => 'Card not found'];
    }
    
    $found = false;
    foreach ($card['events'] as $key => &$event) {
        if ($event['id'] === $event_id && !$event['marked']) {
            $event['marked'] = true;
            $found = true;
            break;
        }
    }
    
    if (!$found) {
        return ['error' => 'Event not found or already marked'];
    }
    
    // Save updated card
    $cards_dir = __DIR__ . '/data/bingo_cards';
    file_put_contents($cards_dir . '/' . $card_id . '.json', json_encode($card));
    
    // Check for bingo
    $bingo = checkBingo($card);
    
    return [
        'success' => true,
        'card' => $card,
        'bingo' => $bingo
    ];
}

function checkBingo($card) {
    $events = $card['events'];
    
    // Check rows
    for ($row = 0; $row < 5; $row++) {
        $bingo = true;
        for ($col = 0; $col < 5; $col++) {
            $key = $row . '_' . $col;
            if (!$events[$key]['marked']) {
                $bingo = false;
                break;
            }
        }
        if ($bingo) return true;
    }
    
    // Check columns
    for ($col = 0; $col < 5; $col++) {
        $bingo = true;
        for ($row = 0; $row < 5; $row++) {
            $key = $row . '_' . $col;
            if (!$events[$key]['marked']) {
                $bingo = false;
                break;
            }
        }
        if ($bingo) return true;
    }
    
    // Check diagonals
    $diag1 = true;
    $diag2 = true;
    for ($i = 0; $i < 5; $i++) {
        $key1 = $i . '_' . $i;
        $key2 = $i . '_' . (4-$i);
        if (!$events[$key1]['marked']) $diag1 = false;
        if (!$events[$key2]['marked']) $diag2 = false;
    }
    
    return $diag1 || $diag2;
}

// Main logic
$method = $_SERVER['REQUEST_METHOD'];
$card_id = isset($_GET['id']) ? $_GET['id'] : null;

try {
    if ($method === 'GET') {
        if ($card_id) {
            $card = getBingoCard($card_id);
            if ($card) {
                echo json_encode($card, JSON_PRETTY_PRINT);
            } else {
                http_response_code(404);
                echo json_encode(['error' => 'Card not found'], JSON_PRETTY_PRINT);
            }
        } else {
            $card = generateBingoCard();
            echo json_encode($card, JSON_PRETTY_PRINT);
        }
    } elseif ($method === 'POST') {
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