"""Endpoints FastAPI — module auth.

TODO: définir les routes (voir plan, section 6. Controller).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])

# TODO: endpoints (déléguer toute la logique au service, jamais au router)
