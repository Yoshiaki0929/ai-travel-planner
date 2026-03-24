<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ConfigController;
use App\Http\Controllers\PlanController;
use App\Http\Controllers\PhotoController;
use App\Http\Controllers\ProfileController;
use App\Http\Controllers\FriendController;
use App\Http\Middleware\SupabaseAuth;

// ── Public ────────────────────────────────────────────────
Route::get('/config',  [ConfigController::class, 'show'])->middleware('throttle:api-general');
Route::get('/health',  fn() => response()->json(['status' => 'ok']));

// AI plan generation — stricter rate limit (calls Groq API)
Route::post('/plan',        [PlanController::class, 'create'])->middleware('throttle:api-plan');
Route::post('/plan/stream', [PlanController::class, 'stream'])->middleware('throttle:api-plan');

Route::get('/profile/{userId}', [ProfileController::class, 'show'])->middleware('throttle:api-general');

Route::get('/photos/timeline', [PhotoController::class, 'timeline'])->middleware('throttle:api-general');

// ── Authenticated ──────────────────────────────────────────
Route::middleware([SupabaseAuth::class, 'throttle:api-general'])->group(function () {
    Route::get('/me', [ProfileController::class, 'me']);

    // Profile
    Route::get('/profile',  [ProfileController::class, 'myProfile']);
    Route::put('/profile',  [ProfileController::class, 'update'])->middleware('throttle:api-write');

    // Plans
    Route::get('/plans',         [PlanController::class, 'index']);
    Route::post('/plans/save',   [PlanController::class, 'save'])->middleware('throttle:api-write');
    Route::delete('/plans/{id}', [PlanController::class, 'destroy'])->middleware('throttle:api-write');

    // Photos
    Route::post('/photos',                       [PhotoController::class, 'store'])->middleware('throttle:api-upload');
    Route::patch('/photos/{photoId}',             [PhotoController::class, 'update'])->middleware('throttle:api-write');
    Route::patch('/photos/{photoId}/visibility',  [PhotoController::class, 'updateVisibility'])->middleware('throttle:api-write');
    Route::delete('/photos/{photoId}',            [PhotoController::class, 'destroy'])->middleware('throttle:api-write');

    // Likes
    Route::get('/photos/my-likes',         [PhotoController::class, 'myLikes']);
    Route::post('/photos/{photoId}/like',  [PhotoController::class, 'toggleLike'])->middleware('throttle:api-write');

    // Friends
    Route::get('/friends',                          [FriendController::class, 'index']);
    Route::get('/friends/requests',                 [FriendController::class, 'requests']);
    Route::get('/friends/statuses',                 [FriendController::class, 'statuses']);
    Route::post('/friends/request/{addresseeId}',   [FriendController::class, 'sendRequest'])->middleware('throttle:api-write');
    Route::put('/friends/{friendshipId}/accept',    [FriendController::class, 'accept'])->middleware('throttle:api-write');
    Route::delete('/friends/{friendshipId}',        [FriendController::class, 'remove'])->middleware('throttle:api-write');
});
