"""Router tax_tracking — compteurs fiscaux + export CSV."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.tax_tracking.service import TaxTrackingService

router = APIRouter(prefix="/tax", tags=["tax_tracking"])


@router.get("/counters")
def get_counters(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = TaxTrackingService(db)
    return service.get_counters(user_id)


@router.get("/export")
def export_csv(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = TaxTrackingService(db)
    return service.export_csv(user_id, date_from, date_to)
