<?php

namespace App\Http\Controllers;

use App\Services\SupabaseService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AdminController extends Controller
{
    public function __construct(private SupabaseService $supabase) {}

    // GET /api/admin/overview — KPI summary counts
    public function overview(): JsonResponse
    {
        $totalUsers      = $this->supabase->count('profiles', 'select=user_id');
        $totalPlans      = $this->supabase->count('saved_plans', 'select=id');
        $totalPhotos     = $this->supabase->count('photos', 'select=id');
        $totalMessages   = $this->supabase->count('messages', 'select=id');
        $totalFriendships = $this->supabase->count('friendships', 'status=eq.accepted&select=id');

        // New users in last 7 days
        $since7d = now()->subDays(7)->toIso8601String();
        $newUsersWeek = $this->supabase->count('profiles', "created_at=gte.{$since7d}&select=user_id");

        // New users in last 30 days
        $since30d = now()->subDays(30)->toIso8601String();
        $newUsersMonth = $this->supabase->count('profiles', "created_at=gte.{$since30d}&select=user_id");

        return response()->json([
            'total_users'        => $totalUsers,
            'total_plans'        => $totalPlans,
            'total_photos'       => $totalPhotos,
            'total_messages'     => $totalMessages,
            'total_friendships'  => $totalFriendships,
            'new_users_week'     => $newUsersWeek,
            'new_users_month'    => $newUsersMonth,
        ]);
    }

    // GET /api/admin/stats/daily — new user signups per day for last 30 days
    public function dailyStats(): JsonResponse
    {
        $since = now()->subDays(30)->toIso8601String();
        $rows = $this->supabase->get(
            'profiles',
            "created_at=gte.{$since}&select=created_at&order=created_at.asc"
        );

        $byDay = [];
        foreach ($rows as $row) {
            if (!empty($row['created_at'])) {
                $day = substr($row['created_at'], 0, 10);
                $byDay[$day] = ($byDay[$day] ?? 0) + 1;
            }
        }

        $result = [];
        for ($i = 29; $i >= 0; $i--) {
            $day = now()->subDays($i)->format('Y-m-d');
            $result[] = ['date' => $day, 'new_users' => $byDay[$day] ?? 0];
        }

        return response()->json($result);
    }

    // GET /api/admin/stats/content — content created per day for last 30 days
    public function contentStats(): JsonResponse
    {
        $since = now()->subDays(30)->toIso8601String();

        $plans = $this->supabase->get(
            'saved_plans',
            "created_at=gte.{$since}&select=created_at&order=created_at.asc"
        );
        $photos = $this->supabase->get(
            'photos',
            "created_at=gte.{$since}&select=created_at&order=created_at.asc"
        );
        $messages = $this->supabase->get(
            'messages',
            "created_at=gte.{$since}&select=created_at&order=created_at.asc"
        );

        $plansByDay = $this->groupByDay($plans);
        $photosByDay = $this->groupByDay($photos);
        $messagesByDay = $this->groupByDay($messages);

        $result = [];
        for ($i = 29; $i >= 0; $i--) {
            $day = now()->subDays($i)->format('Y-m-d');
            $result[] = [
                'date'     => $day,
                'plans'    => $plansByDay[$day] ?? 0,
                'photos'   => $photosByDay[$day] ?? 0,
                'messages' => $messagesByDay[$day] ?? 0,
            ];
        }

        return response()->json($result);
    }

    // GET /api/admin/users — recent 100 users
    public function users(): JsonResponse
    {
        $rows = $this->supabase->get(
            'profiles',
            'select=user_id,display_name,home_city,created_at&order=created_at.desc&limit=100'
        );
        return response()->json($rows);
    }

    private function groupByDay(array $rows): array
    {
        $byDay = [];
        foreach ($rows as $row) {
            if (!empty($row['created_at'])) {
                $day = substr($row['created_at'], 0, 10);
                $byDay[$day] = ($byDay[$day] ?? 0) + 1;
            }
        }
        return $byDay;
    }
}
