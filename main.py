from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel
import json
import os
import asyncio
import traceback
from agents import orchestrate_travel_plan

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
        result = orchestrate_travel_plan(user_message)
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

        # Run synchronous in executor to not block event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, orchestrate_travel_plan, user_message)

        yield f"data: {json.dumps({'type': 'complete', 'plan': result}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}


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
