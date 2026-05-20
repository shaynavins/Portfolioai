"""
Database models for PortfolioAI
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import enum
import uuid

from api.config import settings

Base = declarative_base()

# Async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.ENVIRONMENT == "development",
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    github_id = Column(Integer, unique=True, nullable=False, index=True)
    github_username = Column(String, nullable=False)
    github_token = Column(Text, nullable=False)       # encrypted in prod
    email = Column(String)
    name = Column(String)
    avatar_url = Column(String)
    plan = Column(Enum(PlanTier), default=PlanTier.FREE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    portfolios = relationship("Portfolio", back_populates="user")
    jobs = relationship("BuildJob", back_populates="user")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)  # username slug
    title = Column(String)
    bio = Column(Text)
    theme = Column(String, default="minimal")
    custom_domain = Column(String)
    is_published = Column(Boolean, default=False)
    site_url = Column(String)       # live URL
    vercel_project_id = Column(String)
    r2_path = Column(String)        # path in R2 bucket
    portfolio_data = Column(JSON)   # full generated portfolio JSON
    last_built_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="portfolios")
    jobs = relationship("BuildJob", back_populates="portfolio")


class BuildJob(Base):
    __tablename__ = "build_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    portfolio_id = Column(String, ForeignKey("portfolios.id"))
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    trigger = Column(String, default="manual")  # manual | webhook | scheduled
    celery_task_id = Column(String)
    progress_steps = Column(JSON, default=list)  # list of completed steps
    error = Column(Text)
    result = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="jobs")
    portfolio = relationship("Portfolio", back_populates="jobs")
