"""
Simple Email/Password Auth
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import jwt
import uuid
from typing import Optional

from api.database import get_db, User
from api.config import settings
from api.auth.password import hash_password, verify_password

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_jwt(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


@router.post("/signup", response_model=TokenResponse)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Create an email/password account."""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")
    
    # Create user (no GitHub)
    user = User(
        id=str(uuid.uuid4()),
        github_id=None,
        github_username=req.email.split("@")[0],
        github_token=None,
        password_hash=hash_password(req.password),
        email=req.email,
        name=req.name,
        avatar_url=None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    token = create_jwt(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate an email/password account."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise HTTPException(401, "Invalid email or password")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    
    token = create_jwt(user.id)
    return TokenResponse(access_token=token)


class GitHubOAuthRequest(BaseModel):
    code: str  # GitHub OAuth code from callback


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get authenticated user from JWT token."""
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


@router.get("/github/legacy-callback")
async def github_oauth_callback(
    code: str,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """GitHub OAuth callback - exchange code for token and create/update user."""
    from fastapi.responses import RedirectResponse
    import httpx
    
    if not code:
        return RedirectResponse(url=f"{settings.APP_URL}/auth?error=no_code", status_code=302)
    
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            
            token_data = token_resp.json()
            if token_resp.status_code != 200:
                error_msg = f"GitHub returned {token_resp.status_code}: {token_data}"
                return RedirectResponse(url=f"{settings.APP_URL}/auth?error={error_msg}", status_code=302)
            
            if "error" in token_data:
                error_msg = token_data.get('error_description', token_data.get('error'))
                return RedirectResponse(url=f"{settings.APP_URL}/auth?error={error_msg}", status_code=302)
            
            access_token = token_data.get("access_token")
            if not access_token:
                return RedirectResponse(url=f"{settings.APP_URL}/auth?error=no_token", status_code=302)
            
            # Get user info from GitHub
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if user_resp.status_code != 200:
                return RedirectResponse(url=f"{settings.APP_URL}/auth?error=failed_to_fetch_user", status_code=302)
            
            github_user = user_resp.json()
        
        github_id = github_user["id"]
        github_username = github_user["login"]
        github_email = github_user.get("email")
        
        # Check if user already exists with this GitHub ID
        result = await db.execute(select(User).where(User.github_id == github_id))
        user = result.scalar_one_or_none()
        
        if user:
            # Update existing user with latest GitHub info
            user.github_token = access_token
            user.avatar_url = github_user.get("avatar_url")
        else:
            # Create new user
            user = User(
                id=str(uuid.uuid4()),
                github_id=github_id,
                github_username=github_username,
                github_token=access_token,
                email=github_email or f"{github_username}@github.local",
                name=github_user.get("name") or github_username,
                avatar_url=github_user.get("avatar_url"),
            )
            db.add(user)
        
        await db.commit()
        await db.refresh(user)
        
        # Create JWT token
        token = create_jwt(user.id)
        
        # Redirect to dashboard with token in URL
        return RedirectResponse(url=f"{settings.APP_URL}/dashboard?token={token}", status_code=302)
    
    except Exception as e:
        return RedirectResponse(url=f"{settings.APP_URL}/auth?error=server_error", status_code=302)


@router.get("/session/me")
async def get_me(
    user: User = Depends(get_current_user),
):
    """Get current authenticated user info."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "github_id": user.github_id,
        "github_username": user.github_username,
        "avatar_url": user.avatar_url,
        "plan": user.plan,
    }



@router.post("/github/connect")
async def connect_github(
    req: GitHubOAuthRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect existing user to GitHub account."""
    import httpx
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": req.code,
            },
            headers={"Accept": "application/json"},
        )
        
        if token_resp.status_code != 200:
            raise HTTPException(400, "Failed to exchange GitHub code for token")
        
        token_data = token_resp.json()
        if "error" in token_data:
            raise HTTPException(400, f"GitHub error: {token_data.get('error_description')}")
        
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, "No access token received from GitHub")
        
        # Get user info from GitHub
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if user_resp.status_code != 200:
            raise HTTPException(400, "Failed to fetch GitHub user info")
        
        github_user = user_resp.json()
    
    # Update user with GitHub info
    user.github_id = github_user["id"]
    user.github_username = github_user["login"]
    user.github_token = access_token
    user.avatar_url = github_user.get("avatar_url")
    
    await db.commit()
    await db.refresh(user)
    
    return {
        "success": True,
        "github_username": user.github_username,
        "message": "GitHub account connected successfully",
    }
