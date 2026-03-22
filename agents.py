import os
import json
import re
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("GEMINI_API_KEY", ""),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
MODEL = "gemini-2.5-flash"


def research_destination(destination: str, travel_dates: str) -> str:
    """Research tourist attractions, climate, and local information for a travel destination.
    Args:
        destination: Travel destination (e.g., Bali, Paris, New York)
        travel_dates: Travel period (e.g., March 15-19, 2025)
    """
    mock_data = {
        "Bali": {
            "highlights": ["Ubud Art Village", "Tanah Lot Temple", "Kuta Beach", "Rice Terraces (Tegallalang)"],
            "climate": "Tropical climate, average 27°C year-round. Dry season (April-October) is best.",
            "tips": ["Tipping culture exists", "Do not drink tap water", "Cover up at temples and mosques"],
            "language": "Indonesian & English widely spoken in tourist areas",
            "currency": "Indonesian Rupiah (IDR). 1 USD ≈ 15,500 IDR"
        },
        "バリ島": {
            "highlights": ["Ubud Art Village", "Tanah Lot Temple", "Kuta Beach", "Rice Terraces (Tegallalang)"],
            "climate": "Tropical climate, average 27°C year-round. Dry season (April-October) is best.",
            "tips": ["Tipping culture exists", "Do not drink tap water", "Cover up at temples and mosques"],
            "language": "Indonesian & English widely spoken in tourist areas",
            "currency": "Indonesian Rupiah (IDR). 1 USD ≈ 15,500 IDR"
        },
        "Paris": {
            "highlights": ["Eiffel Tower", "Louvre Museum", "Montmartre", "Versailles Palace"],
            "climate": "Temperate oceanic climate. Spring (April-May) and autumn (Sept-Oct) are ideal.",
            "tips": ["Watch out for pickpockets", "Restaurant reservations recommended", "Many shops closed on Sundays"],
            "language": "French. English is spoken in tourist areas.",
            "currency": "Euro (EUR). 1 EUR ≈ 1.08 USD"
        },
        "パリ": {
            "highlights": ["Eiffel Tower", "Louvre Museum", "Montmartre", "Versailles Palace"],
            "climate": "Temperate oceanic climate. Spring (April-May) and autumn (Sept-Oct) are ideal.",
            "tips": ["Watch out for pickpockets", "Restaurant reservations recommended", "Many shops closed on Sundays"],
            "language": "French. English is spoken in tourist areas.",
            "currency": "Euro (EUR). 1 EUR ≈ 1.08 USD"
        },
        "New York": {
            "highlights": ["Times Square", "Central Park", "Statue of Liberty", "Metropolitan Museum of Art"],
            "climate": "Humid continental. Spring (April-June) and fall (Sept-Nov) are best seasons.",
            "tips": ["Tip 15-20% at restaurants", "Use the subway for efficient travel", "Book Broadway shows in advance"],
            "language": "English",
            "currency": "US Dollar (USD)"
        },
        "London": {
            "highlights": ["Big Ben & Houses of Parliament", "Tower of London", "British Museum", "Buckingham Palace"],
            "climate": "Mild and rainy. Summer (June-August) is most pleasant.",
            "tips": ["Stand on the right on escalators", "Oyster card saves on transport", "Many museums are free"],
            "language": "English",
            "currency": "British Pound (GBP). 1 GBP ≈ 1.27 USD"
        },
        "Tokyo": {
            "highlights": ["Shibuya Crossing", "Senso-ji Temple", "Tsukiji Outer Market", "Shinjuku Gyoen"],
            "climate": "Humid subtropical. Spring (March-May) and autumn (Oct-Nov) are ideal.",
            "tips": ["Cash is still widely used", "Be quiet on public transport", "Convenience stores are your best friend"],
            "language": "Japanese. English signage in major tourist areas.",
            "currency": "Japanese Yen (JPY). 1 USD ≈ 150 JPY"
        },
        "東京": {
            "highlights": ["Shibuya Crossing", "Senso-ji Temple", "Tsukiji Outer Market", "Shinjuku Gyoen"],
            "climate": "Humid subtropical. Spring (March-May) and autumn (Oct-Nov) are ideal.",
            "tips": ["Cash is still widely used", "Be quiet on public transport", "Convenience stores are your best friend"],
            "language": "Japanese. English signage in major tourist areas.",
            "currency": "Japanese Yen (JPY). 1 USD ≈ 150 JPY"
        },
        "Kyoto": {
            "highlights": ["Fushimi Inari Shrine", "Arashiyama Bamboo Grove", "Kinkaku-ji (Golden Pavilion)", "Gion District"],
            "climate": "Humid subtropical. Spring cherry blossoms and autumn foliage are spectacular.",
            "tips": ["Rent a bicycle for easy exploration", "Book popular temples in advance", "Respect geisha privacy in Gion"],
            "language": "Japanese. English signage in major tourist areas.",
            "currency": "Japanese Yen (JPY). 1 USD ≈ 150 JPY"
        },
        "京都": {
            "highlights": ["Fushimi Inari Shrine", "Arashiyama Bamboo Grove", "Kinkaku-ji (Golden Pavilion)", "Gion District"],
            "climate": "Humid subtropical. Spring cherry blossoms and autumn foliage are spectacular.",
            "tips": ["Rent a bicycle for easy exploration", "Book popular temples in advance", "Respect geisha privacy in Gion"],
            "language": "Japanese. English signage in major tourist areas.",
            "currency": "Japanese Yen (JPY). 1 USD ≈ 150 JPY"
        },
    }

    for key in mock_data:
        if key.lower() in destination.lower() or destination.lower() in key.lower():
            data = mock_data[key]
            return json.dumps({
                "destination": destination,
                "travel_dates": travel_dates,
                "highlights": data["highlights"],
                "climate": data["climate"],
                "travel_tips": data["tips"],
                "language": data["language"],
                "currency": data["currency"]
            }, ensure_ascii=False)

    return json.dumps({
        "destination": destination,
        "travel_dates": travel_dates,
        "highlights": ["Main tourist attractions", "Local markets", "Historic landmarks", "Natural scenery"],
        "climate": "Please prepare clothing suitable for the local climate.",
        "travel_tips": ["Check passport validity", "Purchase travel insurance", "Prepare local currency"],
        "language": "Local language; English may be spoken in tourist areas",
        "currency": "Local currency. Credit cards widely accepted."
    }, ensure_ascii=False)


def calculate_budget(destination: str, duration_days: int, total_budget_jpy: int, num_people: int = 1) -> str:
    """Calculate and suggest a travel budget breakdown.
    Args:
        destination: Travel destination
        duration_days: Number of travel days
        total_budget_jpy: Total budget in JPY
        num_people: Number of travelers (default 1)
    """
    total_budget_jpy = int(total_budget_jpy)
    duration_days = int(duration_days)
    num_people = int(num_people)
    per_person_budget = total_budget_jpy // num_people

    expensive_destinations = ["Paris", "パリ", "New York", "ニューヨーク", "London", "ロンドン", "Sydney", "Zurich"]
    cheap_destinations = ["Bali", "バリ島", "Thailand", "タイ", "Bangkok", "バンコク", "Vietnam", "ベトナム", "Ho Chi Minh"]

    is_expensive = any(d.lower() in destination.lower() for d in expensive_destinations)
    is_cheap = any(d.lower() in destination.lower() for d in cheap_destinations)

    if is_expensive:
        flight_ratio, hotel_ratio, food_ratio, activity_ratio, misc_ratio = 0.35, 0.35, 0.15, 0.10, 0.05
        daily_hotel_estimate = 25000
        daily_food_estimate = 8000
    elif is_cheap:
        flight_ratio, hotel_ratio, food_ratio, activity_ratio, misc_ratio = 0.40, 0.25, 0.15, 0.12, 0.08
        daily_hotel_estimate = 8000
        daily_food_estimate = 3000
    else:
        flight_ratio, hotel_ratio, food_ratio, activity_ratio, misc_ratio = 0.35, 0.30, 0.15, 0.12, 0.08
        daily_hotel_estimate = 15000
        daily_food_estimate = 5000

    per_hotel = int(per_person_budget * hotel_ratio)
    per_food = int(per_person_budget * food_ratio)

    budget_breakdown = {
        "Total Budget": f"¥{total_budget_jpy:,} JPY",
        "Per Person Budget": f"¥{per_person_budget:,} JPY",
        "Breakdown": {
            "Flights": f"¥{int(per_person_budget * flight_ratio):,} JPY",
            "Accommodation": f"¥{per_hotel:,} JPY (approx. ¥{per_hotel // duration_days:,} per night)",
            "Food": f"¥{per_food:,} JPY (approx. ¥{per_food // duration_days:,} per day)",
            "Activities": f"¥{int(per_person_budget * activity_ratio):,} JPY",
            "Miscellaneous": f"¥{int(per_person_budget * misc_ratio):,} JPY"
        },
        "Savings Tips": [
            "Book flights early to save 20-30%",
            "Use hostels or vacation rentals to cut accommodation costs",
            "Shop at local supermarkets and markets to reduce food expenses",
            "Take advantage of free attractions and walking tours"
        ],
        "Budget Assessment": "Comfortable" if per_person_budget > (daily_hotel_estimate + daily_food_estimate) * duration_days * 2 else "Moderate" if per_person_budget > (daily_hotel_estimate + daily_food_estimate) * duration_days else "Tight"
    }

    return json.dumps(budget_breakdown, ensure_ascii=False)


def create_itinerary(destination: str, duration_days: int, travel_style: str = "Balanced") -> str:
    """Create a detailed travel itinerary and schedule.
    Args:
        destination: Travel destination
        duration_days: Number of travel days
        travel_style: Travel style (Sightseeing-focused / Food-focused / Resort & Relaxation / Balanced)
    """
    duration_days = int(duration_days)
    days = []

    dest_lower = destination.lower()

    if "bali" in dest_lower or "バリ" in destination:
        base_activities = [
            {"Morning": "Rice Terraces (Tegallalang) walk at sunrise", "Afternoon": "Local warungs lunch in Ubud", "Evening": "Monkey Forest visit", "Night": "Traditional Kecak fire dance performance"},
            {"Morning": "Sunrise at Tanah Lot Temple", "Afternoon": "Surfing lesson at Kuta Beach", "Evening": "Shopping in Seminyak", "Night": "Sunset cocktails on the beach"},
            {"Morning": "Balinese spa & traditional massage", "Afternoon": "Bali coffee plantation tour", "Evening": "Seafood BBQ dinner at Jimbaran Beach", "Night": "Leisurely beach stroll"},
            {"Morning": "Mount Agung trekking", "Afternoon": "Lunch at Kintamani highlands with volcano view", "Evening": "Ubud Royal Palace visit", "Night": "Balinese cooking class"},
        ]
    elif "paris" in dest_lower or "パリ" in destination:
        base_activities = [
            {"Morning": "Eiffel Tower (visit at opening to avoid crowds)", "Afternoon": "Croissant and café au lait at a classic Parisian café", "Evening": "Louvre Museum (Mona Lisa is a must)", "Night": "Seine River cruise"},
            {"Morning": "Montmartre stroll & Sacré-Cœur Basilica", "Afternoon": "French lunch at a local bistro", "Evening": "Marais district art gallery hop", "Night": "Champs-Élysées illuminations"},
            {"Morning": "Day trip to Versailles Palace", "Afternoon": "Picnic in the palace gardens", "Evening": "Musée d'Orsay", "Night": "Paris jazz bar"},
            {"Morning": "Paris morning market shopping", "Afternoon": "Macarons and pain au chocolat tasting walk", "Evening": "Centre Pompidou", "Night": "Dinner at a Michelin-starred restaurant"},
        ]
    elif "tokyo" in dest_lower or "東京" in destination:
        base_activities = [
            {"Morning": "Senso-ji Temple in Asakusa at dawn", "Afternoon": "Tsukiji Outer Market seafood lunch", "Evening": "Shibuya Crossing and Shibuya Sky observation deck", "Night": "Izakaya dinner in Shinjuku"},
            {"Morning": "Meiji Shrine & Harajuku Takeshita Street", "Afternoon": "Ramen tasting in Shinjuku", "Evening": "Akihabara electronics and anime district", "Night": "Karaoke experience"},
            {"Morning": "Teamlab Planets or digital art museum", "Afternoon": "Sushi-making class in Tsukiji", "Evening": "Tokyo Skytree observation", "Night": "Sake tasting bar in Ginza"},
            {"Morning": "Day trip to Nikko or Kamakura", "Afternoon": "Local onsen (hot spring) experience", "Evening": "Souvenir shopping in Asakusa", "Night": "Free time"},
        ]
    elif "kyoto" in dest_lower or "京都" in destination:
        base_activities = [
            {"Morning": "Fushimi Inari Shrine at sunrise (fewer crowds)", "Afternoon": "Traditional Kyoto cuisine (kaiseki) for lunch", "Evening": "Gion district walk for geisha spotting", "Night": "Pontocho alley dinner"},
            {"Morning": "Arashiyama Bamboo Grove walk", "Afternoon": "Tenryu-ji Temple garden", "Evening": "Sagano scenic railway", "Night": "Night illumination at Kinkaku-ji (seasonal)"},
            {"Morning": "Kinkaku-ji (Golden Pavilion)", "Afternoon": "Nishiki Market food tour", "Evening": "Tea ceremony experience", "Night": "Kawaramachi nightlife"},
            {"Morning": "Day trip to Nara (deer park & Todai-ji)", "Afternoon": "Obanzai Kyoto home-cooking lunch", "Evening": "Souvenir shopping in Higashiyama", "Night": "Onsen at a ryokan"},
        ]
    else:
        base_activities = [
            {"Morning": "Main sightseeing spots tour", "Afternoon": "Local restaurant lunch", "Evening": "Historic district walk", "Night": "Night view spot"},
            {"Morning": "Museum or art gallery visit", "Afternoon": "Coffee break at a local café", "Evening": "Local market shopping", "Night": "Local cuisine dinner"},
            {"Morning": "Nature or outdoor activities", "Afternoon": "Picnic lunch", "Evening": "Sunset viewing", "Night": "Night tour"},
            {"Morning": "Day trip to nearby area", "Afternoon": "Local gourmet experience", "Evening": "Souvenir shopping", "Night": "Free time"},
        ]

    for day_num in range(1, duration_days + 1):
        activity = base_activities[(day_num - 1) % len(base_activities)]
        theme = "Arrival & Check-in" if day_num == 1 else "Departure Day" if day_num == duration_days else f"Exploration Day {day_num - 1}"
        day_plan = {
            f"Day {day_num}": {
                "Theme": theme,
                "Morning": activity["Morning"] if day_num > 1 else "Arrive & check in to hotel — explore the neighborhood",
                "Afternoon": activity["Afternoon"],
                "Evening": activity["Evening"] if day_num < duration_days else "Pick up last-minute souvenirs & pack",
                "Night": activity["Night"] if day_num < duration_days else "Early rest — prepare for departure"
            }
        }
        days.append(day_plan)

    return json.dumps({
        "Destination": destination,
        "Duration": f"{duration_days} days",
        "Travel Style": travel_style,
        "Itinerary": days,
        "Packing List": ["Passport", "Travel insurance card", "Credit card", "Power adapter", "Sunscreen", "Basic medications"],
        "Reminders": ["Arrive at the airport at least 2 hours before departure", "Carry copies of important documents", "Note down emergency contact numbers"]
    }, ensure_ascii=False)


def find_experiences(destination: str, interests: str, budget_per_day_jpy: int) -> str:
    """Suggest recommended experiences, restaurants, and activities.
    Args:
        destination: Travel destination
        interests: Interests (e.g., Food & Dining, Arts & Culture, Adventure, Relaxation)
        budget_per_day_jpy: Daily experience budget in JPY
    """
    experiences = {
        "Food & Dining": {
            "High Budget": ["Michelin-starred restaurant dinner", "Private cooking class with a local chef", "Wine or sake tasting tour"],
            "Mid Budget": ["Local market tour + cooking class", "Popular local restaurant crawl", "Food hopping tour with a guide"],
            "Low Budget": ["Street food tour", "Exploring local supermarket ingredients", "Early morning fresh market visit"]
        },
        "Sightseeing": {
            "High Budget": ["Private guided sightseeing tour", "Helicopter sightseeing flight", "VIP museum tour with curator"],
            "Mid Budget": ["Popular landmark group tour", "Audio-guided museum visits", "Night sightseeing bus tour"],
            "Low Budget": ["Self-guided walking tour", "Free public attractions", "Explore with a local guidebook"]
        },
        "Arts & Culture": {
            "High Budget": ["Private gallery tour", "Visit to a renowned artist's atelier", "Exclusive auction house viewing"],
            "Mid Budget": ["Museum & gallery combo ticket", "Local artist workshop", "Street art walking tour"],
            "Low Budget": ["Free museums and galleries", "Public art walking tour", "Local craft market browsing"]
        },
        "Adventure": {
            "High Budget": ["Private yacht charter", "Skydiving experience", "Luxury spa & adventure package"],
            "Mid Budget": ["Surfing lessons", "Guided trekking tour", "Snorkeling or diving experience"],
            "Low Budget": ["Hiking trails", "Bicycle rental sightseeing", "Local sports event spectating"]
        },
        "Relaxation": {
            "High Budget": ["5-star hotel spa package", "Private beach rental", "Luxury river or sea cruise"],
            "Mid Budget": ["Traditional massage experience", "Yoga retreat session", "Hot spring or onsen visit"],
            "Low Budget": ["Relaxing at a public beach", "Picnic in a city park", "Chill at a local café"]
        },
        "Shopping": {
            "High Budget": ["Luxury brand district shopping", "Private personal stylist service", "Antique specialist shop tour"],
            "Mid Budget": ["Local designer boutique", "Outlet mall visit", "Local craft and artisan market"],
            "Low Budget": ["Flea market & bazaar", "Souvenir hunting in a local supermarket", "Covered street market arcade"]
        }
    }

    budget_per_day_jpy = int(budget_per_day_jpy)
    budget_level = "High Budget" if budget_per_day_jpy >= 15000 else "Mid Budget" if budget_per_day_jpy >= 8000 else "Low Budget"

    # Normalize interest string: handle comma-separated or similar
    raw_interests = re.split(r'[,、/]', interests)
    interest_list = []
    for item in raw_interests:
        item = item.strip()
        for key in experiences:
            if key.lower() in item.lower() or item.lower() in key.lower():
                if key not in interest_list:
                    interest_list.append(key)
                break

    if not interest_list:
        interest_list = ["Food & Dining", "Sightseeing"]

    recommendations = {}
    for interest in interest_list:
        recommendations[interest] = experiences[interest][budget_level]

    return json.dumps({
        "Destination": destination,
        "Budget Level": budget_level,
        "Daily Experience Budget": f"¥{budget_per_day_jpy:,} JPY",
        "Recommended Experiences": recommendations,
        "Hidden Gems": [
            "Visit popular spots early morning to beat the crowds",
            "Ask locals for their favorite under-the-radar cafés",
            "Check out local fresh markets for an authentic experience"
        ],
        "Advance Booking Required": [
            "Popular restaurants: book at least a week ahead",
            "High-demand activities: pre-book online for discounts",
            "Special museum exhibitions: check schedules early"
        ]
    }, ensure_ascii=False)


def _extract_travel_params(user_request: str) -> dict:
    """Extract travel parameters from a user request (simple parser supporting English and Japanese)."""

    # Destination detection — English and Japanese city names
    dest_patterns = [
        r'(Bali|Paris|New York|London|Sydney|Tokyo|Kyoto|Osaka|Bangkok|Ho Chi Minh|Seoul|Taipei|Hawaii|Singapore|Rome|Barcelona|Amsterdam|Dubai|Cancun|Lisbon)',
        r'(バリ島|パリ|ニューヨーク|ロンドン|シドニー|東京|京都|大阪|タイ|バンコク|ベトナム|ホーチミン|ソウル|台湾|台北|ハワイ|シンガポール|ローマ|バルセロナ)',
    ]
    destination = "destination"
    for pat in dest_patterns:
        m = re.search(pat, user_request, re.IGNORECASE)
        if m:
            destination = m.group(1)
            break

    # If still not found, try a generic capitalized word (English city heuristic)
    if destination == "destination":
        m = re.search(r'\b([A-Z][a-z]{2,}(?:\s[A-Z][a-z]+)?)\b', user_request)
        if m:
            destination = m.group(1)

    # Japanese city fallback
    if destination == "destination":
        m = re.search(r'([ぁ-んァ-ヶー一-龯]{2,8}(?:島|市|県|州|国)?)', user_request)
        if m:
            destination = m.group(1)

    # Final fallback: read destination from the structured 【旅行先】 tag
    if destination == "destination":
        m = re.search(r'【旅行先】\s*(.+?)(?:\n|【)', user_request)
        if m:
            destination = m.group(1).strip()

    # Duration — English patterns: "X days", "X-day", "X nights" (+1)
    duration_days = 4  # default
    m = re.search(r'(\d+)\s*-?\s*(?:day|days)', user_request, re.IGNORECASE)
    if m:
        duration_days = int(m.group(1))
    else:
        m = re.search(r'(\d+)\s*night', user_request, re.IGNORECASE)
        if m:
            duration_days = int(m.group(1)) + 1
        else:
            # Japanese patterns
            m = re.search(r'(\d+)\s*(?:泊|日間|日)', user_request)
            if m:
                raw = int(m.group(1))
                duration_days = raw + 1 if '泊' in m.group(0) else raw

    # Budget — English: "$XXXX" or "XXXX dollars/USD", Japanese: "XX万円" or "XXXX円"
    budget = 450000  # default ~$3000 equivalent in JPY
    m = re.search(r'\$\s?(\d[\d,]+)', user_request)
    if m:
        usd_amount = int(m.group(1).replace(',', ''))
        budget = usd_amount * 150  # convert USD to JPY
    else:
        m = re.search(r'(\d[\d,]+)\s*(?:dollars?|USD)', user_request, re.IGNORECASE)
        if m:
            usd_amount = int(m.group(1).replace(',', ''))
            budget = usd_amount * 150
        else:
            m = re.search(r'(\d+)\s*万円', user_request)
            if m:
                budget = int(m.group(1)) * 10_000
            else:
                m = re.search(r'([\d,]{4,})\s*円', user_request)
                if m:
                    budget = int(m.group(1).replace(',', ''))

    # Number of people — English: "X people/persons/travelers", Japanese: "X人"
    num_people = 2  # default
    m = re.search(r'(\d+)\s*(?:people|persons?|travelers?|guests?)', user_request, re.IGNORECASE)
    if m:
        num_people = int(m.group(1))
    else:
        m = re.search(r'(\d+)\s*人', user_request)
        if m:
            num_people = int(m.group(1))

    # Interests — detect both English and Japanese keywords
    interest_map = {
        'Food & Dining': ['food', 'dining', 'gourmet', 'restaurant', 'グルメ', '食'],
        'Sightseeing': ['sightseeing', 'sight', 'landmark', 'tour', '観光'],
        'Arts & Culture': ['art', 'culture', 'museum', 'gallery', 'アート', '文化'],
        'Adventure': ['adventure', 'hiking', 'surfing', 'sport', 'アドベンチャー'],
        'Relaxation': ['relax', 'spa', 'beach', 'resort', 'リラックス'],
        'Shopping': ['shopping', 'shop', 'market', 'ショッピング'],
    }
    found_interests = []
    req_lower = user_request.lower()
    for interest, keywords in interest_map.items():
        for kw in keywords:
            if kw.lower() in req_lower:
                if interest not in found_interests:
                    found_interests.append(interest)
                break

    interests = ', '.join(found_interests) if found_interests else 'Food & Dining, Sightseeing'

    return {
        "destination": destination,
        "duration_days": duration_days,
        "budget": budget,
        "num_people": num_people,
        "interests": interests,
    }


def orchestrate_travel_plan(user_request: str) -> str:
    """Main orchestrator: uses Google Gemini (gemini-1.5-flash) to generate a travel plan."""

    # Step 1: Extract parameters from the user request
    params = _extract_travel_params(user_request)
    dest = params["destination"]
    days = params["duration_days"]
    budget = params["budget"]
    people = params["num_people"]
    interests = params["interests"]
    daily_budget = budget // people // max(days, 1)

    # Step 2: Run all agent tools to gather data
    info        = research_destination(dest, f"{days}-day trip")
    budget_data = calculate_budget(dest, days, budget, people)
    itinerary   = create_itinerary(dest, days, "Balanced")
    exps        = find_experiences(dest, interests, daily_budget)

    # Step 3: Pass collected data as context to the LLM and generate a plan in English
    context = f"""Please create a travel plan based on the following data.

[User Request]
{user_request}

[Destination Research]
{info}

[Budget Breakdown]
{budget_data}

[Itinerary Data]
{itinerary}

[Recommended Experiences]
{exps}"""

    system_prompt = """You are a professional English-language travel planner.
Using the provided JSON data, create a well-structured, engaging travel plan in Markdown.

CRITICAL: Use ONLY the budget figures from the [Budget Breakdown] JSON data. Do NOT invent or change any budget numbers. The "Total Budget" and "Per Person Budget" values in the JSON are the correct ones to display.

Always follow this structure:

## 🌍 Travel Plan: [Destination]

### ✈️ Trip Overview
(Destination, duration, budget, and number of travelers — use bullet points)

### 📍 About [Destination]
(Climate, language, currency, and top highlights)

### 💰 Budget Breakdown
(Copy the exact budget figures from the JSON data in a table or list format)

### 📅 Day-by-Day Itinerary
(Detailed schedule from Day 1 to the final day)

### 🎯 Recommended Experiences
(Activities and experiences tailored to the traveler's interests)

### 💡 Travel Tips
(Reminders, packing list, and useful advice)

Write everything in English. Be specific, practical, and make it inspiring to read."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ],
    )

    return response.choices[0].message.content or "Failed to generate a travel plan. Please try again."
