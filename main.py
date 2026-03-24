# ローカル開発用: .envファイルを最初に読み込む（agents.pyのimport前に必要）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Request, Header, UploadFile, File, Form
from typing import Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel
import json
import os
import re
import asyncio
import traceback
import uuid
from agents import orchestrate_travel_plan
import httpx
from auth import get_current_user

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

app = FastAPI(title="AI Travel Planner")

# Serve static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


class TravelRequest(BaseModel):
    destination: str
    duration_days: int
    budget_jpy: int
    num_people: int = 1
    interests: str = "グルメ、観光"
    travel_style: str = "バランス型"
    additional_requests: str = ""
    language: str = "en"


@app.get("/")
async def root():
    return FileResponse("static/index.html")


def _validate_travel_request(r: "TravelRequest"):
    if not r.destination.strip():
        return "Please enter a destination (e.g. Paris, Tokyo, Bali)."
    if r.duration_days < 1 or r.duration_days > 60:
        return "Trip duration must be between 1 and 60 days."
    if r.num_people < 1 or r.num_people > 20:
        return "Number of travelers must be between 1 and 20."
    min_budget = 10000 * r.num_people * r.duration_days
    if r.budget_jpy < min_budget:
        return (f"A budget of ¥{r.budget_jpy:,} is too low for {r.num_people} person(s) "
                f"over {r.duration_days} day(s). Please enter at least ¥{min_budget:,}.")
    return None


@app.post("/api/plan")
async def create_plan(travel_request: TravelRequest):
    """旅行プランを生成するエンドポイント（同期）"""

    validation_error = _validate_travel_request(travel_request)
    if validation_error:
        return JSONResponse(status_code=400, content={"error": validation_error})

    user_message = f"""
以下の条件で旅行プランを作成してください：

【旅行先】{travel_request.destination}
【旅行期間】{travel_request.duration_days}日間
【予算】{travel_request.budget_jpy:,}円（{travel_request.num_people}人）
【人数】{travel_request.num_people}人
【興味・関心】{travel_request.interests}
【旅行スタイル】{travel_request.travel_style}
【その他の希望】{travel_request.additional_requests if travel_request.additional_requests else 'なし'}

旅行先調査、予算計算、日程作成、体験提案の全ツールを使って、完全な旅行プランを作成してください。
"""

    try:
        result = orchestrate_travel_plan(user_message, language=travel_request.language)
        return {"plan": result}
    except Exception as e:
        error_detail = traceback.format_exc()
        return JSONResponse(status_code=500, content={"error": str(e), "detail": error_detail})


@app.post("/api/plan/stream")
async def create_plan_stream(travel_request: TravelRequest):
    """旅行プランをSSEストリームで返すエンドポイント"""

    validation_error = _validate_travel_request(travel_request)
    if validation_error:
        return JSONResponse(status_code=400, content={"error": validation_error})

    user_message = f"""
以下の条件で旅行プランを作成してください：

【旅行先】{travel_request.destination}
【旅行期間】{travel_request.duration_days}日間
【予算】{travel_request.budget_jpy:,}円（{travel_request.num_people}人）
【人数】{travel_request.num_people}人
【興味・関心】{travel_request.interests}
【旅行スタイル】{travel_request.travel_style}
【その他の希望】{travel_request.additional_requests if travel_request.additional_requests else 'なし'}

旅行先調査、予算計算、日程作成、体験提案の全ツールを使って、完全な旅行プランを作成してください。
"""

    async def generate():
        yield f"data: {json.dumps({'type': 'start', 'message': '旅行プランを生成中...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)

        yield f"data: {json.dumps({'type': 'progress', 'message': '🔍 旅行先の情報を調査中...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, orchestrate_travel_plan, user_message, travel_request.language)
            yield f"data: {json.dumps({'type': 'complete', 'plan': result}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/config")
async def get_config():
    """Return public Supabase keys for the frontend."""
    return {
        "supabase_url": os.environ.get("SUPABASE_URL", ""),
        "supabase_anon_key": os.environ.get("SUPABASE_ANON_KEY", ""),
    }


@app.get("/api/me")
async def get_me(authorization: str = Header(None)):
    """Return current user info."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    return user


@app.post("/api/plans/save")
async def save_plan(request: Request, authorization: str = Header(None)):
    """Save a travel plan to Supabase for the logged-in user."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Login required to save plans"})

    body = await request.json()
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_key:
        return JSONResponse(status_code=500, content={"error": "Database not configured"})

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/saved_plans",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={
                "user_id": user["id"],
                "destination": body.get("destination", ""),
                "duration_days": body.get("duration_days", 1),
                "budget_jpy": body.get("budget_jpy", 0),
                "plan_content": body.get("plan_content", ""),
            },
        )
    if resp.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": "Failed to save plan"})
    return {"ok": True, "plan": resp.json()[0] if resp.json() else {}}


@app.get("/api/profile")
async def get_profile(authorization: str = Header(None)):
    """Get the logged-in user's profile."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/profiles?user_id=eq.{user['id']}&limit=1",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    data = resp.json() if resp.status_code == 200 else []
    return data[0] if data else {}


@app.get("/api/profile/{user_id}")
async def get_user_profile(user_id: str):
    """Get any user's public profile by user_id (no auth required)."""
    if not _UUID_RE.match(user_id):
        return JSONResponse(status_code=400, content={"error": "Invalid user_id"})
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/profiles?user_id=eq.{user_id}&limit=1",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    data = resp.json() if resp.status_code == 200 else []
    return data[0] if data else {}


@app.put("/api/profile")
async def update_profile(request: Request, authorization: str = Header(None)):
    """Create or update the logged-in user's profile."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    body = await request.json()
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    profile_data = {
        "user_id": user["id"],
        "display_name": body.get("display_name", ""),
        "bio": body.get("bio", ""),
        "home_city": body.get("home_city", ""),
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/profiles",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
            json=profile_data,
        )
    if resp.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": "Failed to save profile"})
    return {"ok": True}


@app.get("/api/plans")
async def get_plans(authorization: str = Header(None)):
    """Get all saved plans for the logged-in user."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/saved_plans?user_id=eq.{user['id']}&order=created_at.desc",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
            },
        )
    return resp.json() if resp.status_code == 200 else []


@app.delete("/api/plans/{plan_id}")
async def delete_plan(plan_id: str, authorization: str = Header(None)):
    """Delete a saved plan (only if it belongs to the current user)."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/saved_plans?id=eq.{plan_id}&user_id=eq.{user['id']}",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
            },
        )
    return {"ok": resp.status_code == 204}


_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB


@app.post("/api/photos")
async def upload_photo(
    destination: str = Form(...),
    caption: str = Form(""),
    visibility: str = Form("public"),
    file: Optional[UploadFile] = File(None),
    authorization: str = Header(None),
):
    """Post to the travel timeline. Photo is optional (max 5 MB if provided)."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Login required"})
    if not caption.strip() and file is None:
        return JSONResponse(status_code=400, content={"error": "Message or photo is required"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_key:
        return JSONResponse(status_code=500, content={"error": "Storage not configured"})

    image_url = ""
    if file is not None:
        if file.content_type not in _ALLOWED_IMAGE_TYPES:
            return JSONResponse(status_code=400, content={"error": "Only JPEG/PNG/WebP/GIF images are allowed"})
        content = await file.read()
        if len(content) > _MAX_PHOTO_BYTES:
            return JSONResponse(status_code=400, content={"error": "File size must be under 5 MB"})
        ext = (file.filename or "photo").rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
            ext = "jpg"
        file_path = f"{user['id']}/{uuid.uuid4()}.{ext}"
        async with httpx.AsyncClient() as client:
            storage_resp = await client.post(
                f"{supabase_url}/storage/v1/object/travel-photos/{file_path}",
                headers={"Authorization": f"Bearer {supabase_key}", "Content-Type": file.content_type},
                content=content,
            )
        if storage_resp.status_code not in (200, 201):
            return JSONResponse(status_code=500, content={"error": "Image upload failed"})
        image_url = f"{supabase_url}/storage/v1/object/public/travel-photos/{file_path}"

    async with httpx.AsyncClient() as client:
        db_resp = await client.post(
            f"{supabase_url}/rest/v1/photos",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={
                "user_id": user["id"],
                "user_name": user["name"],
                "user_avatar": user.get("avatar") or "",
                "destination": destination.strip(),
                "caption": caption.strip()[:300],
                "image_url": image_url,
                "visibility": visibility if visibility in ("public", "private") else "public",
            },
        )
    if db_resp.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": "Failed to save post"})
    return {"ok": True, "photo": db_resp.json()[0] if db_resp.json() else {}}


@app.get("/api/photos/timeline")
async def get_timeline(limit: int = 20, offset: int = 0, user_id: str = "", authorization: str = Header(None)):
    """Return recent travel photos, optionally filtered by user_id.
    Private posts are only visible to their owner.
    """
    caller = await get_current_user(authorization)
    caller_id = caller["id"] if caller else None

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if user_id and not _UUID_RE.match(user_id):
        return JSONResponse(status_code=400, content={"error": "Invalid user_id"})
    user_filter = f"&user_id=eq.{user_id}" if user_id else ""

    # Show private posts only when viewing own profile
    is_own_profile = user_id and caller_id and user_id == caller_id
    if is_own_profile:
        visibility_filter = ""  # show all (public + private)
    else:
        visibility_filter = "&visibility=eq.public"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/photos?order=created_at.desc&limit={min(limit, 50)}&offset={offset}{user_filter}{visibility_filter}",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    return resp.json() if resp.status_code == 200 else []


@app.get("/api/photos/my-likes")
async def get_my_likes(authorization: str = Header(None)):
    """Return list of photo_ids the current user has liked."""
    user = await get_current_user(authorization)
    if not user:
        return []
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/photo_likes?user_id=eq.{user['id']}&select=photo_id",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    data = resp.json() if resp.status_code == 200 else []
    return [r["photo_id"] for r in data]


@app.post("/api/photos/{photo_id}/like")
async def toggle_like(photo_id: str, authorization: str = Header(None)):
    """Toggle like on a photo. Returns {liked, count}."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}

    async with httpx.AsyncClient() as client:
        # Check existing like
        check = await client.get(
            f"{supabase_url}/rest/v1/photo_likes?photo_id=eq.{photo_id}&user_id=eq.{user['id']}&limit=1",
            headers=headers,
        )
        existing = check.json() if check.status_code == 200 else []

        if existing:
            await client.delete(
                f"{supabase_url}/rest/v1/photo_likes?photo_id=eq.{photo_id}&user_id=eq.{user['id']}",
                headers=headers,
            )
            liked = False
        else:
            await client.post(
                f"{supabase_url}/rest/v1/photo_likes",
                headers={**headers, "Content-Type": "application/json", "Prefer": "resolution=ignore-duplicates"},
                json={"photo_id": photo_id, "user_id": user["id"]},
            )
            liked = True

        # Count current likes
        count_resp = await client.get(
            f"{supabase_url}/rest/v1/photo_likes?photo_id=eq.{photo_id}&select=id",
            headers={**headers, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
        )
        cr = count_resp.headers.get("content-range", "0/0")
        count = int(cr.split("/")[-1]) if "/" in cr else 0

        # Update like_count in photos
        await client.patch(
            f"{supabase_url}/rest/v1/photos?id=eq.{photo_id}",
            headers={**headers, "Content-Type": "application/json"},
            json={"like_count": count},
        )

    return {"liked": liked, "count": count}


@app.patch("/api/photos/{photo_id}")
async def update_photo(photo_id: str, request: Request, authorization: str = Header(None)):
    """Edit destination and caption of a post (owner only)."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    body = await request.json()
    update = {}
    if "destination" in body and body["destination"].strip():
        update["destination"] = body["destination"].strip()[:100]
    if "caption" in body:
        update["caption"] = body["caption"].strip()[:300]
    if not update:
        return JSONResponse(status_code=400, content={"error": "Nothing to update"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{supabase_url}/rest/v1/photos?id=eq.{photo_id}&user_id=eq.{user['id']}",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=update,
        )
    if resp.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": "Database error"})
    rows = resp.json()
    if not rows:
        return JSONResponse(status_code=404, content={"error": "Photo not found"})
    return {"ok": True, "photo": rows[0]}


@app.patch("/api/photos/{photo_id}/visibility")
async def update_visibility(photo_id: str, request: Request, authorization: str = Header(None)):
    """Toggle visibility of a photo (owner only)."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    body = await request.json()
    visibility = body.get("visibility")
    if visibility not in ("public", "private"):
        return JSONResponse(status_code=400, content={"error": "Invalid visibility"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{supabase_url}/rest/v1/photos?id=eq.{photo_id}&user_id=eq.{user['id']}",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={"visibility": visibility},
        )
    if resp.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": "Update failed"})
    rows = resp.json()
    if not rows:
        return JSONResponse(status_code=404, content={"error": "Photo not found"})
    return {"ok": True, "visibility": visibility}


@app.delete("/api/photos/{photo_id}")
async def delete_photo(photo_id: str, authorization: str = Header(None)):
    """Delete a photo (only if it belongs to the current user)."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    async with httpx.AsyncClient() as client:
        fetch_resp = await client.get(
            f"{supabase_url}/rest/v1/photos?id=eq.{photo_id}&user_id=eq.{user['id']}&limit=1",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    photos = fetch_resp.json() if fetch_resp.status_code == 200 else []
    if not photos:
        return JSONResponse(status_code=404, content={"error": "Photo not found"})

    image_url = photos[0].get("image_url", "")
    storage_marker = "/storage/v1/object/public/travel-photos/"
    if storage_marker in image_url:
        file_path = image_url.split(storage_marker, 1)[1]
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{supabase_url}/storage/v1/object/travel-photos/{file_path}",
                headers={"Authorization": f"Bearer {supabase_key}"},
            )

    async with httpx.AsyncClient() as client:
        del_resp = await client.delete(
            f"{supabase_url}/rest/v1/photos?id=eq.{photo_id}&user_id=eq.{user['id']}",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    return {"ok": del_resp.status_code == 204}


class FriendRequestBody(BaseModel):
    addressee_name: str = ""
    addressee_avatar: str = ""


async def _get_all_friendships(user_id: str, supabase_url: str, supabase_key: str) -> list:
    """Return all friendships (any status) involving this user."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/friendships?or=(requester_id.eq.{user_id},addressee_id.eq.{user_id})",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    return resp.json() if resp.status_code == 200 else []


@app.post("/api/friends/request/{addressee_id}")
async def send_friend_request(
    addressee_id: str,
    body: FriendRequestBody,
    authorization: str = Header(None),
):
    """Send a friend request to another user."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    if user["id"] == addressee_id:
        return JSONResponse(status_code=400, content={"error": "Cannot add yourself"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/friendships",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={
                "requester_id": user["id"],
                "requester_name": user["name"] or "",
                "requester_avatar": user.get("avatar") or "",
                "addressee_id": addressee_id,
                "addressee_name": body.addressee_name,
                "addressee_avatar": body.addressee_avatar,
                "status": "pending",
            },
        )
    if resp.status_code in (409,):
        return JSONResponse(status_code=409, content={"error": "Request already exists"})
    if resp.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": "Failed to send request"})
    return {"ok": True, "friendship": resp.json()[0] if resp.json() else {}}


@app.get("/api/friends")
async def get_friends(authorization: str = Header(None)):
    """Return accepted friends for the current user."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    rows = await _get_all_friendships(user["id"], supabase_url, supabase_key)
    friends = []
    for r in rows:
        if r.get("status") != "accepted":
            continue
        if r["requester_id"] == user["id"]:
            friends.append({"friendship_id": r["id"], "user_id": r["addressee_id"],
                            "name": r["addressee_name"], "avatar": r["addressee_avatar"]})
        else:
            friends.append({"friendship_id": r["id"], "user_id": r["requester_id"],
                            "name": r["requester_name"], "avatar": r["requester_avatar"]})
    return friends


@app.get("/api/friends/requests")
async def get_friend_requests(authorization: str = Header(None)):
    """Return pending incoming friend requests."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/friendships?addressee_id=eq.{user['id']}&status=eq.pending",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    rows = resp.json() if resp.status_code == 200 else []
    return [{"friendship_id": r["id"], "user_id": r["requester_id"],
             "name": r["requester_name"], "avatar": r["requester_avatar"],
             "created_at": r["created_at"]} for r in rows]


@app.get("/api/friends/statuses")
async def get_friend_statuses(authorization: str = Header(None)):
    """Return a map of {user_id: {friendship_id, status, is_requester}} for the current user."""
    user = await get_current_user(authorization)
    if not user:
        return {}

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    rows = await _get_all_friendships(user["id"], supabase_url, supabase_key)
    result = {}
    for r in rows:
        other_id = r["addressee_id"] if r["requester_id"] == user["id"] else r["requester_id"]
        result[other_id] = {
            "friendship_id": r["id"],
            "status": r["status"],
            "is_requester": r["requester_id"] == user["id"],
        }
    return result


@app.put("/api/friends/{friendship_id}/accept")
async def accept_friend_request(friendship_id: str, authorization: str = Header(None)):
    """Accept a pending friend request."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{supabase_url}/rest/v1/friendships?id=eq.{friendship_id}&addressee_id=eq.{user['id']}&status=eq.pending",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
            },
            json={"status": "accepted"},
        )
    return {"ok": resp.status_code in (200, 204)}


@app.delete("/api/friends/{friendship_id}")
async def remove_friend(friendship_id: str, authorization: str = Header(None)):
    """Remove a friend or decline/cancel a request."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/friendships?id=eq.{friendship_id}"
            f"&or=(requester_id.eq.{user['id']},addressee_id.eq.{user['id']})",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    return {"ok": resp.status_code == 204}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ===== CHAT =====

_global_room_id: str = ""


class CreateRoomRequest(BaseModel):
    name: str
    is_private: bool = False


class SendMessageRequest(BaseModel):
    content: str


async def _ensure_global_room():
    global _global_room_id
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_key:
        return
    system_user = "00000000-0000-0000-0000-000000000000"
    async with httpx.AsyncClient() as client:
        # Try insert, ignore conflict
        await client.post(
            f"{supabase_url}/rest/v1/chat_rooms",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=ignore-duplicates",
            },
            json={"type": "global", "name": "Global", "is_private": False, "created_by": system_user},
        )
        # Now fetch it
        resp = await client.get(
            f"{supabase_url}/rest/v1/chat_rooms?type=eq.global&limit=1",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    rows = resp.json() if resp.status_code == 200 else []
    if rows:
        _global_room_id = rows[0]["id"]


async def _get_room_access(room_id: str, user_id: str, supabase_url: str, supabase_key: str) -> bool:
    """Returns True if user_id has access to room_id."""
    async with httpx.AsyncClient() as client:
        room_resp = await client.get(
            f"{supabase_url}/rest/v1/chat_rooms?id=eq.{room_id}&limit=1",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    rooms = room_resp.json() if room_resp.status_code == 200 else []
    if not rooms:
        return False
    room = rooms[0]
    if room.get("type") == "global":
        return True
    if room.get("type") == "custom" and not room.get("is_private"):
        return True
    # Check membership
    async with httpx.AsyncClient() as client:
        mem_resp = await client.get(
            f"{supabase_url}/rest/v1/room_members?room_id=eq.{room_id}&user_id=eq.{user_id}&limit=1",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    members = mem_resp.json() if mem_resp.status_code == 200 else []
    return len(members) > 0


@app.on_event("startup")
async def startup_event():
    await _ensure_global_room()


@app.get("/api/chat/global")
async def get_global_room():
    """Return the global room id (no auth required)."""
    return {"id": _global_room_id}


@app.get("/api/chat/rooms")
async def get_chat_rooms(authorization: str = Header(None)):
    """Return all rooms the user has access to."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    user_id = user["id"]

    rooms_map = {}

    # Global room
    if _global_room_id:
        rooms_map[_global_room_id] = {
            "id": _global_room_id, "type": "global", "name": "Global",
            "is_private": False, "plan_id": None, "created_by": None,
        }

    async with httpx.AsyncClient() as client:
        # Rooms user is a member of
        mem_resp = await client.get(
            f"{supabase_url}/rest/v1/room_members?user_id=eq.{user_id}&select=room_id,chat_rooms(*)",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
        if mem_resp.status_code == 200:
            for row in mem_resp.json():
                room = row.get("chat_rooms")
                if room and room.get("id"):
                    rooms_map[room["id"]] = room

        # Public custom rooms
        pub_resp = await client.get(
            f"{supabase_url}/rest/v1/chat_rooms?type=eq.custom&is_private=eq.false",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
        if pub_resp.status_code == 200:
            for room in pub_resp.json():
                if room.get("id"):
                    rooms_map[room["id"]] = room

    return list(rooms_map.values())


@app.post("/api/chat/rooms")
async def create_chat_room(body: CreateRoomRequest, authorization: str = Header(None)):
    """Create a custom chat room."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    name = body.name.strip()[:50]
    if not name:
        return JSONResponse(status_code=400, content={"error": "Room name is required"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    user_id = user["id"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/chat_rooms",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={"type": "custom", "name": name, "is_private": body.is_private, "created_by": user_id},
        )
    if resp.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": "Failed to create room"})
    new_room = resp.json()[0] if resp.json() else {}
    room_id = new_room.get("id")
    if room_id:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{supabase_url}/rest/v1/room_members",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=ignore-duplicates",
                },
                json={"room_id": room_id, "user_id": user_id},
            )
    return new_room


@app.post("/api/chat/dm/{other_user_id}")
async def get_or_create_dm(other_user_id: str, authorization: str = Header(None)):
    """Get or create a DM room between the caller and another user."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    if not _UUID_RE.match(other_user_id):
        return JSONResponse(status_code=400, content={"error": "Invalid user id"})

    user_id = user["id"]
    if user_id == other_user_id:
        return JSONResponse(status_code=400, content={"error": "Cannot DM yourself"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    # Validate friendship
    async with httpx.AsyncClient() as client:
        fr_resp = await client.get(
            f"{supabase_url}/rest/v1/friendships"
            f"?or=(and(requester_id.eq.{user_id},addressee_id.eq.{other_user_id})"
            f",and(requester_id.eq.{other_user_id},addressee_id.eq.{user_id}))"
            f"&status=eq.accepted&limit=1",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    friendships = fr_resp.json() if fr_resp.status_code == 200 else []
    if not friendships:
        return JSONResponse(status_code=403, content={"error": "Not friends with this user"})

    dm_key = "_".join(sorted([user_id, other_user_id]))

    async with httpx.AsyncClient() as client:
        existing = await client.get(
            f"{supabase_url}/rest/v1/chat_rooms?dm_key=eq.{dm_key}&type=eq.dm&limit=1",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    rooms = existing.json() if existing.status_code == 200 else []
    if rooms:
        return rooms[0]

    # Create new DM room
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/chat_rooms",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={"type": "dm", "name": dm_key, "is_private": True, "created_by": user_id, "dm_key": dm_key},
        )
    if resp.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": "Failed to create DM room"})
    new_room = resp.json()[0] if resp.json() else {}
    room_id = new_room.get("id")
    if room_id:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{supabase_url}/rest/v1/room_members",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=ignore-duplicates",
                },
                json=[
                    {"room_id": room_id, "user_id": user_id},
                    {"room_id": room_id, "user_id": other_user_id},
                ],
            )
    return new_room


@app.get("/api/chat/rooms/{room_id}/messages")
async def get_messages(room_id: str, authorization: str = Header(None)):
    """Return messages for a room."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    if not _UUID_RE.match(room_id):
        return JSONResponse(status_code=400, content={"error": "Invalid room_id"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    has_access = await _get_room_access(room_id, user["id"], supabase_url, supabase_key)
    if not has_access:
        return JSONResponse(status_code=403, content={"error": "Access denied"})

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/messages?room_id=eq.{room_id}&order=created_at.asc&limit=100",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    return resp.json() if resp.status_code == 200 else []


@app.post("/api/chat/rooms/{room_id}/messages")
async def send_message(room_id: str, body: SendMessageRequest, authorization: str = Header(None)):
    """Send a message to a room."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    if not _UUID_RE.match(room_id):
        return JSONResponse(status_code=400, content={"error": "Invalid room_id"})

    content = body.content.strip()[:1000]
    if not content:
        return JSONResponse(status_code=400, content={"error": "Message content is required"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    has_access = await _get_room_access(room_id, user["id"], supabase_url, supabase_key)
    if not has_access:
        return JSONResponse(status_code=403, content={"error": "Access denied"})

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/messages",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={
                "room_id": room_id,
                "user_id": user["id"],
                "user_name": user.get("name") or user.get("email", ""),
                "user_avatar": user.get("avatar") or "",
                "content": content,
            },
        )
    if resp.status_code not in (200, 201):
        return JSONResponse(status_code=500, content={"error": "Failed to send message"})
    return {"ok": True, "message": resp.json()[0] if resp.json() else {}}


@app.get("/api/chat/rooms/{room_id}/members")
async def get_room_members(room_id: str, authorization: str = Header(None)):
    """Return members of a room."""
    user = await get_current_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    if not _UUID_RE.match(room_id):
        return JSONResponse(status_code=400, content={"error": "Invalid room_id"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    has_access = await _get_room_access(room_id, user["id"], supabase_url, supabase_key)
    if not has_access:
        return JSONResponse(status_code=403, content={"error": "Access denied"})

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/room_members?room_id=eq.{room_id}&select=user_id,user_name,user_avatar,joined_at",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
    return resp.json() if resp.status_code == 200 else []


if os.environ.get("DEBUG_ENDPOINTS") == "true":
    @app.get("/debug")
    async def debug():
        from openai import OpenAI
        key = os.environ.get("GEMINI_API_KEY", "")
        models = []
        try:
            c = OpenAI(api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
            models = [m.id for m in c.models.list()]
        except Exception as e:
            models = [f"error: {str(e)}"]
        return {
            "gemini_key_set": bool(key),
            "gemini_key_prefix": key[:8] + "..." if len(key) > 8 else "(empty)",
            "available_models": models,
        }

    @app.get("/debug/auth")
    async def debug_auth(authorization: str = Header(None)):
        import jwt as pyjwt
        secret = os.environ.get("SUPABASE_JWT_SECRET", "")
        if not authorization:
            return {"error": "No Authorization header"}
        token = authorization.removeprefix("Bearer ").strip()
        try:
            payload = pyjwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
            return {"ok": True, "sub": payload.get("sub"), "email": payload.get("email"), "role": payload.get("role")}
        except Exception as e:
            try:
                header = pyjwt.get_unverified_header(token)
                unverified = pyjwt.decode(token, options={"verify_signature": False})
            except Exception:
                header, unverified = {}, {}
            return {"error": str(e), "token_header": header, "token_payload_unverified": unverified, "secret_length": len(secret)}



# SPA catch-all: serve index.html for all non-API, non-static routes
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("static/"):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return FileResponse("static/index.html")
