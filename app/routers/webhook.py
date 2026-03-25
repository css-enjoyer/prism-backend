from fastapi import APIRouter, HTTPException, Request
import hmac
from hashlib import sha256
from ..config import settings

router = APIRouter()
# Run server with: uv run uvicorn app.main:app --reload
# Then run ngrok with: ngrok http 8000
# Use ngrok dashboard at: localhost:4040 -> Update github url on every start


@router.post("/webhook")
async def handle_webhook(request: Request):
    event_type = request.headers.get("X-GitHub-Event")
    if event_type != "pull_request":
        return {"status": "ignored", "reason": f"Unsupported event type: {event_type}"}

    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature header")

    if not signature.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Invalid signature format")

    if not hmac.compare_digest(
        signature.split("=", 1)[1],
        hmac.new(
            key=settings.webhook_secret.encode(),
            msg=await request.body(),
            digestmod=sha256,
        ).hexdigest(),
    ):
        raise HTTPException(status_code=403, detail="Invalid signature")

    body = await request.json()
    delivery_id = request.headers.get("X-GitHub-Delivery")
    repo = body["repository"]["full_name"]
    pr_number = body["pull_request"]["number"]
    print(f"Delivery: {delivery_id} | Repo: {repo} | PR: {pr_number}")
    return {"status": "received"}
