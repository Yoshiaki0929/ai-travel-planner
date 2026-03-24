<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;

/**
 * Thin wrapper around Supabase PostgREST + Storage APIs.
 */
class SupabaseService
{
    private string $url;
    private string $serviceKey;

    public function __construct()
    {
        $this->url        = env('SUPABASE_URL', '');
        $this->serviceKey = env('SUPABASE_SERVICE_ROLE_KEY', '');
    }

    /** GET /rest/v1/{table}?{query} */
    public function get(string $table, string $query = ''): array
    {
        $sep = $query ? '?' : '';
        $response = Http::timeout(15)
            ->withHeaders($this->headers())
            ->get("{$this->url}/rest/v1/{$table}{$sep}{$query}");

        return $response->successful() ? $response->json() : [];
    }

    /** POST /rest/v1/{table} — returns first row */
    public function insert(string $table, array $data): ?array
    {
        $response = Http::timeout(15)
            ->withHeaders([...$this->headers(), 'Prefer' => 'return=representation'])
            ->post("{$this->url}/rest/v1/{$table}", $data);

        if ($response->failed()) return null;
        $rows = $response->json();
        return is_array($rows) && count($rows) > 0 ? $rows[0] : null;
    }

    /** POST with resolution=merge-duplicates (upsert) */
    public function upsert(string $table, array $data): ?array
    {
        $response = Http::timeout(15)
            ->withHeaders([
                ...$this->headers(),
                'Prefer' => 'resolution=merge-duplicates,return=representation',
            ])
            ->post("{$this->url}/rest/v1/{$table}", $data);

        if ($response->failed()) return null;
        $rows = $response->json();
        return is_array($rows) && count($rows) > 0 ? $rows[0] : null;
    }

    /** PATCH /rest/v1/{table}?{query} — returns updated rows */
    public function patch(string $table, string $query, array $data): array
    {
        $response = Http::timeout(15)
            ->withHeaders([...$this->headers(), 'Prefer' => 'return=representation'])
            ->patch("{$this->url}/rest/v1/{$table}?{$query}", $data);

        return $response->successful() ? ($response->json() ?? []) : [];
    }

    /** DELETE /rest/v1/{table}?{query} */
    public function delete(string $table, string $query): bool
    {
        $response = Http::timeout(15)
            ->withHeaders($this->headers())
            ->delete("{$this->url}/rest/v1/{$table}?{$query}");

        return $response->status() === 204;
    }

    /** GET row count via Prefer: count=exact */
    public function count(string $table, string $query): int
    {
        $response = Http::timeout(10)
            ->withHeaders([
                ...$this->headers(),
                'Prefer'     => 'count=exact',
                'Range-Unit' => 'items',
                'Range'      => '0-0',
            ])
            ->get("{$this->url}/rest/v1/{$table}?{$query}");

        $cr = $response->header('content-range', '0/0');
        $parts = explode('/', $cr);
        return (int) end($parts);
    }

    /** Upload a file to Supabase Storage */
    public function uploadFile(string $bucket, string $filePath, string $content, string $mime): bool
    {
        $response = Http::timeout(30)
            ->withHeaders([
                'Authorization' => "Bearer {$this->serviceKey}",
                'Content-Type'  => $mime,
            ])
            ->withBody($content, $mime)
            ->post("{$this->url}/storage/v1/object/{$bucket}/{$filePath}");

        return in_array($response->status(), [200, 201]);
    }

    /** Delete a file from Supabase Storage */
    public function deleteFile(string $bucket, string $filePath): void
    {
        Http::timeout(10)
            ->withHeaders(['Authorization' => "Bearer {$this->serviceKey}"])
            ->delete("{$this->url}/storage/v1/object/{$bucket}/{$filePath}");
    }

    public function publicUrl(string $bucket, string $filePath): string
    {
        return "{$this->url}/storage/v1/object/public/{$bucket}/{$filePath}";
    }

    private function headers(): array
    {
        return [
            'apikey'        => $this->serviceKey,
            'Authorization' => "Bearer {$this->serviceKey}",
            'Content-Type'  => 'application/json',
        ];
    }
}
