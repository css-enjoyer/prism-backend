from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
import hmac
from hashlib import sha256

from ..config import settings
from ..services.analysis import run_analysis

router = APIRouter()
# Run server with: uv run uvicorn app.main:app --reload
# Then run ngrok with: ngrok http 8000
# Use ngrok dashboard at: localhost:4040 -> Update github url on every start


@router.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
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

    diff_url = body["pull_request"]["diff_url"]
    repo_full_name = body["repository"]["full_name"]
    pr_number = body["pull_request"]["number"]
    gh_delivery_id = request.headers.get("X-GitHub-Delivery")
    print(
        f"Delivery: {gh_delivery_id} | Repo: {repo_full_name} | PR: {pr_number} | Diff: {diff_url}"
    )

    # Github needs a request within 10 seconds, so we will process the diff in the background and return immediately
    background_tasks.add_task(
        run_analysis,
        diff_url,
        repo_full_name,
        pr_number,
        gh_delivery_id,
    )

    return {
        "status": "received",
        "message": "Pull request event received and will be processed in the background.",
    }
