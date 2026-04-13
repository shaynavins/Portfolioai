"""
PortfolioAI — FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
from pathlib import Path
from fastapi.responses import HTMLResponse

from api.config import settings
from api.database import init_db
from api.routes import auth, portfolio, webhook, user

log = structlog.get_logger()
PREVIEW_DIR = Path(__file__).resolve().parents[1] / ".preview"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting PortfolioAI API", env=settings.ENVIRONMENT)
    await init_db()
    yield
    log.info("Shutting down")


app = FastAPI(
    title="PortfolioAI API",
    description="Agentic portfolio builder — GitHub to deployed site in minutes",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.APP_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(webhook.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(user.router, prefix="/api/user", tags=["user"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/preview/{slug}", response_class=HTMLResponse)
async def preview(slug: str):
    preview_file = PREVIEW_DIR / f"{slug.lower()}.html"
    if not preview_file.exists():
        raise HTTPException(404, "Preview not found")
    return HTMLResponse(preview_file.read_text(encoding="utf-8"))
