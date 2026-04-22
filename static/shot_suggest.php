<?php
/**
 * Shot Calling API - Suggest Shot (root directory version)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$data = json_decode(file_get_contents('php://input'), true);

if (!$data) {
    http_response_code(400);
    echo json_encode(['error' => 'No game state provided'], JSON_PRETTY_PRINT);
    exit;
}

// Extract game state
$possession = $data['possession'] ?? 'team_red';
$score = $data['score'] ?? ['team_red' => 0, 'team_yellow' => 0];
$end = $data['end'] ?? 1;
$throws = $data['throws'] ?? ['team_red' => 0, 'team_yellow' => 0];
$hammer = $data['hammer'] ?? 'team_yellow';
$rocks_in_play = $data['rocks_in_play'] ?? 0;

$suggestions = [];

$is_last_shot = ($throws['team_red'] + $throws['team_yellow']) >= 15;
$our_score = $possession === 'team_red' ? $score['team_red'] : $score['team_yellow'];
$their_score = $possession === 'team_red' ? $score['team_yellow'] : $score['team_red'];
$we_have_hammer = $possession === $hammer;

if ($is_last_shot && $we_have_hammer) {
    if ($their_score > $our_score) {
        $suggestions[] = [
            'shot' => 'draw_to_button',
            'reason' => 'Need points to tie/win - draw to the button',
            'confidence' => 0.85
        ];
    } else {
        $suggestions[] = [
            'shot' => 'guard',
            'reason' => 'Protect your shot - draw up a guard',
            'confidence' => 0.75
        ];
    }
} elseif ($rocks_in_play === 0 && $throws['team_red'] === 0 && $throws['team_yellow'] === 0) {
    $suggestions[] = [
        'shot' => 'center_guard',
        'reason' => 'First rock - establish center guard',
        'confidence' => 0.90
    ];
} elseif ($rocks_in_play < 4) {
    $suggestions[] = [
        'shot' => 'draw_to_button',
        'reason' => 'Draw into the house to build position',
        'confidence' => 0.70
    ];
    $suggestions[] = [
        'shot' => 'guard',
        'reason' => 'Guard existing rocks in the house',
        'confidence' => 0.65
    ];
} else {
    if ($we_have_hammer) {
        $suggestions[] = [
            'shot' => 'freeze',
            'reason' => 'Freeze opponent rock for control',
            'confidence' => 0.65
        ];
    } else {
        $suggestions[] = [
            'shot' => 'takeout',
            'reason' => 'Clear opponent rocks to open house',
            'confidence' => 0.70
        ];
    }
}

$primary = $suggestions[0] ?? [
    'shot' => 'draw_to_button',
    'reason' => 'Default suggestion',
    'confidence' => 0.50
];

echo json_encode([
    'suggestion' => $primary,
    'alternatives' => array_slice($suggestions, 1),
    'situation' => [
        'is_last_shot' => $is_last_shot,
        'we_have_hammer' => $we_have_hammer,
        'rocks_in_play' => $rocks_in_play
    ]
], JSON_PRETTY_PRINT);