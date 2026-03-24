import os
import httpx
from fastapi import Header

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


async def get_current_user(authorization: str = Header(None)) -> dict | None:
    """Validate token by calling Supabase /auth/v1/user. Works with both HS256 and ES256."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    supabase_url = os.environ.get("SUPABASE_URL", "")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not supabase_url or not anon_key:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": anon_key,
                },
                timeout=10,
            )
        if resp.status_code != 200:
            return None
        user = resp.json()
        return {
            "id": user.get("id"),
            "email": user.get("email"),
            "name": (user.get("user_metadata") or {}).get("full_name")
                    or (user.get("email") or "").split("@")[0],
            "avatar": (user.get("user_metadata") or {}).get("avatar_url"),
        }
    except Exception as e:
        print(f"[auth] Supabase user lookup failed: {e}")
        return None
