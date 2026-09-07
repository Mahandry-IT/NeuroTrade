"""Endpoints FastAPI — module tax_tracking.

TODO: définir les routes (voir plan, section 6. Controller).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/tax_tracking", tags=["tax_tracking"])

# TODO: endpoints (déléguer toute la logique au service, jamais au router)
