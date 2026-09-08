"""Repository trading_config — accès données TradingConfig + BotState."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.trading_config.models import TradingConfig, BotState, BotStatus


class TradingConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: int) -> Optional[TradingConfig]:
        return self.db.query(TradingConfig).filter(
            TradingConfig.user_id == user_id
        ).first()

    def get_or_create(self, user_id: int) -> TradingConfig:
        config = self.get_by_user(user_id)
        if not config:
            config = TradingConfig(user_id=user_id)
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def update(self, user_id: int, **kwargs) -> Optional[TradingConfig]:
        config = self.get_by_user(user_id)
        if not config:
            return None
        for key, value in kwargs.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)
        config.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(config)
        return config


class BotStateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: int) -> Optional[BotState]:
        return self.db.query(BotState).filter(BotState.user_id == user_id).first()

    def get_or_create(self, user_id: int) -> BotState:
        state = self.get_by_user(user_id)
        if not state:
            state = BotState(user_id=user_id, status=BotStatus.STOPPED)
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        return state

    def set_running(self, user_id: int) -> BotState:
        state = self.get_or_create(user_id)
        state.status = BotStatus.RUNNING
        state.started_at = datetime.now(timezone.utc)
        state.stopped_at = None
        self.db.commit()
        self.db.refresh(state)
        return state

    def set_stopped(self, user_id: int) -> BotState:
        state = self.get_or_create(user_id)
        state.status = BotStatus.STOPPED
        state.stopped_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(state)
        return state

    def update_last_cycle(self, user_id: int) -> None:
        state = self.get_or_create(user_id)
        state.last_cycle_at = datetime.now(timezone.utc)
        self.db.commit()
