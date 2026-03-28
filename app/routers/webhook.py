from fastapi import APIRouter, Depends, HTTPException, Request
import hmac
from hashlib import sha256

from app.dependencies import verify_api_key
from ..config import settings

router = APIRouter()
# Run server with: uv run uvicorn app.main:app --reload
# Then run ngrok with: ngrok http 8000
# Use ngrok dashboard at: localhost:4040 -> Update github url on every start


@router.post("/webhook", dependencies=[Depends(verify_api_key)])
async def handle_webhook(request: Request):
    # Check if pull request
    event_type = request.headers.get("X-GitHub-Event")
    if event_type != "pull_request":
        return {"status": "ignored", "reason": f"Unsupported event type: {event_type}"}

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature header")
    if not signature.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Invalid signature format")
    body_bytes = await request.body()
    expected = hmac.new(
        key=settings.webhook_secret.encode(),
        msg=body_bytes,
        digestmod=sha256,
    ).hexdigest()
    received = signature.split("=", 1)[1]
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=403, detail="Invalid signature")

    body = await request.json()

    # Check if pull request is opened or updated
    if body.get("action") not in ["opened", "synchronize"]:
        return {
            "status": "ignored",
            "reason": f"Unsupported action: {body.get('action')}",
        }

    delivery_id = request.headers.get("X-GitHub-Delivery")
    diff_payload = body["pull_request"]["diff_url"]
    repo = body["repository"]["full_name"]
    pr_number = body["pull_request"]["number"]
    print(
        f"Delivery: {delivery_id} | Repo: {repo} | PR: {pr_number} | Diff: {diff_payload}"
    )
    return {"status": "received"}
