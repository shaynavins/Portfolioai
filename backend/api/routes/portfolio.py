"""
Portfolio routes — trigger builds, stream progress, get portfolio data
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Header, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json
import asyncio
import structlog

from api.database import get_db, User, Portfolio, BuildJob, JobStatus
from api.config import settings
from api.worker import run_portfolio_build

router = APIRouter()
log = structlog.get_logger()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    from jose import jwt
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(401, "Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.post("/build")
async def trigger_build(
    theme: str = Form("minimal"),
    selected_repos: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new portfolio build job."""
    parsed_selected_repos = None
    if selected_repos:
        try:
            parsed_selected_repos = json.loads(selected_repos)
        except json.JSONDecodeError:
            raise HTTPException(422, "selected_repos must be valid JSON")

    # Read resume bytes if provided
    resume_bytes = None
    resume_filename = None
    if resume:
        resume_bytes = await resume.read()
        resume_filename = resume.filename

    # Create job record
    job = BuildJob(
        user_id=user.id,
        status=JobStatus.PENDING,
        trigger="manual",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch to Celery
    task = run_portfolio_build.delay(
        job_id=job.id,
        user_id=user.id,
        github_token=user.github_token,
        github_username=user.github_username,
        theme=theme,
        selected_repos=parsed_selected_repos,
        resume_bytes=resume_bytes,
        resume_filename=resume_filename,
    )

    # Store celery task id
    job.celery_task_id = task.id
    await db.commit()

    return {"job_id": job.id, "status": "pending"}


@router.get("/build/{job_id}/status")
async def get_build_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current status of a build job."""
    result = await db.execute(
        select(BuildJob).where(BuildJob.id == job_id, BuildJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "progress_steps": job.progress_steps or [],
        "error": job.error,
        "result": job.result,
    }


@router.get("/build/{job_id}/stream")
async def stream_build_progress(
    job_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """SSE stream for real-time build progress updates."""
    async def event_generator():
        while True:
            result = await db.execute(select(BuildJob).where(BuildJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                yield f"data: {json.dumps({'error': 'job not found'})}\n\n"
                break

            yield f"data: {json.dumps({'status': job.status, 'steps': job.progress_steps or []})}\n\n"

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                if job.status == JobStatus.COMPLETED:
                    yield f"data: {json.dumps({'status': 'completed', 'result': job.result})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'failed', 'error': job.error})}\n\n"
                break

            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/me")
async def get_my_portfolio(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's current portfolio."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"portfolio": None}

    return {
        "portfolio": {
            "id": portfolio.id,
            "slug": portfolio.slug,
            "site_url": portfolio.site_url,
            "is_published": portfolio.is_published,
            "theme": portfolio.theme,
            "last_built_at": portfolio.last_built_at,
            "portfolio_data": portfolio.portfolio_data,
        }
    }


@router.get("/repos")
async def list_repos(user: User = Depends(get_current_user)):
    """List user's GitHub repos for repo selection UI."""
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {user.github_token}"},
            params={"sort": "updated", "per_page": 50, "type": "owner"},
        )
        repos = resp.json()

    return {
        "repos": [
            {
                "full_name": r["full_name"],
                "name": r["name"],
                "description": r.get("description"),
                "language": r.get("language"),
                "stars": r.get("stargazers_count", 0),
                "updated_at": r.get("updated_at"),
                "url": r.get("html_url"),
            }
            for r in repos
            if not r.get("fork")
        ]
    }
