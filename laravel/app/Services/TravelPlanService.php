<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;

/**
 * Port of agents.py — orchestrates Groq LLM + tool functions to produce a travel plan.
 */
class TravelPlanService
{
    private const MODEL   = 'llama-3.3-70b-versatile';
    private const API_URL = 'https://api.groq.com/openai/v1/chat/completions';

    // ──────────────────────────────────────────────────────
    // Public entry point
    // ──────────────────────────────────────────────────────

    public function orchestrate(string $userRequest, string $language = 'en'): string
    {
        $params      = $this->extractParams($userRequest);
        $dest        = $params['destination'];
        $days        = $params['duration_days'];
        $budget      = $params['budget'];
        $people      = $params['num_people'];
        $interests   = $params['interests'];
        $travelStyle = $params['travel_style'];
        $dailyBudget = intdiv($budget, max($people, 1) * max($days, 1));

        $info       = $this->researchDestination($dest, "{$days}-day trip");
        $budgetData = $this->calculateBudget($dest, $days, $budget, $people);
        $itinerary  = $this->createItinerary($dest, $days, $travelStyle);
        $exps       = $this->findExperiences($dest, $interests, $dailyBudget);

        return $this->callLlm($userRequest, $dest, $info, $budgetData, $itinerary, $exps, $language);
    }

    // ──────────────────────────────────────────────────────
    // Tool: researchDestination
    // ──────────────────────────────────────────────────────

    private function researchDestination(string $destination, string $travelDates): string
    {
        $mockData = [
            'Bali'      => ['highlights' => ['Ubud Art Village','Tanah Lot Temple','Kuta Beach','Rice Terraces (Tegallalang)'], 'climate' => 'Tropical, avg 27°C. Dry season Apr–Oct is best.', 'tips' => ['Tipping culture exists','Do not drink tap water','Cover up at temples'], 'language' => 'Indonesian & English', 'currency' => 'IDR. 1 USD ≈ 15,500 IDR'],
            'バリ島'    => ['highlights' => ['Ubud Art Village','Tanah Lot Temple','Kuta Beach','Rice Terraces (Tegallalang)'], 'climate' => 'Tropical, avg 27°C. Dry season Apr–Oct is best.', 'tips' => ['Tipping culture exists','Do not drink tap water','Cover up at temples'], 'language' => 'Indonesian & English', 'currency' => 'IDR. 1 USD ≈ 15,500 IDR'],
            'Paris'     => ['highlights' => ['Eiffel Tower','Louvre Museum','Montmartre','Versailles Palace'], 'climate' => 'Temperate. Spring (Apr–May) and autumn (Sept–Oct) are ideal.', 'tips' => ['Watch for pickpockets','Restaurant reservations recommended','Many shops closed Sundays'], 'language' => 'French; English in tourist areas', 'currency' => 'EUR. 1 EUR ≈ 1.08 USD'],
            'パリ'      => ['highlights' => ['Eiffel Tower','Louvre Museum','Montmartre','Versailles Palace'], 'climate' => 'Temperate. Spring (Apr–May) and autumn (Sept–Oct) are ideal.', 'tips' => ['Watch for pickpockets','Restaurant reservations recommended','Many shops closed Sundays'], 'language' => 'French; English in tourist areas', 'currency' => 'EUR. 1 EUR ≈ 1.08 USD'],
            'New York'  => ['highlights' => ['Times Square','Central Park','Statue of Liberty','Metropolitan Museum'], 'climate' => 'Humid continental. Spring/fall are best.', 'tips' => ['Tip 15–20% at restaurants','Use the subway','Book Broadway shows in advance'], 'language' => 'English', 'currency' => 'USD'],
            'London'    => ['highlights' => ['Big Ben','Tower of London','British Museum','Buckingham Palace'], 'climate' => 'Mild and rainy. Summer (Jun–Aug) is pleasant.', 'tips' => ['Stand right on escalators','Oyster card saves money','Many museums free'], 'language' => 'English', 'currency' => 'GBP. 1 GBP ≈ 1.27 USD'],
            'Tokyo'     => ['highlights' => ['Shibuya Crossing','Senso-ji Temple','Tsukiji Outer Market','Shinjuku Gyoen'], 'climate' => 'Humid subtropical. Spring (Mar–May) and autumn (Oct–Nov) are ideal.', 'tips' => ['Cash still widely used','Be quiet on public transport','Convenience stores are lifesavers'], 'language' => 'Japanese; English signage in tourist areas', 'currency' => 'JPY. 1 USD ≈ 150 JPY'],
            '東京'      => ['highlights' => ['Shibuya Crossing','Senso-ji Temple','Tsukiji Outer Market','Shinjuku Gyoen'], 'climate' => 'Humid subtropical. Spring (Mar–May) and autumn (Oct–Nov) are ideal.', 'tips' => ['Cash still widely used','Be quiet on public transport','Convenience stores are lifesavers'], 'language' => 'Japanese; English signage in tourist areas', 'currency' => 'JPY. 1 USD ≈ 150 JPY'],
            'Kyoto'     => ['highlights' => ['Fushimi Inari Shrine','Arashiyama Bamboo Grove','Kinkaku-ji','Gion District'], 'climate' => 'Humid subtropical. Cherry blossoms and autumn foliage are spectacular.', 'tips' => ['Rent a bicycle','Book popular temples in advance','Respect geisha privacy in Gion'], 'language' => 'Japanese; English signage', 'currency' => 'JPY. 1 USD ≈ 150 JPY'],
            '京都'      => ['highlights' => ['Fushimi Inari Shrine','Arashiyama Bamboo Grove','Kinkaku-ji','Gion District'], 'climate' => 'Humid subtropical. Cherry blossoms and autumn foliage are spectacular.', 'tips' => ['Rent a bicycle','Book popular temples in advance','Respect geisha privacy in Gion'], 'language' => 'Japanese; English signage', 'currency' => 'JPY. 1 USD ≈ 150 JPY'],
        ];

        foreach ($mockData as $key => $data) {
            if (stripos($destination, $key) !== false || stripos($key, $destination) !== false) {
                return json_encode([
                    'destination'  => $destination,
                    'travel_dates' => $travelDates,
                    'highlights'   => $data['highlights'],
                    'climate'      => $data['climate'],
                    'travel_tips'  => $data['tips'],
                    'language'     => $data['language'],
                    'currency'     => $data['currency'],
                ], JSON_UNESCAPED_UNICODE);
            }
        }

        return json_encode([
            'destination'  => $destination,
            'travel_dates' => $travelDates,
            'highlights'   => ['Main tourist attractions','Local markets','Historic landmarks','Natural scenery'],
            'climate'      => 'Prepare clothing suitable for the local climate.',
            'travel_tips'  => ['Check passport validity','Purchase travel insurance','Prepare local currency'],
            'language'     => 'Local language; English may be spoken in tourist areas',
            'currency'     => 'Local currency. Credit cards widely accepted.',
        ], JSON_UNESCAPED_UNICODE);
    }

    // ──────────────────────────────────────────────────────
    // Tool: calculateBudget
    // ──────────────────────────────────────────────────────

    private function calculateBudget(string $destination, int $days, int $totalBudget, int $people): string
    {
        $expensive = ['Paris','パリ','New York','ニューヨーク','London','ロンドン','Sydney','Zurich'];
        $cheap     = ['Bali','バリ島','Thailand','タイ','Bangkok','バンコク','Vietnam','ベトナム','Ho Chi Minh'];

        $isExpensive = collect($expensive)->contains(fn($d) => stripos($destination, $d) !== false);
        $isCheap     = collect($cheap)->contains(fn($d) => stripos($destination, $d) !== false);

        if ($isExpensive) {
            [$fr, $hr, $food, $act, $misc, $dailyHotel, $dailyFood] = [0.35, 0.35, 0.15, 0.10, 0.05, 25000, 8000];
        } elseif ($isCheap) {
            [$fr, $hr, $food, $act, $misc, $dailyHotel, $dailyFood] = [0.40, 0.25, 0.15, 0.12, 0.08, 8000, 3000];
        } else {
            [$fr, $hr, $food, $act, $misc, $dailyHotel, $dailyFood] = [0.35, 0.30, 0.15, 0.12, 0.08, 15000, 5000];
        }

        $perPerson = intdiv($totalBudget, max($people, 1));
        $perHotel  = (int) ($perPerson * $hr);
        $perFood   = (int) ($perPerson * $food);

        $assessment = $perPerson > ($dailyHotel + $dailyFood) * $days * 2
            ? 'Comfortable'
            : ($perPerson > ($dailyHotel + $dailyFood) * $days ? 'Moderate' : 'Tight');

        return json_encode([
            'Total Budget'     => '¥'.number_format($totalBudget).' JPY',
            'Per Person Budget'=> '¥'.number_format($perPerson).' JPY',
            'Breakdown'        => [
                'Flights'       => '¥'.number_format((int)($perPerson * $fr)).' JPY',
                'Accommodation' => '¥'.number_format($perHotel).' JPY (approx. ¥'.number_format(intdiv($perHotel, $days)).'/night)',
                'Food'          => '¥'.number_format($perFood).' JPY (approx. ¥'.number_format(intdiv($perFood, $days)).'/day)',
                'Activities'    => '¥'.number_format((int)($perPerson * $act)).' JPY',
                'Miscellaneous' => '¥'.number_format((int)($perPerson * $misc)).' JPY',
            ],
            'Budget Assessment' => $assessment,
            'Savings Tips'     => [
                'Book flights early to save 20–30%',
                'Use hostels or vacation rentals to cut accommodation costs',
                'Shop at local supermarkets to reduce food expenses',
                'Take advantage of free attractions and walking tours',
            ],
        ], JSON_UNESCAPED_UNICODE);
    }

    // ──────────────────────────────────────────────────────
    // Tool: createItinerary
    // ──────────────────────────────────────────────────────

    private function createItinerary(string $destination, int $days, string $travelStyle = 'Balanced'): string
    {
        $dest = strtolower($destination);

        if (str_contains($dest, 'bali') || str_contains($destination, 'バリ')) {
            $base = [
                ['Morning'=>'Rice Terraces (Tegallalang) walk at sunrise','Afternoon'=>'Local warungs lunch in Ubud','Evening'=>'Monkey Forest','Night'=>'Traditional Kecak fire dance'],
                ['Morning'=>'Sunrise at Tanah Lot Temple','Afternoon'=>'Surfing lesson at Kuta Beach','Evening'=>'Shopping in Seminyak','Night'=>'Sunset cocktails on the beach'],
                ['Morning'=>'Balinese spa & traditional massage','Afternoon'=>'Bali coffee plantation tour','Evening'=>'Seafood BBQ at Jimbaran Beach','Night'=>'Beach stroll'],
                ['Morning'=>'Mount Agung trekking','Afternoon'=>'Lunch at Kintamani highlands','Evening'=>'Ubud Royal Palace','Night'=>'Balinese cooking class'],
            ];
        } elseif (str_contains($dest, 'paris') || str_contains($destination, 'パリ')) {
            $base = [
                ['Morning'=>'Eiffel Tower (open early to avoid crowds)','Afternoon'=>'Croissant & café au lait at a classic Parisian café','Evening'=>'Louvre Museum','Night'=>'Seine River cruise'],
                ['Morning'=>'Montmartre stroll & Sacré-Cœur','Afternoon'=>'French lunch at a local bistro','Evening'=>'Marais art gallery hop','Night'=>'Champs-Élysées illuminations'],
                ['Morning'=>'Day trip to Versailles Palace','Afternoon'=>'Picnic in palace gardens','Evening'=>'Musée d\'Orsay','Night'=>'Paris jazz bar'],
                ['Morning'=>'Paris morning market','Afternoon'=>'Macarons & pain au chocolat walk','Evening'=>'Centre Pompidou','Night'=>'Michelin dinner'],
            ];
        } elseif (str_contains($dest, 'tokyo') || str_contains($destination, '東京')) {
            $base = [
                ['Morning'=>'Senso-ji Temple in Asakusa at dawn','Afternoon'=>'Tsukiji Outer Market seafood lunch','Evening'=>'Shibuya Crossing & Shibuya Sky','Night'=>'Izakaya in Shinjuku'],
                ['Morning'=>'Meiji Shrine & Harajuku Takeshita St','Afternoon'=>'Ramen tasting in Shinjuku','Evening'=>'Akihabara electronics district','Night'=>'Karaoke experience'],
                ['Morning'=>'TeamLab Planets','Afternoon'=>'Sushi-making class in Tsukiji','Evening'=>'Tokyo Skytree','Night'=>'Sake tasting in Ginza'],
                ['Morning'=>'Day trip to Nikko or Kamakura','Afternoon'=>'Onsen experience','Evening'=>'Souvenir shopping in Asakusa','Night'=>'Free time'],
            ];
        } elseif (str_contains($dest, 'kyoto') || str_contains($destination, '京都')) {
            $base = [
                ['Morning'=>'Fushimi Inari Shrine at sunrise','Afternoon'=>'Traditional kaiseki lunch','Evening'=>'Gion district walk for geisha spotting','Night'=>'Pontocho alley dinner'],
                ['Morning'=>'Arashiyama Bamboo Grove','Afternoon'=>'Tenryu-ji Temple garden','Evening'=>'Sagano scenic railway','Night'=>'Kinkaku-ji night illumination (seasonal)'],
                ['Morning'=>'Kinkaku-ji (Golden Pavilion)','Afternoon'=>'Nishiki Market food tour','Evening'=>'Tea ceremony','Night'=>'Kawaramachi nightlife'],
                ['Morning'=>'Day trip to Nara (deer park & Todai-ji)','Afternoon'=>'Obanzai Kyoto home-cooking lunch','Evening'=>'Higashiyama shopping','Night'=>'Onsen at a ryokan'],
            ];
        } else {
            $base = [
                ['Morning'=>'Main sightseeing spots tour','Afternoon'=>'Local restaurant lunch','Evening'=>'Historic district walk','Night'=>'Night view spot'],
                ['Morning'=>'Museum or art gallery','Afternoon'=>'Coffee break at local café','Evening'=>'Local market shopping','Night'=>'Local cuisine dinner'],
                ['Morning'=>'Nature or outdoor activities','Afternoon'=>'Picnic lunch','Evening'=>'Sunset viewing','Night'=>'Night tour'],
                ['Morning'=>'Day trip to nearby area','Afternoon'=>'Local gourmet experience','Evening'=>'Souvenir shopping','Night'=>'Free time'],
            ];
        }

        $itinerary = [];
        for ($i = 1; $i <= $days; $i++) {
            $act   = $base[($i - 1) % count($base)];
            $theme = $i === 1 ? 'Arrival & Check-in' : ($i === $days ? 'Departure Day' : "Exploration Day ".($i - 1));
            $itinerary[] = ["Day {$i}" => [
                'Theme'    => $theme,
                'Morning'  => $i > 1 ? $act['Morning'] : 'Arrive & check in — explore the neighborhood',
                'Afternoon'=> $act['Afternoon'],
                'Evening'  => $i < $days ? $act['Evening'] : 'Pick up last-minute souvenirs & pack',
                'Night'    => $i < $days ? $act['Night'] : 'Early rest — prepare for departure',
            ]];
        }

        return json_encode([
            'Destination' => $destination,
            'Duration'    => "{$days} days",
            'Travel Style'=> $travelStyle,
            'Itinerary'   => $itinerary,
            'Packing List'=> ['Passport','Travel insurance','Credit card','Power adapter','Sunscreen','Basic medications'],
            'Reminders'   => ['Arrive 2 hours before departure','Carry copies of documents','Note emergency contacts'],
        ], JSON_UNESCAPED_UNICODE);
    }

    // ──────────────────────────────────────────────────────
    // Tool: findExperiences
    // ──────────────────────────────────────────────────────

    private function findExperiences(string $destination, string $interests, int $budgetPerDay): string
    {
        $experiences = [
            'Food & Dining'  => ['High Budget'=>['Michelin-starred dinner','Private cooking class','Wine/sake tasting tour'],'Mid Budget'=>['Local market + cooking class','Popular restaurant crawl','Food hopping tour'],'Low Budget'=>['Street food tour','Local supermarket exploration','Fresh market visit at dawn']],
            'Sightseeing'    => ['High Budget'=>['Private guided tour','Helicopter sightseeing','VIP museum tour'],'Mid Budget'=>['Popular landmark group tour','Audio-guided museum','Night bus tour'],'Low Budget'=>['Self-guided walking tour','Free public attractions','Explore with guidebook']],
            'Arts & Culture' => ['High Budget'=>['Private gallery tour','Artist atelier visit','Exclusive auction viewing'],'Mid Budget'=>['Museum & gallery combo','Local artist workshop','Street art tour'],'Low Budget'=>['Free museums','Public art walk','Craft market']],
            'Adventure'      => ['High Budget'=>['Private yacht charter','Skydiving','Luxury spa & adventure package'],'Mid Budget'=>['Surfing lessons','Guided trekking','Snorkeling or diving'],'Low Budget'=>['Hiking trails','Bicycle sightseeing','Local sports event']],
            'Relaxation'     => ['High Budget'=>['5-star spa package','Private beach','Luxury cruise'],'Mid Budget'=>['Traditional massage','Yoga retreat','Hot spring / onsen'],'Low Budget'=>['Public beach','City park picnic','Local café chill']],
            'Shopping'       => ['High Budget'=>['Luxury brand district','Personal stylist service','Antique shop tour'],'Mid Budget'=>['Local designer boutique','Outlet mall','Craft & artisan market'],'Low Budget'=>['Flea market & bazaar','Local supermarket souvenir hunt','Street market arcade']],
        ];

        $level = $budgetPerDay >= 15000 ? 'High Budget' : ($budgetPerDay >= 8000 ? 'Mid Budget' : 'Low Budget');

        $interestList = [];
        foreach (preg_split('/[,、\/]/', $interests) as $item) {
            $item = trim($item);
            foreach (array_keys($experiences) as $key) {
                if (stripos($key, $item) !== false || stripos($item, $key) !== false) {
                    if (!in_array($key, $interestList)) $interestList[] = $key;
                    break;
                }
            }
        }
        if (empty($interestList)) $interestList = ['Food & Dining', 'Sightseeing'];

        $recommendations = [];
        foreach ($interestList as $interest) {
            $recommendations[$interest] = $experiences[$interest][$level];
        }

        return json_encode([
            'Destination'            => $destination,
            'Budget Level'           => $level,
            'Daily Experience Budget'=> '¥'.number_format($budgetPerDay).' JPY',
            'Recommended Experiences'=> $recommendations,
            'Hidden Gems'            => ['Visit popular spots early morning','Ask locals for under-the-radar cafés','Local fresh markets for authentic experience'],
            'Advance Booking Required'=> ['Popular restaurants: book a week ahead','High-demand activities: pre-book online','Special exhibitions: check schedules early'],
        ], JSON_UNESCAPED_UNICODE);
    }

    // ──────────────────────────────────────────────────────
    // Parameter extraction
    // ──────────────────────────────────────────────────────

    private function extractParams(string $req): array
    {
        // Destination
        $destination = 'destination';
        if (preg_match('/【旅行先】\s*(.+?)(?:\n|【)/', $req, $m)) {
            $destination = trim($m[1]);
        }
        if ($destination === 'destination') {
            $patterns = [
                '/(Bali|Paris|New York|London|Sydney|Tokyo|Kyoto|Osaka|Bangkok|Ho Chi Minh|Seoul|Taipei|Hawaii|Singapore|Rome|Barcelona|Amsterdam|Dubai|Lisbon)/i',
                '/(バリ島|パリ|ニューヨーク|ロンドン|シドニー|東京|京都|大阪|バンコク|ベトナム|ソウル|台湾|ハワイ|シンガポール)/',
            ];
            foreach ($patterns as $pat) {
                if (preg_match($pat, $req, $m)) { $destination = $m[1]; break; }
            }
        }
        if ($destination === 'destination' && preg_match('/\b([A-Z][a-z]{2,}(?:\s[A-Z][a-z]+)?)\b/', $req, $m)) {
            $destination = $m[1];
        }

        // Duration
        $days = 4;
        if (preg_match('/(\d+)\s*-?\s*(?:day|days)/i', $req, $m))      $days = (int)$m[1];
        elseif (preg_match('/(\d+)\s*night/i', $req, $m))              $days = (int)$m[1] + 1;
        elseif (preg_match('/(\d+)\s*(?:泊|日間|日)/', $req, $m))       $days = str_contains($m[0], '泊') ? (int)$m[1] + 1 : (int)$m[1];
        elseif (preg_match('/【旅行期間】\s*(\d+)/', $req, $m))          $days = (int)$m[1];

        // Budget
        $budget = 450000;
        if (preg_match('/\$\s?(\d[\d,]+)/', $req, $m))                          $budget = (int)str_replace(',','',$m[1]) * 150;
        elseif (preg_match('/(\d[\d,]+)\s*(?:dollars?|USD)/i', $req, $m))       $budget = (int)str_replace(',','',$m[1]) * 150;
        elseif (preg_match('/(\d+)\s*万円/', $req, $m))                          $budget = (int)$m[1] * 10000;
        elseif (preg_match('/([\d,]{4,})\s*円/', $req, $m))                     $budget = (int)str_replace(',','',$m[1]);
        elseif (preg_match('/【予算】\s*([\d,]+)/', $req, $m))                   $budget = (int)str_replace(',','',$m[1]);

        // People
        $people = 2;
        if (preg_match('/(\d+)\s*(?:people|persons?|travelers?)/i', $req, $m)) $people = (int)$m[1];
        elseif (preg_match('/(\d+)\s*人/', $req, $m))                           $people = (int)$m[1];
        elseif (preg_match('/【人数】\s*(\d+)/', $req, $m))                      $people = (int)$m[1];

        // Interests
        $interestMap = [
            'Food & Dining' => ['food','dining','gourmet','restaurant','グルメ','食'],
            'Sightseeing'   => ['sightseeing','sight','landmark','tour','観光'],
            'Arts & Culture'=> ['art','culture','museum','gallery','アート','文化'],
            'Adventure'     => ['adventure','hiking','surfing','sport','アドベンチャー'],
            'Relaxation'    => ['relax','spa','beach','resort','リラックス'],
            'Shopping'      => ['shopping','shop','market','ショッピング'],
        ];
        $found = [];
        $lower = strtolower($req);
        foreach ($interestMap as $interest => $keywords) {
            foreach ($keywords as $kw) {
                if (str_contains($lower, strtolower($kw))) { $found[] = $interest; break; }
            }
        }
        $interests = $found ? implode(', ', $found) : 'Food & Dining, Sightseeing';

        // Travel style
        $styleMap = [
            'Sightseeing-focused'  => ['sightseeing','観光重視'],
            'Food-focused'         => ['food-focused','gourmet','グルメ重視'],
            'Resort & Relaxation'  => ['resort','relaxation','リゾート','リラックス重視'],
            'Balanced'             => ['balanced','バランス'],
        ];
        $travelStyle = 'Balanced';
        if (preg_match('/【旅行スタイル】\s*(.+?)(?:\n|【|$)/u', $req, $m)) {
            $travelStyle = trim($m[1]);
        } else {
            foreach ($styleMap as $style => $kws) {
                foreach ($kws as $kw) {
                    if (str_contains($lower, strtolower($kw))) { $travelStyle = $style; break 2; }
                }
            }
        }

        return [
            'destination'   => $destination,
            'duration_days' => $days,
            'budget'        => $budget,
            'num_people'    => $people,
            'interests'     => $interests,
            'travel_style'  => $travelStyle,
        ];
    }

    // ──────────────────────────────────────────────────────
    // Groq LLM call
    // ──────────────────────────────────────────────────────

    private function callLlm(string $userRequest, string $dest, string $info, string $budgetData, string $itinerary, string $exps, string $language): string
    {
        $isJa = $language === 'ja';
        $langInstruction = $isJa ? '日本語で書いてください。' : 'Write everything in English.';

        $structure = $isJa ? $this->structureJa() : $this->structureEn();

        $systemPrompt = <<<PROMPT
You are an expert travel planner with deep local knowledge of destinations worldwide.
Using the provided JSON data as a base AND your own extensive knowledge, create a highly detailed and specific travel plan in Markdown.

{$langInstruction}

CRITICAL RULES — you MUST follow all of these:

1. **SPECIFIC PLACE NAMES ONLY**: Every attraction, restaurant, market, and neighborhood must use its real, actual name.
   - ❌ BAD: "Visit a local temple" / "Have lunch at a local restaurant"
   - ✅ GOOD: "Visit Wat Pho (Th Wang Phraya, 08:00–18:30, ฿200)" / "Lunch at Thip Samai (Maha Chai Rd) — iconic pad thai since 1966"

2. **REAL LOGISTICS**: Include approximate travel times, best visiting hours, entrance fees, and nearest transit stop.

3. **ITINERARY DATA OVERRIDE**: If the [Itinerary Data] contains generic entries, REPLACE them with specific real recommendations for {$dest}.

4. **BUDGET NUMBERS**: Use ONLY the exact figures from [Budget Breakdown] JSON.

5. **LOCAL INSIDER TIPS**: Include at least 2–3 tips that only a local or seasoned traveler would know.

6. **FOOD SPECIFICITY**: Name at least 3 specific restaurants or street food stalls with neighborhood/address and a signature dish.

Always follow this structure:
{$structure}
PROMPT;

        $context = <<<CTX
Create a highly detailed, specific travel plan for the following request.

[User Request]
{$userRequest}

[Destination Research]
{$info}

[Budget Breakdown]
{$budgetData}

[Itinerary Data — use as skeleton only; replace generic entries with real specific place names]
{$itinerary}

[Recommended Experiences]
{$exps}

[IMPORTANT REMINDER]
- Use real attraction names, real restaurant names, real neighborhood names for {$dest}.
- Include specific details: opening hours, entrance fees, addresses, transport options.
CTX;

        for ($attempt = 0; $attempt < 3; $attempt++) {
            try {
                $response = Http::timeout(120)
                    ->withHeaders([
                        'Authorization' => 'Bearer '.env('GROQ_API_KEY', ''),
                        'Content-Type'  => 'application/json',
                    ])
                    ->post(self::API_URL, [
                        'model'    => self::MODEL,
                        'messages' => [
                            ['role' => 'system', 'content' => $systemPrompt],
                            ['role' => 'user',   'content' => $context],
                        ],
                    ]);

                if ($response->successful()) {
                    return $response->json('choices.0.message.content')
                        ?? 'Failed to generate a travel plan. Please try again.';
                }

                if ($response->status() === 429) {
                    $wait = 15 * ($attempt + 1);
                    sleep($wait);
                    continue;
                }

                throw new \RuntimeException('Groq API error: '.$response->status());
            } catch (\Throwable $e) {
                if ($attempt === 2) throw $e;
                sleep(5);
            }
        }

        return 'Failed to generate a travel plan due to API quota limits. Please try again in a few minutes.';
    }

    private function structureJa(): string
    {
        return <<<'MD'
## 🌍 旅行プラン：[実際の目的地名]

### ✈️ 旅行概要
- 目的地・日数・予算・人数を箇条書きで

### 📍 [目的地] について
- 気候・ベストシーズン・言語・通貨・治安情報

### 💰 予算内訳
（JSONデータの数値をそのままリスト形式で記載）

### 📅 日程（Day 1〜最終日）
**Day X：[その日のテーマ]**
- 🌅 午前：[具体的なスポット名・住所・所要時間・入場料]
- ☀️ 午後：[具体的なレストラン名・おすすめメニュー]
- 🌆 夕方：[具体的な場所・アクティビティ]
- 🌙 夜：[ディナーのレストラン名や夜の過ごし方]
- 🚇 移動ヒント：[交通手段・所要時間・費用]

### 🎯 おすすめ体験 & グルメ
- 必食料理（具体的な店名・住所付き）
- 見逃せないアクティビティ（予約方法・費用）
- 地元民も通うローカルスポット

### 💡 旅のヒント
- 入場料・開館時間の注意点
- 混雑回避テクニック
- 持ち物リスト・注意事項
MD;
    }

    private function structureEn(): string
    {
        return <<<'MD'
## 🌍 Travel Plan: [Actual Destination Name]

### ✈️ Trip Overview
- Destination, duration, budget, number of travelers (bullet points)

### 📍 About [Destination]
- Climate, best season, language, currency, safety tips

### 💰 Budget Breakdown
(Use exact figures from JSON data in list format)

### 📅 Day-by-Day Itinerary
**Day X: [Theme for the day]**
- 🌅 Morning: [Specific attraction, area/address, duration, entry fee]
- ☀️ Afternoon: [Specific restaurant or site name, recommended dishes]
- 🌆 Evening: [Specific venue or activity with details]
- 🌙 Night: [Restaurant name or evening activity]
- 🚇 Transport Tips: [How to get around, duration, cost]

### 🎯 Recommended Experiences & Food
- Must-try dishes (with specific restaurant names and addresses)
- Top activities (booking info and costs)
- Hidden local gems off the tourist trail

### 💡 Travel Tips
- Opening hours and entry fees for key attractions
- Crowd-avoidance strategies
- Packing list and important reminders
MD;
    }
}
