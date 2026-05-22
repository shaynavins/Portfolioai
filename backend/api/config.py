"""PortfolioAI Configuration - Production Grade
Loads all settings from environment variables with validation"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────────────────────────────
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"
    PORTFOLIO_BASE_DOMAIN: str = "portfolioai.app"
    DEBUG: bool = True

    # ─── Security & Secrets ────────────────────────────────────────────────────
    JWT_SECRET: str  # Required in production
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15  # Short-lived access token
    JWT_REFRESH_EXPIRE_DAYS: int = 30  # Longer-lived refresh token
    
    # HTTPS enforcement
    REQUIRE_HTTPS: bool = True
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000"]
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_FREE_TIER: int = 100  # req/min
    RATE_LIMIT_PRO_TIER: int = 500
    RATE_LIMIT_TEAM_TIER: int = 0  # unlimited

    # ─── GitHub OAuth ─────────────────────────────────────────────────────────
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_WEBHOOK_SECRET: str = ""

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # ─── Redis/Cache ──────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # ─── Celery/Job Queue ─────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_TIMEOUT: int = 600

    # ─── AI / Gemini ──────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_FAST_MODEL: str = "gemini-2.5-flash"

    # ─── Object Storage (Cloudflare R2) ────────────────────────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "portfolioai-sites"
    R2_PUBLIC_URL: str = ""

    # ─── Vercel Deployment ────────────────────────────────────────────────────
    VERCEL_TOKEN: str = ""
    VERCEL_TEAM_ID: str = ""

    # ─── Razorpay / Payments ─────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    
    # ─── Stripe / Payments (deprecated, use Razorpay) ────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRODUCT_ID_PRO: str = ""
    STRIPE_PRODUCT_ID_TEAM: str = ""

    # ─── Email / SendGrid ─────────────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@portfolioai.app"
    SENDGRID_FROM_NAME: str = "PortfolioAI"

    # ─── Monitoring / Error Tracking ──────────────────────────────────────────
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    
    # ─── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # ─── Tier-based Limits ────────────────────────────────────────────────────
    PORTFOLIO_LIMIT_FREE: int = 1
    PORTFOLIO_LIMIT_PRO: int = 10
    PORTFOLIO_LIMIT_TEAM: int = 100
    
    UPDATE_CADENCE_FREE_HOURS: int = 24
    UPDATE_CADENCE_PRO_HOURS: int = 0
    UPDATE_CADENCE_TEAM_HOURS: int = 0
    
    CUSTOM_DOMAIN_ENABLED_FREE: bool = False
    CUSTOM_DOMAIN_ENABLED_PRO: bool = True
    CUSTOM_DOMAIN_ENABLED_TEAM: bool = True

    # ─── Feature Flags ────────────────────────────────────────────────────────
    FEATURE_EMAIL_NOTIFICATIONS: bool = True
    FEATURE_WEBHOOKS: bool = True
    FEATURE_ANALYTICS: bool = False
    FEATURE_WHITE_LABEL: bool = False


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton for settings. Call once at startup."""
    return Settings()


settings = get_settings()


def validate_production_settings() -> None:
    """Validate all required settings for production. Call in main.py on startup."""
    if settings.ENVIRONMENT == Environment.PRODUCTION:
        required = [
            "JWT_SECRET",
            "GITHUB_CLIENT_ID",
            "GITHUB_CLIENT_SECRET",
            "GITHUB_WEBHOOK_SECRET",
            "DATABASE_URL",
            "GOOGLE_API_KEY",
        ]
        missing = [field for field in required if not getattr(settings, field)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
