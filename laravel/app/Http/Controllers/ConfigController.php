<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;

class ConfigController extends Controller
{
    public function show(): JsonResponse
    {
        return response()->json([
            'supabase_url'      => env('SUPABASE_URL', ''),
            'supabase_anon_key' => env('SUPABASE_ANON_KEY', ''),
        ]);
    }
}
