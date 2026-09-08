"""Router trading_engine — contrôle du bot (start/stop/status)."""

import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.trading_config.service import TradingConfigService
from app.modules.trading_engine.service import TradingEngineService
from app.schemas.trading_config import BotControlResponse, BotStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bot", tags=["bot_control"])


@router.post("/start", response_model=BotControlResponse)
def start_bot(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    logger.info("bot_start_requested user_id=%d", user_id)
    config_service = TradingConfigService(db)
    engine_service = TradingEngineService(db)

    try:
        result = config_service.start_bot(user_id, engine_service.run_analysis_cycle)
        return BotControlResponse(**result)
    except ValueError as e:
        logger.warning("bot_start_failed user_id=%d error=%s\n%s", user_id, str(e), traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/stop", response_model=BotControlResponse)
def stop_bot(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    config_service = TradingConfigService(db)
    result = config_service.stop_bot(user_id)
    return BotControlResponse(**result)


@router.get("/status", response_model=BotStatusResponse)
def bot_status(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    config_service = TradingConfigService(db)
    return config_service.get_bot_status(user_id)
