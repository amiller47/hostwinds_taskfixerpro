<?php
/**
 * Shot Calling API - Analyze Shot Endpoint
 * Analyze a proposed shot and predict outcome.
 *
 * Usage: POST /api/shot_analyze.php
 * Body: JSON with proposed shot and game state
 * Returns: JSON with analysis
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');

$data = json_decode(file_get_contents('php://input'), true);

if (!$data) {
    http_response_code(400);
    echo json_encode(['error' => 'No shot data provided'], JSON_PRETTY_PRINT);
    exit;
}

$shot_type = $data['shot_type'] ?? 'draw_to_button';
$difficulty = $data['difficulty'] ?? 'medium';
$game_state = $data['game_state'] ?? [];

// Shot type definitions with difficulty and success rates
$shot_definitions = [
    'draw_to_button' => [
        'name' => 'Draw to the Button',
        'base_difficulty' => 'medium',
        'success_rate' => 0.75,
        'description' => 'Draw to the center of the house'
    ],
    'takeout' => [
        'name' => 'Takeout',
        'base_difficulty' => 'easy',
        'success_rate' => 0.85,
        'description' => 'Hit and remove opponent stone'
    ],
    'guard' => [
        'name' => 'Guard',
        'base_difficulty' => 'easy',
        'success_rate' => 0.90,
        'description' => 'Place a stone in front of the house'
    ],
    'freeze' => [
        'name' => 'Freeze',
        'base_difficulty' => 'hard',
        'success_rate' => 0.55,
        'description' => 'Draw to freeze on another stone'
    ],
    'raise' => [
        'name' => 'Raise',
        'base_difficulty' => 'hard',
        'success_rate' => 0.50,
        'description' => 'Hit a stone to move it into scoring position'
    ],
    'hit_and_roll' => [
        'name' => 'Hit and Roll',
        'base_difficulty' => 'medium',
        'success_rate' => 0.65,
        'description' => 'Hit and roll into the house'
    ],
    'double_takeout' => [
        'name' => 'Double Takeout',
        'base_difficulty' => 'hard',
        'success_rate' => 0.45,
        'description' => 'Remove two opponent stones'
    ],
    'peel' => [
        'name' => 'Peel Guard',
        'base_difficulty' => 'medium',
        'success_rate' => 0.70,
        'description' => 'Remove a guard stone'
    ],
    'wick' => [
        'name' => 'Wick',
        'base_difficulty' => 'very_hard',
        'success_rate' => 0.35,
        'description' => 'Touch a stone and roll to position'
    ],
    'come_around' => [
        'name' => 'Come Around',
        'base_difficulty' => 'medium',
        'success_rate' => 0.65,
        'description' => 'Curl behind a guard'
    ]
];

// Get shot definition
$shot_def = $shot_definitions[$shot_type] ?? [
    'name' => 'Unknown Shot',
    'base_difficulty' => 'unknown',
    'success_rate' => 0.50,
    'description' => 'Unknown shot type'
];

// Adjust success rate based on conditions
$conditions = $game_state['conditions'] ?? 'normal';
$ice_condition_modifier = match($conditions) {
    'fast_ice' => 0.95,
    'slow_ice' => 0.90,
    'heavy_ice' => 0.85,
    default => 1.0
};

$final_success_rate = $shot_def['success_rate'] * $ice_condition_modifier;

// Risk assessment
$risk_factors = [];
if ($final_success_rate < 0.50) {
    $risk_factors[] = 'High risk shot';
}
if ($shot_def['base_difficulty'] === 'hard' || $shot_def['base_difficulty'] === 'very_hard') {
    $risk_factors[] = 'Requires precision';
}

echo json_encode([
    'shot_type' => $shot_type,
    'shot_name' => $shot_def['name'],
    'description' => $shot_def['description'],
    'difficulty' => $shot_def['base_difficulty'],
    'success_probability' => round($final_success_rate, 2),
    'risk_factors' => $risk_factors,
    'recommendations' => [
        'Practice this shot in warmup' => $shot_def['base_difficulty'] === 'hard',
        'Consider a simpler alternative' => $final_success_rate < 0.55,
        'Good choice for this situation' => $final_success_rate > 0.70
    ]
], JSON_PRETTY_PRINT);