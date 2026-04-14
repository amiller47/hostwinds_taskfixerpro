<?php
/**
 * Coaching Review API - Games List Endpoint
 * Returns list of games with their ends and shots.
 *
 * Usage: GET /api/games.php
 * Query params: limit (default 50)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$db_path = __DIR__ . '/../data/games.db';
$limit = isset($_GET['limit']) ? max(1, intval($_GET['limit'])) : 50;

try {
    $db = new SQLite3($db_path);
    $db->enableExceptions(true);

    // Get games
    $games = [];
    $result = $db->query("SELECT * FROM games ORDER BY date DESC, created_at DESC LIMIT $limit");
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
        $games[] = $row;
    }

    // Get ends and shots for each game
    foreach ($games as &$game) {
        $game_id = $game['id'];

        // Get ends
        $game['ends'] = [];
        $ends_result = $db->query("SELECT * FROM ends WHERE game_id = $game_id ORDER BY end_number");
        while ($end_row = $ends_result->fetchArray(SQLITE3_ASSOC)) {
            $end = $end_row;
            $end_id = $end['id'];

            // Get shots for this end
            $end['shots'] = [];
            $shots_result = $db->query("SELECT * FROM shots WHERE end_id = $end_id ORDER BY shot_number");
            while ($shot_row = $shots_result->fetchArray(SQLITE3_ASSOC)) {
                $end['shots'][] = $shot_row;
            }
            $game['ends'][] = $end;
        }
    }

    $db->close();
    echo json_encode($games, JSON_PRETTY_PRINT);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()], JSON_PRETTY_PRINT);
}