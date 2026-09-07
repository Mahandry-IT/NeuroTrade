"""Endpoints FastAPI — module trading_engine.

TODO: définir les routes (voir plan, section 6. Controller).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/trading_engine", tags=["trading_engine"])

# TODO: endpoints (déléguer toute la logique au service, jamais au router)
