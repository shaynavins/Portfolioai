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
from api.models.subscription import Subscription
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter()
log = structlog.get_logger()

# Build limits per tier (per month)
BUILD_LIMITS = {
    "free": 3,
    "pro": 50,
    "team": None,  # Unlimited
}


async def check_build_limit(user: User, db: AsyncSession) -> bool:
    """
    Check if user has reached their monthly build limit.
    Returns True if they can build, False if limit reached.
    """
    # Get user's subscription tier
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    tier = subscription.tier if subscription else "free"
    limit = BUILD_LIMITS.get(tier, BUILD_LIMITS["free"])
    
    # Unlimited tier
    if limit is None:
        return True
    
    # Count builds this month
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    count_result = await db.execute(
        select(func.count(BuildJob.id)).where(
            BuildJob.user_id == user.id,
            BuildJob.created_at >= month_start,
            BuildJob.status != JobStatus.FAILED,  # Don't count failed builds
        )
    )
    build_count = count_result.scalar() or 0
    
    return build_count < limit


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
    """Build portfolio synchronously (no Celery needed for MVP)."""
    # Require GitHub connection
    if not user.github_token:
        raise HTTPException(400, "Please connect your GitHub account first to build your portfolio")
    
    # Check build limit
    can_build = await check_build_limit(user, db)
    if not can_build:
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscription = result.scalar_one_or_none()
        tier = subscription.tier if subscription else "free"
        limit = BUILD_LIMITS.get(tier, BUILD_LIMITS["free"])
        
        raise HTTPException(
            429,
            f"Build limit reached for {tier} plan ({limit} per month). Upgrade your plan to build more portfolios."
        )
    
    # Create job record
    job = BuildJob(
        user_id=user.id,
        status=JobStatus.COMPLETED,  # Mark as completed immediately
        trigger="manual",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Create simple portfolio data immediately
    portfolio_data = {
        "name": user.name or user.github_username,
        "bio": "Developer | Building awesome projects",
        "github_url": f"https://github.com/{user.github_username}",
        "theme": theme,
        "projects": [],
        "skills": [],
    }
    
    # Try to fetch GitHub repos if GitHub token available
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"Bearer {user.github_token}"},
                params={"sort": "updated", "per_page": 10, "type": "owner"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                repos = resp.json()
                portfolio_data["projects"] = [
                    {
                        "name": r["name"],
                        "description": r.get("description", ""),
                        "url": r["html_url"],
                        "stars": r.get("stargazers_count", 0),
                        "language": r.get("language"),
                    }
                    for r in repos[:5] if not r.get("fork")
                ]
    except Exception as e:
        log.error("Failed to fetch repos", error=str(e))
    
    # Create or update portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    
    if portfolio:
        portfolio.theme = theme
        portfolio.portfolio_data = portfolio_data
        portfolio.last_built_at = datetime.utcnow()
    else:
        portfolio = Portfolio(
            user_id=user.id,
            slug=user.github_username or user.email.split("@")[0],
            theme=theme,
            portfolio_data=portfolio_data,
            is_published=True,
            site_url=f"https://portfolio.local/{user.github_username or user.id}",
        )
        db.add(portfolio)
    
    job.result = {"portfolio_id": portfolio.id, "site_url": portfolio.site_url}
    await db.commit()

    return {"job_id": job.id, "status": "completed", "portfolio_id": portfolio.id}


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
