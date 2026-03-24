<?php

return [
    // Only allow requests from the same origin (SPA is served from Laravel itself)
    'paths'                    => ['api/*'],
    'allowed_methods'          => ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    'allowed_origins'          => [env('APP_URL', 'http://localhost:8000')],
    'allowed_origins_patterns' => [],
    'allowed_headers'          => ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept'],
    'exposed_headers'          => [],
    'max_age'                  => 86400,
    'supports_credentials'     => false,
];
