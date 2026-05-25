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

from api.database import get_db, User, Portfolio, BuildJob, JobStatus, GoogleResumeSync
from api.config import settings
from api.worker import run_portfolio_build
from api.models.subscription import Subscription
from api.routes.auth import get_current_user
from sqlalchemy import func
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timedelta

router = APIRouter()
log = structlog.get_logger()

# Build limits per tier (per month)
BUILD_LIMITS = {
    "free": 100,  # Increased for testing
    "pro": 30,
    "team": None,  # Unlimited
}

# Portfolio count limits per tier
PORTFOLIO_COUNT_LIMITS = {
    "free": 1,
    "pro": 10,
    "team": 100,
}

# Feature flags per tier
FEATURE_FLAGS = {
    "free": {"custom_domain": False, "analytics": False, "export": False},
    "pro": {"custom_domain": True, "analytics": True, "export": True},
    "team": {"custom_domain": True, "analytics": True, "export": True},
}


async def check_build_limit(user: User, db: AsyncSession) -> bool:
    """
    Check if user has reached their monthly build limit.
    Returns True if they can build, False if limit reached.
    """
    # Get user's plan tier
    tier = user.plan.value if user.plan else "free"
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




@router.post("/build")
async def trigger_build(
    theme: str = Form("minimal"),
    selected_repos: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None),
    user_prompt: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build portfolio synchronously (no Celery needed for MVP)."""
    try:
        # Require GitHub connection
        if not user.github_token:
            raise HTTPException(400, "Please connect your GitHub account first to build your portfolio")
        
        # ─── CHECK USER SUBSCRIPTION TIER ───
        sub_result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscription = sub_result.scalar_one_or_none()
        tier = subscription.status.value if subscription else "free"
        
        # If no subscription, they're free tier
        is_free = subscription is None
        
        # ─── FREE TIER: ONE BUILD ONLY ───
        if is_free:
            # Check if user already has a portfolio built
            result = await db.execute(
                select(Portfolio).where(Portfolio.user_id == user.id)
            )
            existing_portfolio = result.scalar_one_or_none()
            
            if existing_portfolio:
                # Free user already built once, show paywall
                raise HTTPException(
                    403,
                    detail={
                        "error": "free_tier_limit",
                        "message": "Free users can build only 1 portfolio. Upgrade to Pro to build more.",
                        "tier": "free",
                        "requires_upgrade": True
                    }
                )
        
        # ─── PRO/TEAM: CHECK MONTHLY LIMIT ───
        can_build = await check_build_limit(user, db)
        if not can_build:
            tier = user.plan.value if user.plan else "free"
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

        # ── Parse uploaded document ──────────────────────────────────────
        doc_text = ""
        if resume:
            try:
                content = await resume.read()
                filename = (resume.filename or "").lower()
                if filename.endswith(".txt"):
                    doc_text = content.decode("utf-8", errors="ignore").strip()
                elif filename.endswith(".json"):
                    import json as json_lib
                    data = json_lib.loads(content)
                    doc_text = " ".join(str(v) for v in data.values() if isinstance(v, str))[:600]
                elif filename.endswith(".pdf"):
                    try:
                        import io, pypdf
                        reader = pypdf.PdfReader(io.BytesIO(content))
                        doc_text = " ".join(p.extract_text() or "" for p in reader.pages[:3])
                    except Exception:
                        pass
                elif filename.endswith(".docx") or filename.endswith(".doc"):
                    try:
                        import io
                        from docx import Document as DocxDocument
                        doc = DocxDocument(io.BytesIO(content))
                        doc_text = " ".join(p.text for p in doc.paragraphs if p.text.strip())
                    except Exception:
                        doc_text = content.decode("utf-8", errors="ignore").strip()
            except Exception as e:
                log.warning("Failed to parse document", error=str(e))

        # ── Parse resume content from upload and/or synced Google Doc ─────
        resume_profile = {}
        if doc_text:
            try:
                from tools.resume_tool import ResumeTool
                resume_profile = await ResumeTool()._parse_text(doc_text)
            except Exception as e:
                log.warning("Failed to parse uploaded resume text", error=str(e))

        # If a Google Docs resume is connected, poll it and use it as the live source of truth.
        try:
            sync_result = await db.execute(select(GoogleResumeSync).where(GoogleResumeSync.user_id == user.id))
            google_sync = sync_result.scalar_one_or_none()
            if google_sync and google_sync.doc_id:
                from api.routes.google import _sync_resume_doc
                await _sync_resume_doc(google_sync, user, db, force=False)
                if google_sync.parsed_resume:
                    resume_profile = google_sync.parsed_resume
        except Exception as e:
            log.warning("Google resume sync skipped", error=str(e))

        # ── Build bio from prompt + document ─────────────────────────────
        prompt = (user_prompt or "").strip()
        gh_bio = ""
        gh_location = ""
        gh_company = ""
        all_languages: list = []

        # Fetch GitHub profile for richer data
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                profile_resp = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {user.github_token}"},
                    timeout=5.0,
                )
                if profile_resp.status_code == 200:
                    profile = profile_resp.json()
                    gh_bio = profile.get("bio") or ""
                    gh_location = profile.get("location") or ""
                    gh_company = profile.get("company") or ""
        except Exception:
            pass

        # ── Fetch repos ───────────────────────────────────────────────────
        repos_data = []
        selected = json.loads(selected_repos) if selected_repos else []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.github.com/user/repos",
                    headers={"Authorization": f"Bearer {user.github_token}"},
                    params={"sort": "updated", "per_page": 30, "type": "owner"},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    all_repos = [r for r in resp.json() if not r.get("fork")]
                    # Respect selected repos if provided
                    if selected:
                        filtered = [r for r in all_repos if r["full_name"] in selected]
                        if not filtered:
                            filtered = all_repos
                    else:
                        filtered = all_repos
                    # Sort by stars + recency
                    filtered.sort(key=lambda r: (r.get("stargazers_count", 0) * 2 + (1 if r.get("description") else 0)), reverse=True)
                    show_all = prompt and any(k in prompt.lower() for k in ["all my", "all github", "all projects"])
                    limit = 50 if show_all else 8
                    repos_data = [
                        {
                            "name": r["name"],
                            "description": r.get("description") or "",
                            "url": r["html_url"],
                            "stars": r.get("stargazers_count", 0),
                            "language": r.get("language"),
                        }
                        for r in filtered[:limit]
                    ]
                    all_languages = list({r["language"] for r in filtered if r.get("language")})
        except Exception as e:
            log.error("Failed to fetch repos", error=str(e))

        # ── Generate portfolio with Gemini AI ──────────────────────────────
        from api.integrations.portfolio_generator import generate_portfolio_html
        
        resume_skills = resume_profile.get("skills") or []
        combined_skills = list(dict.fromkeys([*resume_skills, *all_languages]))[:20]
        display_name = resume_profile.get("name") or user.name or user.github_username
        display_bio = resume_profile.get("summary") or gh_bio or "Software Developer"

        # Generate custom HTML portfolio based on user prompt
        portfolio_html = generate_portfolio_html(
            user_prompt=prompt,
            user_name=display_name,
            user_bio=display_bio,
            github_url=f"https://github.com/{user.github_username}",
            projects=repos_data,
            avatar_url=user.avatar_url or "",
            skills=combined_skills,
        )

        # ── Build unique accent color from username hash ───────────────────
        import hashlib
        seed = int(hashlib.md5(user.github_username.encode()).hexdigest()[:6], 16)
        accent_hues = [210, 260, 340, 160, 30, 190, 280, 15]
        accent_hue = accent_hues[seed % len(accent_hues)]

        # ── Assemble portfolio data ───────────────────────────────────────
        portfolio_data = {
            "name": display_name,
            "bio": display_bio,
            "github_url": f"https://github.com/{user.github_username}",
            "avatar_url": user.avatar_url,
            "username": user.github_username,
            "location": gh_location,
            "company": gh_company,
            "theme": theme,
            "accent_hue": accent_hue,
            "skills": combined_skills,
            "projects": repos_data,
            "resume_profile": resume_profile,
            "resume_source": "google_docs" if resume_profile and not doc_text else ("upload" if doc_text else None),
            "html": portfolio_html,  # Store Gemini-generated HTML
        }

        # Create or update portfolio
        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = result.scalar_one_or_none()

        if portfolio:
            portfolio.theme = theme
            portfolio.portfolio_data = portfolio_data
            portfolio.last_built_at = datetime.utcnow()
            flag_modified(portfolio, "portfolio_data")
        else:
            portfolio = Portfolio(
                user_id=user.id,
                slug=user.github_username or user.email.split("@")[0],
                theme=theme,
                portfolio_data=portfolio_data,
                is_published=False,  # Don't auto-publish, let user click Publish button
                site_url=None,
            )
            db.add(portfolio)
        
        job.result = {"portfolio_id": portfolio.id, "site_url": portfolio.site_url}
        await db.commit()

        return {"job_id": job.id, "status": "completed", "portfolio_id": portfolio.id}
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("Build endpoint error", error=str(e), exc_info=True)
        raise HTTPException(500, f"Build failed: {str(e)}")


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
        try:
            while True:
                try:
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

                    await asyncio.sleep(1)  # Check every 1 second
                except Exception as e:
                    log.error("Streaming error", error=str(e))
                    yield f"data: {json.dumps({'error': 'streaming failed'})}\n\n"
                    break
        except Exception as e:
            log.error("Event generator error", error=str(e))

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


@router.get("/public/{username}")
async def get_public_portfolio(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a public portfolio by username — no auth required."""
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.slug == username.lower(),
            Portfolio.is_published == True,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(404, f"Portfolio for @{username} not found")

    return {
        "id": portfolio.id,
        "slug": portfolio.slug,
        "theme": portfolio.theme,
        "last_built_at": str(portfolio.last_built_at) if portfolio.last_built_at else None,
        "portfolio_data": portfolio.portfolio_data,
    }


@router.post("/publish")
async def publish_portfolio(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish user's portfolio to make it publicly accessible."""
    try:
        from api.integrations.deployer import publish_portfolio as deploy_publish
        
        # ─── CHECK USER SUBSCRIPTION TIER ───
        sub_result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscription = sub_result.scalar_one_or_none()
        is_free = subscription is None
        
        # ─── PAYWALL: FREE USERS CANNOT PUBLISH ───
        if is_free:
            raise HTTPException(
                403,
                detail={
                    "error": "publish_requires_pro",
                    "message": "Publishing requires a Pro plan. Upgrade now to publish your portfolio.",
                    "tier": "free",
                    "requires_upgrade": True
                }
            )
        
        # Get user's current portfolio
        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise HTTPException(404, "No portfolio found. Build one first.")
        
        if not portfolio.portfolio_data or not portfolio.portfolio_data.get("html"):
            raise HTTPException(400, "Portfolio has no generated HTML. Rebuild first.")
        
        # Deploy portfolio HTML to R2 (or fallback to database)
        deployment = await deploy_publish(
            portfolio_id=str(portfolio.id),
            html_content=portfolio.portfolio_data["html"],
            username=user.github_username,
        )
        
        # Mark as published in database with deployed URL
        portfolio.is_published = True
        portfolio.site_url = deployment["site_url"]
        
        await db.commit()
        await db.refresh(portfolio)
        
        log.info("portfolio_published", user_id=user.id, portfolio_id=portfolio.id, site_url=portfolio.site_url)
        
        return {
            "status": "published",
            "site_url": portfolio.site_url,
            "public_url": portfolio.site_url,
            "message": f"Portfolio live at {portfolio.site_url}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("Portfolio publish error", error=str(e), exc_info=True)
        raise HTTPException(500, f"Failed to publish portfolio: {str(e)}")


@router.get("/repos")
async def list_repos(user: User = Depends(get_current_user)):
    """List user's GitHub repos for repo selection UI."""
    if not user.github_token:
        raise HTTPException(400, "GitHub account not connected")
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"Bearer {user.github_token}"},
                params={"sort": "updated", "per_page": 50, "type": "owner"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                log.error("GitHub API error", status=resp.status_code, body=resp.text)
                raise HTTPException(500, "Failed to fetch repos from GitHub")
            
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
    except HTTPException:
        raise
    except Exception as e:
        log.error("Error fetching repos", error=str(e))
        raise HTTPException(500, "Error fetching repos")
