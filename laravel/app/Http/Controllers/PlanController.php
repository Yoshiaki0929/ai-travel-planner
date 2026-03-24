<?php

namespace App\Http\Controllers;

use App\Services\SupabaseService;
use App\Services\TravelPlanService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\StreamedResponse;

class PlanController extends Controller
{
    private const UUID_RE       = '/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i';
    private const MAX_PLAN_BYTES = 100_000; // 100 KB for stored plan content

    public function __construct(
        private SupabaseService $supabase,
        private TravelPlanService $planner,
    ) {}

    // ── POST /api/plan (non-streaming) ─────────────────────
    public function create(Request $request): JsonResponse
    {
        $data = $request->json()->all();

        $error = $this->validateRequest($data);
        if ($error) {
            return response()->json(['error' => $error], 400);
        }

        $message = $this->buildMessage($data);

        try {
            $result = $this->planner->orchestrate($message, $data['language'] ?? 'en');
            return response()->json(['plan' => $result]);
        } catch (\Throwable $e) {
            return response()->json(['error' => 'Failed to generate plan. Please try again.'], 500);
        }
    }

    // ── POST /api/plan/stream (SSE) ─────────────────────────
    public function stream(Request $request): StreamedResponse
    {
        $data = $request->json()->all();

        $error = $this->validateRequest($data);
        if ($error) {
            return new StreamedResponse(function () use ($error) {
                echo 'data: ' . json_encode(['type' => 'error', 'message' => $error]) . "\n\n";
                flush();
            }, 200, $this->sseHeaders());
        }

        $message  = $this->buildMessage($data);
        $language = $data['language'] ?? 'en';
        $planner  = $this->planner;

        return new StreamedResponse(function () use ($planner, $message, $language) {
            echo 'data: ' . json_encode(['type' => 'start',    'message' => '旅行プランを生成中...'],         JSON_UNESCAPED_UNICODE) . "\n\n";
            flush();
            echo 'data: ' . json_encode(['type' => 'progress', 'message' => '🔍 旅行先の情報を調査中...'], JSON_UNESCAPED_UNICODE) . "\n\n";
            flush();

            try {
                $result = $planner->orchestrate($message, $language);
                echo 'data: ' . json_encode(['type' => 'complete', 'plan' => $result], JSON_UNESCAPED_UNICODE) . "\n\n";
            } catch (\Throwable $e) {
                echo 'data: ' . json_encode(['type' => 'error', 'message' => 'Failed to generate plan. Please try again.']) . "\n\n";
            }
            flush();
        }, 200, $this->sseHeaders());
    }

    // ── GET /api/plans ──────────────────────────────────────
    public function index(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');
        $rows = $this->supabase->get('saved_plans', "user_id=eq.{$user['id']}&order=created_at.desc");
        return response()->json($rows);
    }

    // ── POST /api/plans/save ────────────────────────────────
    public function save(Request $request): JsonResponse
    {
        $user = $request->attributes->get('auth_user');
        $body = $request->json()->all();

        $destination = mb_substr(trim(strip_tags($body['destination'] ?? '')), 0, 200);
        $planContent = $body['plan_content'] ?? '';

        if (!$destination) {
            return response()->json(['error' => 'Destination is required'], 400);
        }
        if (strlen($planContent) > self::MAX_PLAN_BYTES) {
            return response()->json(['error' => 'Plan content too large'], 400);
        }

        $row = $this->supabase->insert('saved_plans', [
            'user_id'      => $user['id'],
            'destination'  => $destination,
            'duration_days'=> max(1, min(60, (int) ($body['duration_days'] ?? 1))),
            'budget_jpy'   => max(0, (int) ($body['budget_jpy'] ?? 0)),
            'plan_content' => $planContent,
        ]);

        if (!$row) {
            return response()->json(['error' => 'Failed to save plan'], 500);
        }
        return response()->json(['ok' => true, 'plan' => $row]);
    }

    // ── DELETE /api/plans/{id} ──────────────────────────────
    public function destroy(Request $request, string $id): JsonResponse
    {
        if (!preg_match(self::UUID_RE, $id)) {
            return response()->json(['error' => 'Invalid plan id'], 400);
        }
        $user = $request->attributes->get('auth_user');
        $ok   = $this->supabase->delete('saved_plans', "id=eq.{$id}&user_id=eq.{$user['id']}");
        return response()->json(['ok' => $ok]);
    }

    // ── Helpers ────────────────────────────────────────────
    private function validateRequest(array $d): ?string
    {
        $destination = trim(strip_tags($d['destination'] ?? ''));
        $days        = (int) ($d['duration_days'] ?? 0);
        $people      = (int) ($d['num_people'] ?? 1);
        $budget      = (int) ($d['budget_jpy'] ?? 0);

        if (!$destination) return 'Please enter a destination (e.g. Paris, Tokyo, Bali).';
        if (mb_strlen($destination) > 200) return 'Destination name is too long.';
        if ($days < 1 || $days > 60) return 'Trip duration must be between 1 and 60 days.';
        if ($people < 1 || $people > 20) return 'Number of travelers must be between 1 and 20.';
        $minBudget = 10000 * $people * $days;
        if ($budget < $minBudget) {
            return "A budget of ¥" . number_format($budget) . " is too low for {$people} person(s) over {$days} day(s). Please enter at least ¥" . number_format($minBudget) . ".";
        }
        return null;
    }

    private function buildMessage(array $d): string
    {
        $dest   = mb_substr(trim(strip_tags($d['destination'] ?? '')), 0, 200);
        $days   = max(1, min(60, (int) ($d['duration_days'] ?? 1)));
        $budget = number_format(max(0, (int) ($d['budget_jpy'] ?? 0)));
        $people = max(1, min(20, (int) ($d['num_people'] ?? 1)));
        $inter  = mb_substr(trim(strip_tags($d['interests'] ?? 'グルメ、観光')), 0, 200);
        $style  = mb_substr(trim(strip_tags($d['travel_style'] ?? 'バランス型')), 0, 100);
        $extra  = mb_substr(trim(strip_tags($d['additional_requests'] ?? '')), 0, 500) ?: 'なし';

        return <<<MSG
以下の条件で旅行プランを作成してください：

【旅行先】{$dest}
【旅行期間】{$days}日間
【予算】{$budget}円（{$people}人）
【人数】{$people}人
【興味・関心】{$inter}
【旅行スタイル】{$style}
【その他の希望】{$extra}

旅行先調査、予算計算、日程作成、体験提案の全ツールを使って、完全な旅行プランを作成してください。
MSG;
    }

    private function sseHeaders(): array
    {
        return [
            'Content-Type'      => 'text/event-stream',
            'Cache-Control'     => 'no-store',
            'X-Accel-Buffering' => 'no',
        ];
    }
}
