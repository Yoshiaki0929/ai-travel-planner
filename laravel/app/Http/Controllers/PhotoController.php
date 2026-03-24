<?php

namespace App\Http\Controllers;

use App\Http\Middleware\SupabaseAuth;
use App\Services\SupabaseService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class PhotoController extends Controller
{
    private const ALLOWED_MIME   = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    private const MAX_BYTES      = 5 * 1024 * 1024; // 5 MB
    private const UUID_RE        = '/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i';

    // Magic bytes for each allowed image type
    private const MAGIC_BYTES = [
        'image/jpeg' => ["\xFF\xD8\xFF"],
        'image/png'  => ["\x89PNG\r\n\x1a\n"],
        'image/gif'  => ["GIF87a", "GIF89a"],
        'image/webp' => ["RIFF"],   // checked together with offset 8
    ];

    public function __construct(private SupabaseService $supabase) {}

    // ── GET /api/photos/timeline ─────────────────────────────
    public function timeline(Request $request): JsonResponse
    {
        $user     = SupabaseAuth::resolveUser($request);
        $callerId = $user['id'] ?? null;

        $limit  = min((int) $request->query('limit', 20), 50);
        $offset = max(0, (int) $request->query('offset', 0));
        $userId = (string) $request->query('user_id', '');

        if ($userId && !preg_match(self::UUID_RE, $userId)) {
            return response()->json(['error' => 'Invalid user_id'], 400);
        }

        $userFilter   = $userId ? "&user_id=eq.{$userId}" : '';
        $isOwnProfile = $userId && $callerId && $userId === $callerId;
        $visFilter    = $isOwnProfile ? '' : '&visibility=eq.public';

        $rows = $this->supabase->get(
            'photos',
            "order=created_at.desc&limit={$limit}&offset={$offset}{$userFilter}{$visFilter}"
        );
        return response()->json($rows);
    }

    // ── POST /api/photos ─────────────────────────────────────
    public function store(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');

        $destination = mb_substr(trim(strip_tags($request->input('destination', ''))), 0, 200);
        $caption     = mb_substr(trim($request->input('caption', '')), 0, 300);
        $visibility  = in_array($request->input('visibility'), ['public', 'private'])
                       ? $request->input('visibility')
                       : 'public';

        if (!$caption && !$request->hasFile('file')) {
            return response()->json(['error' => 'Message or photo is required'], 400);
        }

        $imageUrl = '';
        if ($request->hasFile('file')) {
            $file = $request->file('file');

            // 1. Check declared MIME type
            if (!in_array($file->getMimeType(), self::ALLOWED_MIME)) {
                return response()->json(['error' => 'Only JPEG/PNG/WebP/GIF images are allowed'], 400);
            }

            // 2. Check actual file size
            if ($file->getSize() > self::MAX_BYTES) {
                return response()->json(['error' => 'File size must be under 5 MB'], 400);
            }

            // 3. Verify magic bytes (prevent MIME-type spoofing)
            $handle  = fopen($file->getRealPath(), 'rb');
            $header  = fread($handle, 16);
            fclose($handle);
            if (!$this->validateMagicBytes($file->getMimeType(), $header)) {
                return response()->json(['error' => 'File content does not match declared type'], 400);
            }

            // 4. Use a safe UUID filename (ignore client filename entirely)
            $extMap   = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp', 'image/gif' => 'gif'];
            $ext      = $extMap[$file->getMimeType()] ?? 'jpg';
            $filePath = $user['id'] . '/' . \Illuminate\Support\Str::uuid() . '.' . $ext;
            $content  = file_get_contents($file->getRealPath());

            if (!$this->supabase->uploadFile('travel-photos', $filePath, $content, $file->getMimeType())) {
                return response()->json(['error' => 'Image upload failed'], 500);
            }
            $imageUrl = $this->supabase->publicUrl('travel-photos', $filePath);
        }

        $row = $this->supabase->insert('photos', [
            'user_id'     => $user['id'],
            'user_name'   => mb_substr($user['name'] ?? '', 0, 100),
            'user_avatar' => $user['avatar'] ?? '',
            'destination' => $destination,
            'caption'     => $caption,
            'image_url'   => $imageUrl,
            'visibility'  => $visibility,
        ]);

        if (!$row) {
            return response()->json(['error' => 'Failed to save post'], 500);
        }
        return response()->json(['ok' => true, 'photo' => $row]);
    }

    // ── PATCH /api/photos/{photoId} ──────────────────────────
    public function update(Request $request, string $photoId): JsonResponse
    {
        if (!preg_match(self::UUID_RE, $photoId)) {
            return response()->json(['error' => 'Invalid photo id'], 400);
        }
        $user = $request->attributes->get('auth_user');
        $body = $request->json()->all();

        $data = [];
        if (!empty($body['destination'])) {
            $data['destination'] = mb_substr(trim(strip_tags($body['destination'])), 0, 200);
        }
        if (isset($body['caption'])) {
            $data['caption'] = mb_substr(trim($body['caption']), 0, 300);
        }

        if (!$data) {
            return response()->json(['error' => 'Nothing to update'], 400);
        }

        $rows = $this->supabase->patch('photos', "id=eq.{$photoId}&user_id=eq.{$user['id']}", $data);

        if ($rows === null) {
            return response()->json(['error' => 'Database error'], 500);
        }
        if (empty($rows)) {
            return response()->json(['error' => 'Photo not found'], 404);
        }
        return response()->json(['ok' => true, 'photo' => $rows[0]]);
    }

    // ── PATCH /api/photos/{photoId}/visibility ───────────────
    public function updateVisibility(Request $request, string $photoId): JsonResponse
    {
        if (!preg_match(self::UUID_RE, $photoId)) {
            return response()->json(['error' => 'Invalid photo id'], 400);
        }
        $user       = $request->attributes->get('auth_user');
        $visibility = $request->json('visibility');

        if (!in_array($visibility, ['public', 'private'])) {
            return response()->json(['error' => 'Invalid visibility'], 400);
        }

        $rows = $this->supabase->patch('photos', "id=eq.{$photoId}&user_id=eq.{$user['id']}", ['visibility' => $visibility]);

        if ($rows === null) {
            return response()->json(['error' => 'Update failed'], 500);
        }
        if (empty($rows)) {
            return response()->json(['error' => 'Photo not found'], 404);
        }
        return response()->json(['ok' => true, 'visibility' => $visibility]);
    }

    // ── DELETE /api/photos/{photoId} ─────────────────────────
    public function destroy(Request $request, string $photoId): JsonResponse
    {
        if (!preg_match(self::UUID_RE, $photoId)) {
            return response()->json(['error' => 'Invalid photo id'], 400);
        }
        $user = $request->attributes->get('auth_user');

        $rows = $this->supabase->get('photos', "id=eq.{$photoId}&user_id=eq.{$user['id']}&limit=1");
        if (empty($rows)) {
            return response()->json(['error' => 'Photo not found'], 404);
        }

        // Delete from storage only if the URL belongs to our bucket
        $imageUrl = $rows[0]['image_url'] ?? '';
        $marker   = '/storage/v1/object/public/travel-photos/';
        if (str_contains($imageUrl, $marker)) {
            $rawPath  = substr($imageUrl, strpos($imageUrl, $marker) + strlen($marker));
            // Prevent path traversal — allow only UUID/UUID.ext
            $filePath = preg_replace('/[^a-zA-Z0-9\-_\/\.]/', '', $rawPath);
            if ($filePath) {
                $this->supabase->deleteFile('travel-photos', $filePath);
            }
        }

        $ok = $this->supabase->delete('photos', "id=eq.{$photoId}&user_id=eq.{$user['id']}");
        return response()->json(['ok' => $ok]);
    }

    // ── GET /api/photos/my-likes ─────────────────────────────
    public function myLikes(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');
        $rows = $this->supabase->get('photo_likes', "user_id=eq.{$user['id']}&select=photo_id");
        return response()->json(array_column($rows, 'photo_id'));
    }

    // ── POST /api/photos/{photoId}/like ──────────────────────
    public function toggleLike(Request $request, string $photoId): JsonResponse
    {
        if (!preg_match(self::UUID_RE, $photoId)) {
            return response()->json(['error' => 'Invalid photo id'], 400);
        }
        $user = $request->attributes->get('auth_user');

        $existing = $this->supabase->get('photo_likes', "photo_id=eq.{$photoId}&user_id=eq.{$user['id']}&limit=1");

        if ($existing) {
            $this->supabase->delete('photo_likes', "photo_id=eq.{$photoId}&user_id=eq.{$user['id']}");
            $liked = false;
        } else {
            $this->supabase->upsert('photo_likes', ['photo_id' => $photoId, 'user_id' => $user['id']]);
            $liked = true;
        }

        $count = $this->supabase->count('photo_likes', "photo_id=eq.{$photoId}");
        $this->supabase->patch('photos', "id=eq.{$photoId}", ['like_count' => $count]);

        return response()->json(['liked' => $liked, 'count' => $count]);
    }

    // ── Private helpers ──────────────────────────────────────

    private function validateMagicBytes(string $mime, string $header): bool
    {
        return match ($mime) {
            'image/jpeg' => str_starts_with($header, "\xFF\xD8\xFF"),
            'image/png'  => str_starts_with($header, "\x89PNG\r\n\x1a\n"),
            'image/gif'  => str_starts_with($header, "GIF87a") || str_starts_with($header, "GIF89a"),
            'image/webp' => str_starts_with($header, "RIFF") && substr($header, 8, 4) === "WEBP",
            default      => false,
        };
    }
}
