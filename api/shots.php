<?php
/**
 * Coaching Review API - Shot Search Endpoint
 * Search shots by team, type, result.
 *
 * Usage: GET /api/shots.php?team=red&shot_type=draw&result=made
 * Query params: team, shot_type, result, limit
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$db_path = __DIR__ . '/../data/games.db';
$limit = isset($_GET['limit']) ? max(1, intval($_GET['limit'])) : 100;

try {
    $db = new SQLite3($db_path);
    $db->enableExceptions(true);

    $where_clauses = [];
    $params = [];

    if (isset($_GET['team'])) {
        $where_clauses[] = 's.team = ?';
        $params[] = $_GET['team'];
    }
    if (isset($_GET['shot_type'])) {
        $where_clauses[] = 's.shot_type = ?';
        $params[] = $_GET['shot_type'];
    }
    if (isset($_GET['result'])) {
        $where_clauses[] = 's.result = ?';
        $params[] = $_GET['result'];
    }

    $where_sql = count($where_clauses) > 0 ? 'WHERE ' . implode(' AND ', $where_clauses) : '';

    $query = "SELECT s.*, e.end_number, e.game_id
               FROM shots s
               JOIN ends e ON s.end_id = e.id
               $where_sql
               ORDER BY e.game_id, e.end_number, s.shot_number
               LIMIT $limit";

    $stmt = $db->prepare($query);
    foreach ($params as $i => $param) {
        $stmt->bindValue($i + 1, $param);
    }

    $result = $stmt->execute();
    $shots = [];
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
        $shots[] = $row;
    }

    $db->close();
    echo json_encode($shots, JSON_PRETTY_PRINT);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()], JSON_PRETTY_PRINT);
}