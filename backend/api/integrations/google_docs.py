"""Google OAuth + Drive/Docs helpers for resume Google Docs sync."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

from api.config import settings

log = structlog.get_logger()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_API = "https://www.googleapis.com/drive/v3"
DOCS_API = "https://docs.googleapis.com/v1/documents"
SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]


def google_redirect_uri() -> str:
    return f"{settings.API_URL.rstrip('/')}/api/google/callback"


def build_google_auth_url(state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": google_redirect_uri(),
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def ensure_access_token(sync) -> str:
    expires_at = sync.google_token_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if sync.google_access_token and expires_at and expires_at > datetime.now(timezone.utc) + timedelta(minutes=2):
        return sync.google_access_token

    if not sync.google_refresh_token:
        raise ValueError("Google refresh token missing; reconnect Google Docs")

    token_data = await refresh_access_token(sync.google_refresh_token)
    sync.google_access_token = token_data["access_token"]
    sync.google_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
    return sync.google_access_token


def _escape_drive_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


async def list_resume_docs(access_token: str, page_size: int = 50, name_query: str | None = None) -> list[dict[str, Any]]:
    query = "mimeType='application/vnd.google-apps.document' and trashed=false"
    if name_query and name_query.strip():
        query += f" and name contains '{_escape_drive_query_value(name_query.strip())}'"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{DRIVE_API}/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "q": query,
                "pageSize": page_size,
                "orderBy": "modifiedTime desc",
                "fields": "files(id,name,modifiedTime,webViewLink,mimeType)",
            },
        )
        resp.raise_for_status()
        files = resp.json().get("files", [])
    return files


async def get_file_metadata(access_token: str, doc_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{DRIVE_API}/files/{doc_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "id,name,modifiedTime,webViewLink,mimeType"},
        )
        resp.raise_for_status()
        return resp.json()


async def export_google_doc_text(access_token: str, doc_id: str) -> str:
    # Drive export gives cleaner plain text than manually walking Docs structural elements.
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{DRIVE_API}/files/{doc_id}/export",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"mimeType": "text/plain"},
        )
        resp.raise_for_status()
        return resp.text


def parse_google_time(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
