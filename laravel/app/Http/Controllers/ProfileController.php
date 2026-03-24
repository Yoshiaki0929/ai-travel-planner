<?php

namespace App\Http\Controllers;

use App\Services\SupabaseService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class ProfileController extends Controller
{
    private const UUID_RE = '/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i';

    public function __construct(private SupabaseService $supabase) {}

    // ── GET /api/me ─────────────────────────────────────────
    public function me(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');
        return response()->json($user);
    }

    // ── GET /api/profile (own profile) ──────────────────────
    public function myProfile(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');
        $rows = $this->supabase->get('profiles', "user_id=eq.{$user['id']}&limit=1");
        return response()->json($rows[0] ?? (object)[]);
    }

    // ── GET /api/profile/{userId} (public) ──────────────────
    public function show(string $userId): JsonResponse
    {
        if (!preg_match(self::UUID_RE, $userId)) {
            return response()->json(['error' => 'Invalid user_id'], 400);
        }
        $rows = $this->supabase->get('profiles', "user_id=eq.{$userId}&limit=1");
        return response()->json($rows[0] ?? (object)[]);
    }

    // ── PUT /api/profile ─────────────────────────────────────
    public function update(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');
        $body = $request->json()->all();

        // Validate and sanitize — no arbitrary HTML/scripts stored
        $data = ['user_id' => $user['id']];

        if (isset($body['display_name'])) {
            $val = mb_substr(trim(strip_tags($body['display_name'])), 0, 100);
            if ($val !== '') $data['display_name'] = $val;
        }
        if (isset($body['bio'])) {
            $data['bio'] = mb_substr(trim(strip_tags($body['bio'])), 0, 500);
        }
        if (isset($body['home_city'])) {
            $data['home_city'] = mb_substr(trim(strip_tags($body['home_city'])), 0, 100);
        }

        if (count($data) === 1) {
            return response()->json(['error' => 'Nothing to update'], 400);
        }

        $row = $this->supabase->upsert('profiles', $data);

        if (!$row) {
            return response()->json(['error' => 'Failed to save profile'], 500);
        }
        return response()->json(['ok' => true]);
    }
}
