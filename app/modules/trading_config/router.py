"""Router trading_config — paramètres de trading + contrôle bot."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.trading_config.service import TradingConfigService
from app.modules.trading_engine.service import TradingEngineService
from app.schemas.trading_config import (
    TradingConfigUpdate, TradingConfigResponse,
    BotStatusResponse, BotControlResponse, SimulationModeUpdate,
)

router = APIRouter(prefix="/config", tags=["trading_config"])


@router.get("/trading-params", response_model=TradingConfigResponse)
def get_trading_params(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = TradingConfigService(db)
    return service.get_config(user_id)


@router.put("/trading-params", response_model=TradingConfigResponse)
def update_trading_params(
    body: TradingConfigUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = TradingConfigService(db)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    try:
        return service.update_config(user_id, **update_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.put("/simulation-mode", response_model=dict)
def set_simulation_mode(
    body: SimulationModeUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = TradingConfigService(db)
    try:
        mode = service.set_simulation_mode(user_id, body.simulation_mode, body.confirm)
        return {"simulation_mode": mode, "message": f"Switched to {mode} mode"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
