"""Endpoints FastAPI — module market_analysis.

TODO: définir les routes (voir plan, section 6. Controller).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/market_analysis", tags=["market_analysis"])

# TODO: endpoints (déléguer toute la logique au service, jamais au router)
