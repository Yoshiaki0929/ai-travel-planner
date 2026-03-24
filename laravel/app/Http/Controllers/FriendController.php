<?php

namespace App\Http\Controllers;

use App\Services\SupabaseService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class FriendController extends Controller
{
    private const UUID_RE = '/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i';

    public function __construct(private SupabaseService $supabase) {}

    // ── GET /api/friends ─────────────────────────────────────
    public function index(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');
        $rows = $this->getAllFriendships($user['id']);

        $friends = [];
        foreach ($rows as $r) {
            if (($r['status'] ?? '') !== 'accepted') continue;
            if ($r['requester_id'] === $user['id']) {
                $friends[] = [
                    'friendship_id' => $r['id'],
                    'user_id'       => $r['addressee_id'],
                    'name'          => $r['addressee_name'],
                    'avatar'        => $r['addressee_avatar'],
                ];
            } else {
                $friends[] = [
                    'friendship_id' => $r['id'],
                    'user_id'       => $r['requester_id'],
                    'name'          => $r['requester_name'],
                    'avatar'        => $r['requester_avatar'],
                ];
            }
        }
        return response()->json($friends);
    }

    // ── GET /api/friends/requests ────────────────────────────
    public function requests(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');
        $rows = $this->supabase->get('friendships', "addressee_id=eq.{$user['id']}&status=eq.pending");

        $result = array_map(fn($r) => [
            'friendship_id' => $r['id'],
            'user_id'       => $r['requester_id'],
            'name'          => $r['requester_name'],
            'avatar'        => $r['requester_avatar'],
            'created_at'    => $r['created_at'],
        ], $rows);

        return response()->json($result);
    }

    // ── GET /api/friends/statuses ────────────────────────────
    public function statuses(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');
        $rows = $this->getAllFriendships($user['id']);

        $result = [];
        foreach ($rows as $r) {
            $otherId = $r['requester_id'] === $user['id']
                ? $r['addressee_id']
                : $r['requester_id'];
            $result[$otherId] = [
                'friendship_id' => $r['id'],
                'status'        => $r['status'],
                'is_requester'  => $r['requester_id'] === $user['id'],
            ];
        }
        return response()->json($result);
    }

    // ── POST /api/friends/request/{addresseeId} ──────────────
    public function sendRequest(Request $request, string $addresseeId): JsonResponse
    {
        if (!preg_match(self::UUID_RE, $addresseeId)) {
            return response()->json(['error' => 'Invalid user id'], 400);
        }

        $user = $request->attributes->get('auth_user');

        if ($user['id'] === $addresseeId) {
            return response()->json(['error' => 'Cannot add yourself'], 400);
        }

        // Check for existing friendship/request to prevent duplicates and spam
        $existing = $this->supabase->get(
            'friendships',
            "or=(and(requester_id.eq.{$user['id']},addressee_id.eq.{$addresseeId}),and(requester_id.eq.{$addresseeId},addressee_id.eq.{$user['id']}))"
        );
        if (!empty($existing)) {
            return response()->json(['error' => 'Friendship already exists or is pending'], 409);
        }

        $body = $request->json()->all();

        // Sanitize caller-supplied name/avatar — do NOT trust them to be accurate
        // They are cosmetic hints only; Supabase RLS / app logic uses IDs
        $addresseeName   = mb_substr(trim(strip_tags($body['addressee_name']   ?? '')), 0, 100);
        $addresseeAvatar = filter_var($body['addressee_avatar'] ?? '', FILTER_VALIDATE_URL)
                           ? $body['addressee_avatar']
                           : '';

        $row = $this->supabase->insert('friendships', [
            'requester_id'    => $user['id'],
            'requester_name'  => mb_substr($user['name'] ?? '', 0, 100),
            'requester_avatar'=> $user['avatar'] ?? '',
            'addressee_id'    => $addresseeId,
            'addressee_name'  => $addresseeName,
            'addressee_avatar'=> $addresseeAvatar,
            'status'          => 'pending',
        ]);

        if (!$row) {
            return response()->json(['error' => 'Failed to send request'], 500);
        }
        return response()->json(['ok' => true, 'friendship' => $row]);
    }

    // ── PUT /api/friends/{friendshipId}/accept ───────────────
    public function accept(Request $request, string $friendshipId): JsonResponse
    {
        if (!preg_match(self::UUID_RE, $friendshipId)) {
            return response()->json(['error' => 'Invalid friendship id'], 400);
        }
        $user = $request->attributes->get('auth_user');
        $rows = $this->supabase->patch(
            'friendships',
            "id=eq.{$friendshipId}&addressee_id=eq.{$user['id']}&status=eq.pending",
            ['status' => 'accepted']
        );
        return response()->json(['ok' => !empty($rows)]);
    }

    // ── DELETE /api/friends/{friendshipId} ───────────────────
    public function remove(Request $request, string $friendshipId): JsonResponse
    {
        if (!preg_match(self::UUID_RE, $friendshipId)) {
            return response()->json(['error' => 'Invalid friendship id'], 400);
        }
        $user = $request->attributes->get('auth_user');
        $ok   = $this->supabase->delete(
            'friendships',
            "id=eq.{$friendshipId}&or=(requester_id.eq.{$user['id']},addressee_id.eq.{$user['id']})"
        );
        return response()->json(['ok' => $ok]);
    }

    // ── Helper ────────────────────────────────────────────────
    private function getAllFriendships(string $userId): array
    {
        return $this->supabase->get(
            'friendships',
            "or=(requester_id.eq.{$userId},addressee_id.eq.{$userId})"
        );
    }
}
