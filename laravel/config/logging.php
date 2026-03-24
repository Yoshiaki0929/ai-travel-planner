<?php

return [
    'default' => env('LOG_CHANNEL', 'stack'),
    'channels' => [
        'stack' => [
            'driver'   => 'stack',
            'channels' => ['single'],
        ],
        'single' => [
            'driver' => 'single',
            'path'   => storage_path('logs/laravel.log'),
            'level'  => env('LOG_LEVEL', 'debug'),
        ],
        'stderr' => [
            'driver'    => 'monolog',
            'handler'   => Monolog\Handler\StreamHandler::class,
            'formatter' => Monolog\Formatter\LineFormatter::class,
            'with'      => ['stream' => 'php://stderr'],
        ],
    ],
];
