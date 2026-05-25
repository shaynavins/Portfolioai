"""Google Docs resume sync routes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from api.config import settings
from api.database import GoogleResumeSync, Portfolio, User, get_db
from api.integrations.google_docs import (
    build_google_auth_url,
    ensure_access_token,
    exchange_code,
    export_google_doc_text,
    get_file_metadata,
    list_resume_docs,
    parse_google_time,
)
from api.routes.auth import get_current_user
from tools.resume_tool import ResumeTool

router = APIRouter()
log = structlog.get_logger()


class ConnectDocRequest(BaseModel):
    doc_id: str


def _require_google_oauth_config():
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth is not configured")


def _make_state(user_id: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=15)
    return jwt.encode({"sub": user_id, "kind": "google_oauth", "exp": exp}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _decode_state(state: str) -> str:
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("kind") != "google_oauth" or not payload.get("sub"):
            raise ValueError("Invalid OAuth state")
        return payload["sub"]
    except (JWTError, ValueError):
        raise HTTPException(400, "Invalid or expired OAuth state")


async def _get_or_create_sync(db: AsyncSession, user_id: str) -> GoogleResumeSync:
    result = await db.execute(select(GoogleResumeSync).where(GoogleResumeSync.user_id == user_id))
    sync = result.scalar_one_or_none()
    if sync:
        return sync
    sync = GoogleResumeSync(user_id=user_id)
    db.add(sync)
    await db.flush()
    return sync


@router.get("/auth-url")
async def google_auth_url(user: User = Depends(get_current_user)):
    """Return a Google OAuth URL for the logged-in user."""
    _require_google_oauth_config()
    return {"url": build_google_auth_url(_make_state(user.id))}


@router.get("/callback")
async def google_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback, store tokens, then return to dashboard."""
    _require_google_oauth_config()
    user_id = _decode_state(state)
    try:
        token_data = await exchange_code(code)
        sync = await _get_or_create_sync(db, user_id)
        sync.google_access_token = token_data["access_token"]
        # Google only sends a refresh token on first consent or prompt=consent.
        if token_data.get("refresh_token"):
            sync.google_refresh_token = token_data["refresh_token"]
        sync.google_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
        await db.commit()
        return RedirectResponse(f"{settings.APP_URL.rstrip('/')}/dashboard?google=connected", status_code=302)
    except Exception as e:
        await db.rollback()
        log.error("google_oauth_callback_failed", error=str(e), user_id=user_id)
        return RedirectResponse(f"{settings.APP_URL.rstrip('/')}/dashboard?google=error", status_code=302)


@router.get("/status")
async def google_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GoogleResumeSync).where(GoogleResumeSync.user_id == user.id))
    sync = result.scalar_one_or_none()
    if not sync or not sync.google_refresh_token:
        return {"connected": False, "doc": None}
    return {
        "connected": True,
        "doc": None if not sync.doc_id else {
            "id": sync.doc_id,
            "name": sync.doc_name,
            "url": sync.doc_url,
            "modified_time": sync.doc_modified_time,
            "last_synced_at": sync.last_synced_at,
        },
    }


@router.get("/docs")
async def google_docs(
    q: Optional[str] = Query(None, description="Search Google Docs by document name"),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List/search Google Docs so the user can pick their live resume document."""
    result = await db.execute(select(GoogleResumeSync).where(GoogleResumeSync.user_id == user.id))
    sync = result.scalar_one_or_none()
    if not sync or not sync.google_refresh_token:
        raise HTTPException(400, "Connect Google Docs first")
    access_token = await ensure_access_token(sync)
    files = await list_resume_docs(access_token, page_size=page_size, name_query=q)
    await db.commit()
    return {"docs": files, "query": q or "", "page_size": page_size}


@router.post("/resume-doc")
async def connect_resume_doc(payload: ConnectDocRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Attach a Google Doc as the user's resume source of truth and sync it once."""
    sync = await _get_or_create_sync(db, user.id)
    if not sync.google_refresh_token:
        raise HTTPException(400, "Connect Google Docs first")
    access_token = await ensure_access_token(sync)
    meta = await get_file_metadata(access_token, payload.doc_id)
    if meta.get("mimeType") != "application/vnd.google-apps.document":
        raise HTTPException(400, "Selected file is not a Google Doc")

    sync.doc_id = meta["id"]
    sync.doc_name = meta.get("name")
    sync.doc_url = meta.get("webViewLink")
    sync.doc_modified_time = parse_google_time(meta.get("modifiedTime"))
    await _sync_resume_doc(sync, user, db, force=True)
    await db.commit()
    return {"status": "connected", "doc": {"id": sync.doc_id, "name": sync.doc_name, "url": sync.doc_url}}


@router.post("/sync")
async def sync_resume(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), force: bool = False):
    """Poll the selected Google Doc; if edited, fetch text and update parsed portfolio resume data."""
    result = await db.execute(select(GoogleResumeSync).where(GoogleResumeSync.user_id == user.id))
    sync = result.scalar_one_or_none()
    if not sync or not sync.doc_id:
        raise HTTPException(400, "No Google resume doc connected")
    changed = await _sync_resume_doc(sync, user, db, force=force)
    await db.commit()
    return {"status": "synced" if changed else "unchanged", "doc_modified_time": sync.doc_modified_time, "last_synced_at": sync.last_synced_at, "parsed_resume": sync.parsed_resume}


async def _sync_resume_doc(sync: GoogleResumeSync, user: User, db: AsyncSession, force: bool = False) -> bool:
    access_token = await ensure_access_token(sync)
    meta = await get_file_metadata(access_token, sync.doc_id)
    modified = parse_google_time(meta.get("modifiedTime"))

    if not force and sync.doc_modified_time and modified and modified <= sync.doc_modified_time:
        return False

    text = await export_google_doc_text(access_token, sync.doc_id)
    parsed = await ResumeTool()._parse_text(text)

    sync.doc_name = meta.get("name") or sync.doc_name
    sync.doc_url = meta.get("webViewLink") or sync.doc_url
    sync.doc_modified_time = modified
    sync.last_synced_at = datetime.now(timezone.utc)
    sync.last_resume_text = text
    sync.parsed_resume = parsed
    flag_modified(sync, "parsed_resume")

    # Persist parsed resume into existing portfolio data so future AI/builds can use it.
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))
    portfolio = result.scalar_one_or_none()
    if portfolio:
        data = dict(portfolio.portfolio_data or {})
        data["resume_source"] = "google_docs"
        data["resume_doc"] = {"id": sync.doc_id, "name": sync.doc_name, "url": sync.doc_url}
        data["resume_profile"] = parsed
        if parsed.get("name"):
            data["name"] = parsed["name"]
        if parsed.get("summary"):
            data["bio"] = parsed["summary"]
        if parsed.get("skills"):
            existing = data.get("skills") or []
            if isinstance(existing, dict):
                existing = [*(existing.get("languages") or []), *(existing.get("frameworks") or [])]
            data["skills"] = list(dict.fromkeys([*(existing or []), *parsed["skills"]]))[:20]
        portfolio.portfolio_data = data
        flag_modified(portfolio, "portfolio_data")

    log.info("google_resume_synced", user_id=user.id, doc_id=sync.doc_id, chars=len(text))
    return True
