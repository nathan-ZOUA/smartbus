<?php
declare(strict_types=1);

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
if (!str_starts_with($path, '/api/')) {
    return false;
}

$query = $_SERVER['QUERY_STRING'] ?? '';
$upstream = 'http://127.0.0.1:8000' . $path . ($query !== '' ? '?' . $query : '');
$requestHeaders = function_exists('getallheaders') ? getallheaders() : [];
$forwardHeaders = [];
foreach ($requestHeaders as $name => $value) {
    if (in_array(strtolower($name), ['host', 'connection', 'content-length', 'transfer-encoding'], true)) {
        continue;
    }
    $forwardHeaders[] = $name . ': ' . $value;
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$context = stream_context_create([
    'http' => [
        'method' => $method,
        'header' => implode("\r\n", $forwardHeaders),
        'content' => file_get_contents('php://input') ?: '',
        'ignore_errors' => true,
        'follow_location' => 0,
        'timeout' => 15,
    ],
]);

$body = @file_get_contents($upstream, false, $context);
if ($body === false) {
    http_response_code(502);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['detail' => 'L’API SmartBus est temporairement indisponible.']);
    exit;
}

$responseHeaders = $http_response_header ?? [];
foreach ($responseHeaders as $responseHeader) {
    if (preg_match('/^HTTP\/\S+\s+(\d{3})/', $responseHeader, $matches)) {
        http_response_code((int) $matches[1]);
        continue;
    }
    if (stripos($responseHeader, 'Content-Type:') === 0) {
        header($responseHeader);
    }
}
echo $body;
