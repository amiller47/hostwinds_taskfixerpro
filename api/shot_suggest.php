<?php
/**
 * Shot Calling API - Suggest Shot Endpoint
 * Suggest the best shot based on current game state.
 *
 * Usage: POST /api/shot_suggest.php
 * Body: JSON with game state
 * Returns: JSON with suggested shot
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');

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
$hammer = $data['hammer'] ?? 'team_yellow'; // Team with last stone advantage
$rocks_in_play = $data['rocks_in_play'] ?? 0;
$game_type = $data['game_type'] ?? 'mens'; // mens, womens, mixed

// Simple heuristic-based shot suggestion
// This is a simplified version - the real logic would be in Python
$suggestions = [];

// Determine situation
$is_last_shot = ($throws['team_red'] + $throws['team_yellow']) >= 15;
$our_score = $possession === 'team_red' ? $score['team_red'] : $score['team_yellow'];
$their_score = $possession === 'team_red' ? $score['team_yellow'] : $score['team_red'];
$we_have_hammer = $possession === $hammer;

// Basic heuristics
if ($is_last_shot && $we_have_hammer) {
    // Last shot with hammer - draw for win/tie
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
    // First rock - center guard
    $suggestions[] = [
        'shot' => 'center_guard',
        'reason' => 'First rock - establish center guard',
        'confidence' => 0.90
    ];
} elseif ($rocks_in_play < 4) {
    // Early game - build house
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
    // Mid-late game - tactical
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

// Primary suggestion
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