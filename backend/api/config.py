from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # App
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"
    PORTFOLIO_BASE_DOMAIN: str = "portfolioai.app"

    # Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    # GitHub
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Gemini
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_FAST_MODEL: str = "gemini-2.5-flash"

    # R2 Storage
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "portfolioai-sites"
    R2_PUBLIC_URL: str = ""

    # Vercel
    VERCEL_TOKEN: str = ""
    VERCEL_TEAM_ID: str = ""

@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
