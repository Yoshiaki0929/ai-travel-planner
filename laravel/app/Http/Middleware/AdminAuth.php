<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class AdminAuth
{
    public function handle(Request $request, Closure $next): Response
    {
        $user = SupabaseAuth::resolveUser($request);

        if (!$user) {
            return response()->json(['error' => 'Not authenticated'], 401);
        }

        $adminEmails = array_filter(
            array_map('trim', explode(',', env('ADMIN_EMAILS', '')))
        );

        if (empty($adminEmails) || !in_array($user['email'], $adminEmails, true)) {
            return response()->json(['error' => 'Forbidden'], 403);
        }

        $request->attributes->set('auth_user', $user);

        return $next($request);
    }
}
