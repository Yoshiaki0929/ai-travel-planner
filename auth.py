import os
import jwt
from fastapi import Header
from fastapi.responses import JSONResponse

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

async def get_current_user(authorization: str = Header(None)) -> dict | None:
    """Extract and validate Supabase JWT. Returns user dict or None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not SUPABASE_JWT_SECRET:
        return None
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("user_metadata", {}).get("full_name") or payload.get("email", "").split("@")[0],
            "avatar": payload.get("user_metadata", {}).get("avatar_url"),
        }
    except Exception:
        return None
