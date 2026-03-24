<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Symfony\Component\HttpFoundation\Response;

class SupabaseAuth
{
    public function handle(Request $request, Closure $next): Response
    {
        $user = $this->resolveUser($request);

        if (!$user) {
            return response()->json(['error' => 'Not authenticated'], 401);
        }

        $request->attributes->set('auth_user', $user);

        return $next($request);
    }

    /**
     * Validate the Bearer token against Supabase /auth/v1/user.
     * Returns the normalized user array or null on failure.
     */
    public static function resolveUser(Request $request): ?array
    {
        $header = $request->header('Authorization', '');
        if (!str_starts_with($header, 'Bearer ')) {
            return null;
        }

        $token      = substr($header, 7);
        $supabaseUrl = env('SUPABASE_URL', '');
        $anonKey    = env('SUPABASE_ANON_KEY', '');

        if (!$supabaseUrl || !$anonKey) {
            return null;
        }

        try {
            $response = Http::timeout(10)
                ->withHeaders([
                    'Authorization' => "Bearer {$token}",
                    'apikey'        => $anonKey,
                ])
                ->get("{$supabaseUrl}/auth/v1/user");

            if ($response->failed()) {
                return null;
            }

            $data = $response->json();
            $meta = $data['user_metadata'] ?? [];
            $email = $data['email'] ?? '';

            return [
                'id'     => $data['id'] ?? null,
                'email'  => $email,
                'name'   => $meta['full_name'] ?? explode('@', $email)[0],
                'avatar' => $meta['avatar_url'] ?? null,
            ];
        } catch (\Throwable) {
            return null;
        }
    }
}
