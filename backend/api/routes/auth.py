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
from urllib.parse import urlencode, quote

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


def create_oauth_state(user_id: Optional[str] = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=10)
    payload = {"exp": expire}
    if user_id:
        payload["connect_user_id"] = user_id
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@router.get("/github")
async def github_login(connect: bool = False, token: Optional[str] = None):
    """Redirect user to GitHub OAuth authorization page."""
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "scope": "repo,user:email",
    }
    if connect:
        if not token:
            raise HTTPException(400, "Missing token for GitHub connect flow")
        user_id = await decode_token(f"Bearer {token}")
        params["state"] = create_oauth_state(user_id)
    return RedirectResponse(f"{GITHUB_AUTH_URL}?{urlencode(params)}")


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle GitHub OAuth callback — exchange code for token and upsert user."""
    if not code:
        return RedirectResponse(url=f"{settings.APP_URL}/auth?error=no_code", status_code=302)

    try:
        connect_user_id: Optional[str] = None
        if state:
            state_payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            connect_user_id = state_payload.get("connect_user_id")

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
            if token_resp.status_code != 200:
                error_msg = f"github_token_exchange_failed:{token_resp.status_code}"
                log.error("GitHub token exchange failed", status_code=token_resp.status_code, response=token_data)
                return RedirectResponse(
                    url=f"{settings.APP_URL}/auth?error={quote(error_msg)}",
                    status_code=302,
                )

            if "error" in token_data:
                error_msg = token_data.get("error_description") or token_data.get("error") or "github_oauth_failed"
                log.error("GitHub OAuth returned error", response=token_data)
                return RedirectResponse(
                    url=f"{settings.APP_URL}/auth?error={quote(error_msg)}",
                    status_code=302,
                )

            github_token = token_data.get("access_token")

            if not github_token:
                log.error("GitHub OAuth access token missing", response=token_data)
                return RedirectResponse(
                    url=f"{settings.APP_URL}/auth?error=no_token",
                    status_code=302,
                )

            # Fetch GitHub user profile
            user_resp = await client.get(
                f"{GITHUB_API_URL}/user",
                headers={"Authorization": f"Bearer {github_token}"},
            )
            if user_resp.status_code != 200:
                log.error("GitHub user fetch failed", status_code=user_resp.status_code, response=user_resp.text)
                return RedirectResponse(
                    url=f"{settings.APP_URL}/auth?error=failed_to_fetch_user",
                    status_code=302,
                )
            gh_user = user_resp.json()

            # Fetch primary email if not public
            email = gh_user.get("email")
            if not email:
                emails_resp = await client.get(
                    f"{GITHUB_API_URL}/user/emails",
                    headers={"Authorization": f"Bearer {github_token}"},
                )
                if emails_resp.status_code != 200:
                    log.error("GitHub emails fetch failed", status_code=emails_resp.status_code, response=emails_resp.text)
                    return RedirectResponse(
                        url=f"{settings.APP_URL}/auth?error=failed_to_fetch_email",
                        status_code=302,
                    )
                for e in emails_resp.json():
                    if e.get("primary"):
                        email = e["email"]
                        break

        if connect_user_id:
            result = await db.execute(select(User).where(User.id == connect_user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(404, "User not found for GitHub connect flow")
            user.github_token = github_token
            user.github_id = gh_user["id"]
            user.github_username = gh_user["login"]
            user.avatar_url = gh_user.get("avatar_url")
            user.name = gh_user.get("name") or user.name or gh_user["login"]
            user.email = email or user.email
        else:
            result = await db.execute(select(User).where(User.github_id == gh_user["id"]))
            user = result.scalar_one_or_none()

            if not user and email:
                email_match = await db.execute(select(User).where(User.email == email))
                user = email_match.scalar_one_or_none()

            if user:
                user.github_id = gh_user["id"]
                user.github_username = gh_user["login"]
                user.github_token = github_token
                user.avatar_url = gh_user.get("avatar_url")
                user.name = gh_user.get("name") or user.name or gh_user["login"]
                user.email = email or user.email
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

        if connect_user_id:
            redirect_url = f"{settings.APP_URL}/dashboard?github_connected=1"
        else:
            token = create_jwt(user.id)
            redirect_url = f"{settings.APP_URL}/dashboard?token={token}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        log.error("GitHub callback error", error=str(e), exc_info=True)
        return RedirectResponse(
            url=f"{settings.APP_URL}/auth?error=server_error",
            status_code=302,
        )


async def decode_token(authorization: Optional[str]) -> str:
    """Decode JWT from Authorization header. Returns user_id. Raises HTTPException on error."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated - missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token missing sub claim")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired - please log in again")
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, f"Invalid token - {str(e)}")
    except Exception as e:
        log.error("token_decode_error", error=str(e))
        raise HTTPException(401, "Invalid token")


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get authenticated user from JWT. Use this dependency in protected routes."""
    user_id = await decode_token(authorization)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Decode JWT and return current user profile."""
    return {
        "id": user.id,
        "github_username": user.github_username,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "plan": user.plan,
    }
