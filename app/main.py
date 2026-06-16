"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import router, health_router
from app.exceptions import AppException
from app.database.base import engine, Base
from app.core import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("🚀 Application starting up...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database initialized")
    yield
    # Shutdown
    logger.info("🛑 Application shutting down...")
    await engine.dispose()
    logger.info("✅ Application shutdown complete")


app = FastAPI(
    title="HelpDesk Bot API",
    description="Automated helpdesk ticket management system",
    version="0.1.0",
    lifespan=lifespan,
)


# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    """Handle application exceptions."""
    logger.error(f"Application error: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.code,
            "detail": exc.message,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors."""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "detail": str(exc),
        },
    )


# Include routers
app.include_router(health_router)
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "HelpDesk Bot API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
