<?php
/**
 * Bingo Functions Library
 * Shared functions for bingo card management.
 */

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
    'corner_guard' => 'Corner guard'
];

/**
 * Generate a new 5x5 bingo card with random events.
 */
function generateBingoCard() {
    global $BINGO_EVENTS;

    $event_keys = array_keys($BINGO_EVENTS);
    shuffle($event_keys);

    // Select 24 events (center is FREE)
    $selected = array_slice($event_keys, 0, 24);

    $card = [
        'id' => uniqid('bingo_'),
        'created_at' => time(),
        'events' => []
    ];

    // Build 5x5 grid
    $idx = 0;
    for ($row = 0; $row < 5; $row++) {
        for ($col = 0; $col < 5; $col++) {
            $key = "{$row}_{$col}";
            if ($row === 2 && $col === 2) {
                $card['events'][$key] = [
                    'id' => 'free',
                    'name' => 'FREE',
                    'marked' => true
                ];
            } else {
                $event_id = $selected[$idx++];
                $card['events'][$key] = [
                    'id' => $event_id,
                    'name' => $BINGO_EVENTS[$event_id],
                    'marked' => false
                ];
            }
        }
    }

    // Save card to file (simple file-based storage)
    $cards_dir = __DIR__ . '/../data/bingo_cards';
    if (!is_dir($cards_dir)) {
        mkdir($cards_dir, 0755, true);
    }
    file_put_contents("$cards_dir/{$card['id']}.json", json_encode($card));

    return $card;
}

/**
 * Get a specific bingo card.
 */
function getBingoCard($card_id) {
    $cards_dir = __DIR__ . '/../data/bingo_cards';
    $file = "$cards_dir/$card_id.json";

    if (!file_exists($file)) {
        return null;
    }

    return json_decode(file_get_contents($file), true);
}

/**
 * Mark an event on a bingo card.
 */
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
    $cards_dir = __DIR__ . '/../data/bingo_cards';
    file_put_contents("$cards_dir/$card_id.json", json_encode($card));

    // Check for bingo
    $bingo = checkBingo($card);

    return [
        'success' => true,
        'card' => $card,
        'bingo' => $bingo
    ];
}

/**
 * Check if card has a bingo.
 */
function checkBingo($card) {
    $events = $card['events'];

    // Check rows
    for ($row = 0; $row < 5; $row++) {
        $bingo = true;
        for ($col = 0; $col < 5; $col++) {
            if (!$events["{$row}_{$col}"]['marked']) {
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
            if (!$events["{$row}_{$col}"]['marked']) {
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
        if (!$events["{$i}_{$i}"]['marked']) $diag1 = false;
        if (!$events["{$i}_" . (4-$i)"]['marked']) $diag2 = false;
    }

    return $diag1 || $diag2;
}