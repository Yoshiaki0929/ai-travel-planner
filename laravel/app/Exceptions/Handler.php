<?php

namespace App\Exceptions;

use Illuminate\Foundation\Exceptions\Handler as ExceptionHandler;
use Illuminate\Http\Request;
use Symfony\Component\HttpKernel\Exception\HttpException;
use Throwable;

class Handler extends ExceptionHandler
{
    protected $dontReport = [];

    protected $dontFlash = ['current_password', 'password', 'password_confirmation'];

    public function register(): void
    {
        $this->renderable(function (Throwable $e, Request $request) {
            if ($request->is('api/*') || $request->expectsJson()) {
                $status  = $e instanceof HttpException ? $e->getStatusCode() : 500;
                $message = $e instanceof HttpException
                    ? ($e->getMessage() ?: $this->httpStatusMessage($status))
                    : (config('app.debug') ? $e->getMessage() : 'Server Error');

                return response()->json(['error' => $message], $status);
            }
        });
    }

    private function httpStatusMessage(int $status): string
    {
        return match ($status) {
            400 => 'Bad Request',
            401 => 'Unauthorized',
            403 => 'Forbidden',
            404 => 'Not Found',
            405 => 'Method Not Allowed',
            422 => 'Unprocessable Entity',
            429 => 'Too Many Requests',
            default => 'Server Error',
        };
    }
}
