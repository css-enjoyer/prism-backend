from fastapi import APIRouter, Request
import json

router = APIRouter()
# Run server with: uv run uvicorn app.main:app --reload
# Then run ngrok with: ngrok http 8000


@router.post("/webhook")
async def handle_webhook(request: Request):
    event_type = request.headers.get("X-GitHub-Event")
    if event_type != "pull_request":
        return {"status": "ignored", "reason": f"Unsupported event type: {event_type}"}

    body = await request.json()
    delivery_id = request.headers.get("X-GitHub-Delivery")
    repo = body["repository"]["full_name"]
    pr_number = body["pull_request"]["number"]
    print(f"Delivery: {delivery_id} | Repo: {repo} | PR: {pr_number}")
    return {"status": "received"}
