<?php

// Suppress PHP 8.5 deprecation notices from framework internals (PDO constants)
error_reporting(E_ALL & ~E_DEPRECATED & ~E_USER_DEPRECATED);

// Remove PHP version disclosure header
header_remove('X-Powered-By');

use Illuminate\Contracts\Http\Kernel;
use Illuminate\Http\Request;

define('LARAVEL_START', microtime(true));

// Maintenance mode check
if (file_exists($maintenance = __DIR__.'/../storage/framework/maintenance.php')) {
    require $maintenance;
}

require __DIR__.'/../vendor/autoload.php';

$app = require_once __DIR__.'/../bootstrap/app.php';

$kernel = $app->make(Kernel::class);

$response = $kernel->handle(
    $request = Request::capture()
)->send();

$kernel->terminate($request, $response);
