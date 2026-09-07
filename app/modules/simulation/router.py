"""Endpoints FastAPI — module simulation.

TODO: définir les routes (voir plan, section 6. Controller).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/simulation", tags=["simulation"])

# TODO: endpoints (déléguer toute la logique au service, jamais au router)
