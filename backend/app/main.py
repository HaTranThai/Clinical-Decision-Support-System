"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import auth, users, sessions, alerts, settings as settings_route, analytics, health, mlops as mlops_route
from app.api.ws.live import router as ws_router
from app.services.kafka_consumer import KafkaConsumerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("backend")

kafka_consumer_service = KafkaConsumerService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up ECG CDSS Backend...")
    # Start Kafka consumer in background
    kafka_consumer_service.start()
    yield
    logger.info("Shutting down...")
    kafka_consumer_service.stop()


app = FastAPI(
    title="ECG Real-time CDSS API",
    description="Real-time Clinical Decision Support System for ECG Arrhythmia Detection",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
origins = settings.BACKEND_CORS_ORIGINS.split(",") if settings.BACKEND_CORS_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/admin/users", tags=["Admin - Users"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(settings_route.router, prefix="/api/admin/settings", tags=["Admin - Settings"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(mlops_route.router, prefix="/api/mlops", tags=["MLOps"])
app.include_router(ws_router)
