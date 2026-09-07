"""Router history — listing trades + stats performance."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.history.service import HistoryService

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/trades")
def get_trades(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    is_simulated: Optional[bool] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = HistoryService(db)
    from datetime import datetime
    dt_from = datetime.combine(date_from, datetime.min.time()) if date_from else None
    dt_to = datetime.combine(date_to, datetime.max.time()) if date_to else None
    return service.get_trades(user_id, page, limit, is_simulated, dt_from, dt_to, symbol)


@router.get("/stats")
def get_stats(
    is_simulated: Optional[bool] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = HistoryService(db)
    from datetime import datetime
    dt_from = datetime.combine(date_from, datetime.min.time()) if date_from else None
    dt_to = datetime.combine(date_to, datetime.max.time()) if date_to else None
    return service.get_stats(user_id, is_simulated, dt_from, dt_to)
