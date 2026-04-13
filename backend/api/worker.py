"""
Celery worker — async job execution
Dispatches the LangGraph portfolio build agent
"""
from celery import Celery
from kombu import Queue
from pathlib import Path
import sys
from api.config import settings
import structlog
import asyncio

log = structlog.get_logger()

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

celery_app = Celery(
    "portfolioai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_default_queue="builds",
    task_queues=(Queue("builds"),),
    task_create_missing_queues=True,
    task_routes={
        "api.worker.run_portfolio_build": {"queue": "builds"},
    },
)


@celery_app.task(bind=True, name="api.worker.run_portfolio_build", max_retries=2)
def run_portfolio_build(self, job_id: str, user_id: str, **kwargs):
    """
    Main Celery task — runs the LangGraph agent synchronously.
    The agent does all the heavy lifting: GitHub data fetch,
    AI content generation, site build, and deployment.
    """
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from agents.portfolio_agent import PortfolioAgent
    from api.database import BuildJob, JobStatus
    from api.config import settings
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    async def _run():
        engine = create_async_engine(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            echo=settings.ENVIRONMENT == "development",
        )
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with session_factory() as db:
            # Mark job as running
            result = await db.execute(select(BuildJob).where(BuildJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                await engine.dispose()
                return

            job.status = JobStatus.RUNNING
            await db.commit()

            try:
                agent = PortfolioAgent(
                    job_id=job_id,
                    user_id=user_id,
                    db=db,
                    **kwargs,
                )
                result_data = await agent.run()

                job.status = JobStatus.COMPLETED
                job.result = result_data
            except Exception as e:
                log.error("Build failed", job_id=job_id, error=str(e))
                job.status = JobStatus.FAILED
                job.error = str(e)

            await db.commit()
        await engine.dispose()

    asyncio.run(_run())


# Re-export for import compatibility
run_portfolio_build = celery_app.tasks["api.worker.run_portfolio_build"]
