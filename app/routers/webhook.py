from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
import hmac
from hashlib import sha256

from ..db.session import get_db
from ..models.analysis import Analysis, AnalysisStatus
from ..config import settings
from ..services.analysis import EMPTY_FEEDBACK, run_analysis

router = APIRouter()
# Run server with: uv run uvicorn app.main:app --reload
# Then run ngrok with: ngrok http 8000
# Use ngrok dashboard at: localhost:4040 -> Update github url on every start


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
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

    # Check if pull request
    event_type = request.headers.get("X-GitHub-Event")
    if event_type != "pull_request":
        return {"status": "ignored", "reason": f"Unsupported event type: {event_type}"}

    body = await request.json()

    # Check if pull request is opened or updated
    if body.get("action") not in ["opened", "synchronize"]:
        return {
            "status": "ignored",
            "reason": f"Unsupported action: {body.get('action')}",
        }

    repo_full_name = body["repository"]["full_name"]
    pr_number = body["pull_request"]["number"]
    gh_delivery_id = request.headers.get("X-GitHub-Delivery")

    if not gh_delivery_id:
        raise HTTPException(status_code=400, detail="Missing delivery id header")

    # Upon valid request, record into db
    stmt = (
        pg_insert(Analysis)
        .values(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            gh_delivery_id=gh_delivery_id,
            feedback=EMPTY_FEEDBACK,
            status=AnalysisStatus.pending,
        )
        .on_conflict_do_nothing(index_elements=["gh_delivery_id"])
        .returning(Analysis.id)
    )
    result = await db.execute(stmt)
    analysis_id = result.scalar_one_or_none()
    await db.commit()

    if analysis_id is None:
        return {"status": "ignored", "reason": "Duplicate delivery"}

    # Github needs a request within 10 seconds, so we will process the diff in the background and return immediately
    background_tasks.add_task(
        run_analysis,
        analysis_id,
        repo_full_name,
        pr_number,
        # gh_delivery_id,
    )

    return {
        "status": "received",
        "message": "Pull request event received and will be processed in the background.",
    }
