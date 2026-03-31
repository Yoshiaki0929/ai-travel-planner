<?php

use Illuminate\Support\Facades\Route;

// Admin dashboard
Route::get('/admin', function () {
    return response()->file(public_path('admin.html'));
});

// Serve the SPA for all non-API routes
Route::get('/{any?}', function () {
    return response()->file(public_path('index.html'));
})->where('any', '^(?!api|admin).*');
