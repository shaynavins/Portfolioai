"""Input Validation Schemas
Pydantic models for all API requests and responses
"""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


# ─── Auth Requests ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Email + password login."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """User registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="At least 8 characters")
    name: Optional[str] = Field(None, max_length=255)


class RefreshTokenRequest(BaseModel):
    """Request new access token using refresh token."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout and revoke tokens."""
    refresh_token: Optional[str] = None


# ─── Auth Responses ──────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Auth token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds


class UserResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    name: Optional[str]
    github_username: Optional[str]
    avatar_url: Optional[str]
    subscription_tier: str = "free"
    created_at: datetime
    updated_at: datetime


# ─── Portfolio Requests ──────────────────────────────────────────────────────

class PortfolioBuildRequest(BaseModel):
    """Trigger a portfolio build."""
    theme: str = Field("minimal", pattern="^(minimal|dark|creative)$")
    selected_repos: Optional[List[str]] = Field(
        None,
        description="List of repo full names (owner/repo) to feature"
    )


class PortfolioUpdateRequest(BaseModel):
    """Update portfolio settings."""
    theme: Optional[str] = Field(None, pattern="^(minimal|dark|creative)$")
    custom_domain: Optional[str] = None
    is_published: Optional[bool] = None

    @field_validator("custom_domain")
    @classmethod
    def validate_domain(cls, v):
        if v and not (3 < len(v) < 256 and "." in v):
            raise ValueError("Invalid domain")
        return v


# ─── Portfolio Responses ─────────────────────────────────────────────────────

class PortfolioResponse(BaseModel):
    """Portfolio data."""
    id: str
    user_id: str
    slug: str
    site_url: Optional[str]
    theme: str
    is_published: bool
    last_built_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class BuildJobResponse(BaseModel):
    """Build job status."""
    job_id: str
    status: str  # pending, running, completed, failed
    progress_steps: List[str] = []
    error: Optional[str] = None
    result: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


# ─── Error Responses ─────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    code: str
    trace_id: Optional[str] = None
    details: Optional[dict] = None


class ValidationErrorResponse(BaseModel):
    """Validation error with field details."""
    error: str
    code: str = "validation_error"
    fields: List[dict]  # [{field: str, message: str}]


# ─── Health Check ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
