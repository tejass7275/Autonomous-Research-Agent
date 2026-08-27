"""
main.py
FastAPI application entrypoint. Wires together routers, CORS, and startup
DB initialization. Run locally with:
    uvicorn api.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import settings
from api.db.database import init_db
from api.routers import search, summary, papers
from api.routers.history import auth_router, history_router

logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="API powering the Autonomous Research Agent — paper discovery, RAG-based Q&A, and automated summaries.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(papers.router)
app.include_router(search.router)
app.include_router(summary.router)
app.include_router(history_router)


@app.on_event("startup")
def on_startup():
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.ENVIRONMENT)
    init_db()


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}