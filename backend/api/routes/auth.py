"""
GitHub OAuth authentication routes
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt
from datetime import datetime, timedelta
import httpx
import structlog

from api.database import get_db, User
from api.config import settings

router = APIRouter()
log = structlog.get_logger()

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


def create_jwt(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


@router.get("/github")
async def github_login():
    """Redirect user to GitHub OAuth authorization page."""
    params = f"client_id={settings.GITHUB_CLIENT_ID}&scope=repo,user:email"
    return RedirectResponse(f"{GITHUB_AUTH_URL}?{params}")


@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handle GitHub OAuth callback — exchange code for token and upsert user."""
    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for GitHub access token
            token_resp = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                json={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                },
            )
            token_data = token_resp.json()
            github_token = token_data.get("access_token")

            if not github_token:
                raise ValueError("GitHub OAuth failed")

            # Fetch GitHub user profile
            user_resp = await client.get(
                f"{GITHUB_API_URL}/user",
                headers={"Authorization": f"Bearer {github_token}"},
            )
            gh_user = user_resp.json()

            # Fetch primary email if not public
            email = gh_user.get("email")
            if not email:
                emails_resp = await client.get(
                    f"{GITHUB_API_URL}/user/emails",
                    headers={"Authorization": f"Bearer {github_token}"},
                )
                for e in emails_resp.json():
                    if e.get("primary"):
                        email = e["email"]
                        break

        # Upsert user in DB
        result = await db.execute(select(User).where(User.github_id == gh_user["id"]))
        user = result.scalar_one_or_none()

        if user:
            user.github_token = github_token
            user.avatar_url = gh_user.get("avatar_url")
            user.name = gh_user.get("name")
            user.email = email
        else:
            user = User(
                github_id=gh_user["id"],
                github_username=gh_user["login"],
                github_token=github_token,
                email=email,
                name=gh_user.get("name") or gh_user["login"],
                avatar_url=gh_user.get("avatar_url"),
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)

        # Issue JWT and redirect to frontend
        token = create_jwt(user.id)
        redirect_url = f"{settings.APP_URL}/dashboard?token={token}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        log.error("GitHub callback error", error=str(e))
        raise HTTPException(500, f"Authentication failed: {str(e)}")


@router.get("/me")
async def get_me(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Decode JWT and return current user profile."""
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

    return {
        "id": user.id,
        "github_username": user.github_username,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "plan": user.plan,
    }
