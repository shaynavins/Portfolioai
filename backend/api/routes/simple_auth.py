"""
Simple Email/Password Auth (No GitHub dependency)
For testing and MVP phase
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
    """Simple email/password signup."""
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
    """Simple email/password login."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    
    if not user:
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
