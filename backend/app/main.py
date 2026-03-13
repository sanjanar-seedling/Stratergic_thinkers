"""Seedlings API — FastAPI Application Entry Point.

The core backend for the AI Co-Founder for the Mind.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.auth import router as auth_router
from app.api.integrations import router as integrations_router
from app.core.config import get_settings
from app.core.redis_client import close_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    logger.info(f"🌱 {settings.app_name} starting up...")
    logger.info(f"   Database: {settings.database_url.split('@')[-1]}")
    logger.info(f"   Redis: {settings.redis_url}")
    logger.info(f"   LLM Provider: {settings.llm_provider}")
    yield
    logger.info("🌱 Shutting down...")
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    description="AI strategic thinking partner for founders — improving judgment quality, not output quantity.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])
app.include_router(integrations_router, prefix=f"{settings.api_prefix}/integrations", tags=["integrations"])
app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
