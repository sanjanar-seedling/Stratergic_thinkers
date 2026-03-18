"""Seedlings API — FastAPI Application Entry Point.

The core backend for the AI Co-Founder for the Mind.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.auth import router as auth_router
from app.api.integrations import router as integrations_router
from app.core.config import get_settings
from app.core.redis_client import close_redis
from app.services.event_processor import EventProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# Global event processor instance
_event_processor = None
_processor_task = None


async def start_event_processor():
    """Start the event processor as a background task."""
    global _event_processor, _processor_task
    try:
        _event_processor = EventProcessor(
            redis_url=settings.redis_url,
            stream_name=settings.redis_stream_name,
            consumer_group="seedlings-processors",
            consumer_name="processor-1",
        )
        _processor_task = asyncio.create_task(_event_processor.process_stream())
        logger.info("✅ Event processor started")
    except Exception as e:
        logger.error(f"Failed to start event processor: {e}", exc_info=True)


async def stop_event_processor():
    """Stop the event processor."""
    global _processor_task
    if _processor_task:
        _processor_task.cancel()
        try:
            await _processor_task
        except asyncio.CancelledError:
            logger.info("✅ Event processor stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    logger.info(f"🌱 {settings.app_name} starting up...")
    logger.info(f"   Database: {settings.database_url.split('@')[-1]}")
    logger.info(f"   Redis: {settings.redis_url}")
    logger.info(f"   LLM Provider: {settings.llm_provider}")
    
    # Start background services
    await start_event_processor()
    
    yield
    
    logger.info("🌱 Shutting down...")
    await stop_event_processor()
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
