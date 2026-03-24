<?php

namespace App\Providers;

use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    public function boot(): void
    {
        $this->configureRateLimiting();
    }

    private function configureRateLimiting(): void
    {
        // General API reads — 60 req/min per IP
        RateLimiter::for('api-general', function (Request $request) {
            return Limit::perMinute(60)->by($request->ip());
        });

        // AI plan generation (calls Groq API, expensive) — 10 req/min per IP
        RateLimiter::for('api-plan', function (Request $request) {
            return Limit::perMinute(10)->by($request->ip());
        });

        // Photo uploads — 20 req/min per IP
        RateLimiter::for('api-upload', function (Request $request) {
            return Limit::perMinute(20)->by($request->ip());
        });

        // Write operations (save, delete, update, friends) — 30 req/min per IP
        RateLimiter::for('api-write', function (Request $request) {
            return Limit::perMinute(30)->by($request->ip());
        });
    }
}
