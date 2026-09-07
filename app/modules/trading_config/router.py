"""Endpoints FastAPI — module trading_config.

TODO: définir les routes (voir plan, section 6. Controller).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/trading_config", tags=["trading_config"])

# TODO: endpoints (déléguer toute la logique au service, jamais au router)
