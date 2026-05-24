"""
Security Configuration
CORS, CSRF, security headers, and rate limiting setup
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
from urllib.parse import urlparse

from api.config import settings, Environment

log = structlog.get_logger()


def setup_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware.
    In production, only allow specific origins.
    In development, allow localhost.
    """
    origins = settings.ALLOWED_ORIGINS
    
    if settings.ENVIRONMENT == Environment.PRODUCTION:
        # Production: strict CORS based on configured public URLs.
        origins = list(dict.fromkeys([
            *settings.ALLOWED_ORIGINS,
            settings.APP_URL,
            settings.API_URL,
        ]))
    elif settings.ENVIRONMENT == Environment.DEVELOPMENT:
        # Development: allow localhost on any port
        origins = [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8000",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:8000",
        ]
    
    log.info("CORS configured", environment=settings.ENVIRONMENT, origins=origins)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,  # 24 hours
    )


def setup_trusted_hosts(app: FastAPI) -> None:
    """
    Prevent Host header attacks.
    Only allow requests to specific domains.
    """
    # Railway health checks can arrive with an internal Host header that does not
    # match the public domain. Enforcing TrustedHostMiddleware here causes the
    # service to fail health checks even though the app is healthy.
    if settings.ENVIRONMENT != Environment.DEVELOPMENT:
        log.info("Trusted host middleware disabled for deployment compatibility")
        return

    allowed_hosts = {
        "localhost",
        "localhost:8000",
        "127.0.0.1",
        "api.portfolioai.app",
    }

    for public_url in (settings.APP_URL, settings.API_URL):
        if public_url:
            hostname = urlparse(public_url).hostname or public_url
            if hostname:
                allowed_hosts.add(hostname)
    
    log.info("Trusted hosts configured", hosts=sorted(allowed_hosts))
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=sorted(allowed_hosts),
    )


def add_security_headers(app: FastAPI) -> None:
    """
    Add HTTP security headers to all responses.
    """
    @app.middleware("http")
    async def add_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (strict)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.github.com https://api.stripe.com; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HTTPS enforcement
        if settings.REQUIRE_HTTPS and settings.ENVIRONMENT == Environment.PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


def setup_https_redirect(app: FastAPI) -> None:
    """
    Redirect HTTP to HTTPS in production.
    """
    @app.middleware("http")
    async def https_redirect(request: Request, call_next):
        if settings.REQUIRE_HTTPS and settings.ENVIRONMENT == Environment.PRODUCTION:
            if request.url.scheme == "http":
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=url, status_code=301)
        return await call_next(request)


class RateLimitStore:
    """Simple in-memory rate limit store. For production, use Redis."""
    def __init__(self):
        self.requests = {}  # {user_id: [timestamps]}
    
    def is_allowed(self, user_id: str, limit: int, window_seconds: int = 60) -> bool:
        """Check if user is within rate limit."""
        import time
        now = time.time()
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests outside window
        self.requests[user_id] = [t for t in self.requests[user_id] if now - t < window_seconds]
        
        if len(self.requests[user_id]) < limit:
            self.requests[user_id].append(now)
            return True
        return False


# Global rate limit store
rate_limit_store = RateLimitStore()


async def check_rate_limit(user_id: str, tier: str = "free") -> None:
    """
    Check if user has exceeded rate limit.
    Raises HTTPException if limit exceeded.
    """
    if not settings.RATE_LIMIT_ENABLED:
        return
    
    limit_map = {
        "free": settings.RATE_LIMIT_FREE_TIER,
        "pro": settings.RATE_LIMIT_PRO_TIER,
        "team": settings.RATE_LIMIT_TEAM_TIER,
    }
    limit = limit_map.get(tier, 100)
    
    if limit == 0:  # unlimited
        return
    
    if not rate_limit_store.is_allowed(user_id, limit, window_seconds=60):
        log.warning("Rate limit exceeded", user_id=user_id, tier=tier)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"},
        )
