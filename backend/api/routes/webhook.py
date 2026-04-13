"""
GitHub Webhook handler — auto-rebuild portfolio on push events
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import hmac
import structlog

from api.database import get_db, User, BuildJob, JobStatus
from api.config import settings
from api.worker import run_portfolio_build

router = APIRouter()
log = structlog.get_logger()

WEBHOOK_SECRET = settings.JWT_SECRET  # reuse secret for webhook signing


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook HMAC signature."""
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github/{user_id}")
async def handle_github_webhook(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Receives GitHub webhook push events.
    URL is per-user: /api/webhooks/github/{user_id}
    User registers this URL in their GitHub App/Webhook settings.
    """
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    # Verify signature
    if not verify_github_signature(body, signature):
        raise HTTPException(401, "Invalid webhook signature")

    event = request.headers.get("X-GitHub-Event")
    if event not in ("push", "create"):
        return {"ignored": True, "event": event}

    payload = await request.json()
    ref = payload.get("ref", "")

    # Only rebuild on main/master branch pushes
    if not any(ref.endswith(b) for b in ("main", "master")):
        return {"ignored": True, "reason": "non-default branch"}

    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # Check plan throttling — free tier: max 1 auto-rebuild per 24h
    # (add rate limiting logic here for production)

    # Dispatch rebuild job
    job = BuildJob(
        user_id=user.id,
        status=JobStatus.PENDING,
        trigger="webhook",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = run_portfolio_build.delay(
        job_id=job.id,
        user_id=user.id,
        github_token=user.github_token,
        github_username=user.github_username,
        trigger="webhook",
        pushed_repo=payload.get("repository", {}).get("full_name"),
    )

    job.celery_task_id = task.id
    await db.commit()

    log.info("Webhook rebuild triggered", user=user.github_username, repo=payload.get("repository", {}).get("full_name"))
    return {"job_id": job.id, "status": "queued"}
