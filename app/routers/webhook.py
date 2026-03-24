from fastapi import APIRouter, Request
import json

router = APIRouter()


@router.post("/webhook")
async def handle_webhook(request: Request):
    headers = request.headers

    raw_body = await request.body()
    content_type = headers.get("content-type", "")

    parsed_json = None
    if "application/json" in content_type and raw_body:
        try:
            parsed_json = json.loads(raw_body)
        except json.JSONDecodeError:
            parsed_json = None

    return {"url": str(request.url), "parsed_json": parsed_json}
