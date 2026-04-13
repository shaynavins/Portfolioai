"""User settings routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db

router = APIRouter()

@router.get("/webhook-url")
async def get_webhook_url(authorization: str = None):
    """Returns the user's personal webhook URL for GitHub."""
    from jose import jwt
    from api.config import settings
    if not authorization:
        from fastapi import HTTPException
        raise HTTPException(401, "Not authenticated")
    token = authorization.split(" ")[-1]
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    user_id = payload["sub"]
    return {
        "webhook_url": f"{settings.API_URL}/api/webhooks/github/{user_id}",
        "events": ["push"],
        "content_type": "application/json",
    }
