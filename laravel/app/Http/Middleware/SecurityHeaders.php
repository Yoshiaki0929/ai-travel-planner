<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/**
 * Add security headers to every response and strip information-disclosure headers.
 */
class SecurityHeaders
{
    public function handle(Request $request, Closure $next): Response
    {
        $response = $next($request);

        // ── Information disclosure ──────────────────────────
        $response->headers->remove('X-Powered-By');
        $response->headers->remove('Server');

        // ── Clickjacking protection ─────────────────────────
        $response->headers->set('X-Frame-Options', 'DENY');

        // ── MIME-sniffing protection ─────────────────────────
        $response->headers->set('X-Content-Type-Options', 'nosniff');

        // ── XSS auditor (legacy browsers) ────────────────────
        $response->headers->set('X-XSS-Protection', '1; mode=block');

        // ── Referrer ─────────────────────────────────────────
        $response->headers->set('Referrer-Policy', 'strict-origin-when-cross-origin');

        // ── Permissions ──────────────────────────────────────
        $response->headers->set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');

        // ── HSTS (enable when HTTPS is deployed) ─────────────
        if ($request->secure()) {
            $response->headers->set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
        }

        // ── Content-Security-Policy (HTML responses only) ────
        if (!$request->is('api/*')) {
            $csp = implode('; ', [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data: blob: https:",
                "media-src 'self' https:",
                "connect-src 'self' https://*.supabase.co https://api.groq.com https://nominatim.openstreetmap.org",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]);
            $response->headers->set('Content-Security-Policy', $csp);
        }

        return $response;
    }
}
