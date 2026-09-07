"""Endpoints FastAPI — module history.

TODO: définir les routes (voir plan, section 6. Controller).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/history", tags=["history"])

# TODO: endpoints (déléguer toute la logique au service, jamais au router)
