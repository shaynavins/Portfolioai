"""
PortfolioAI — FastAPI Backend
Main application entry point with production-grade security
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import structlog
import uuid
from pathlib import Path

from api.config import settings, validate_production_settings, Environment
from api.database import init_db
from api.routes import auth, portfolio, webhook, user, billing, simple_auth
from api.security import setup_cors, setup_trusted_hosts, add_security_headers
from api.validation import ErrorResponse, HealthResponse

log = structlog.get_logger()
PREVIEW_DIR = Path(__file__).resolve().parents[1] / ".preview"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    log.info(
        "Starting PortfolioAI API",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
    )
    
    # Validate production settings
    if settings.ENVIRONMENT == Environment.PRODUCTION:
        try:
            validate_production_settings()
        except ValueError as e:
            log.error("Production settings validation failed", error=str(e))
            raise
    
    # Initialize database
    await init_db()
    log.info("Database initialized")
    
    yield
    log.info("Shutting down PortfolioAI API")


# Create FastAPI app
app = FastAPI(
    title="PortfolioAI API",
    description="Agentic portfolio builder — GitHub to deployed site in minutes",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Setup security middleware (MUST be before routes)
setup_cors(app)
add_security_headers(app)
# Don't setup trusted hosts in development
if not settings.DEBUG:
    setup_trusted_hosts(app)


# Global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured validation error response."""
    trace_id = str(uuid.uuid4())
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"][1:]),
            "message": error["msg"],
        })
    log.warning(
        "Validation error",
        trace_id=trace_id,
        path=request.url.path,
        errors=errors,
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "code": "validation_error",
            "trace_id": trace_id,
            "details": {"fields": errors},
        },
    )


# Global exception handler for HTTP exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return structured HTTP error response."""
    trace_id = str(uuid.uuid4())
    log.warning(
        "HTTP exception",
        trace_id=trace_id,
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": f"http_{exc.status_code}",
            "trace_id": trace_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unexpected exceptions with path context."""
    trace_id = str(uuid.uuid4())
    log.error(
        "Unhandled exception",
        trace_id=trace_id,
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "internal_server_error",
            "trace_id": trace_id,
        },
    )


# Mount routers
app.include_router(simple_auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])  # GitHub auth
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(webhook.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
    ).model_dump()


@app.get("/preview/{slug}", response_class=HTMLResponse)
async def preview(slug: str):
    """Serve development portfolio preview."""
    preview_file = PREVIEW_DIR / f"{slug.lower()}.html"
    if not preview_file.exists():
        raise HTTPException(404, "Preview not found")
    return HTMLResponse(preview_file.read_text(encoding="utf-8"))
