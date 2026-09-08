"""Point d'entrée FastAPI — Trading Bot IA Backend."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.core.config import settings

# Import des modèles pour que SQLAlchemy les détecte
from app.modules.auth.models import User, PlatformConnection  # noqa: F401
from app.modules.trading_config.models import TradingConfig, BotState  # noqa: F401
from app.modules.market_analysis.models import TechnicalSignal  # noqa: F401
from app.modules.trading_engine.models import Position, Trade  # noqa: F401
from app.modules.notifications.models import Notification  # noqa: F401
from app.modules.tax_tracking.models import TaxableConversion  # noqa: F401

# Import des routers
from app.modules.auth.router import router as auth_router
from app.modules.trading_config.router import router as config_router
from app.modules.trading_engine.router import router as bot_router
from app.modules.history.router import router as history_router
from app.modules.tax_tracking.router import router as tax_router
from app.modules.notifications.router import router as notifications_router
from app.modules.market_scanner.router import router as scanner_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting Trading Bot IA Backend")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning("Could not connect to database on startup: %s", e)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Trading Bot IA — Backend",
    description="Backend Python/FastAPI pour un bot de trading crypto piloté par IA (Gemini free tier).",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routers under /api/v1 ──
app.include_router(auth_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(bot_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")
app.include_router(tax_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(scanner_router, prefix="/api/v1")


@app.get("/health")
def health():
    """Healthcheck — DB status."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}


@app.get("/")
def root():
    return {
        "name": "Trading Bot IA — Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
