"""Endpoints FastAPI — module notifications.

TODO: définir les routes (voir plan, section 6. Controller).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["notifications"])

# TODO: endpoints (déléguer toute la logique au service, jamais au router)
