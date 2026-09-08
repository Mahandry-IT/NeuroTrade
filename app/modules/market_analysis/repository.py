"""Repository market_analysis — signaux techniques calculés."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.modules.market_analysis.models import TechnicalSignal


class MarketAnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_signal(
        self,
        symbol: str,
        rsi: Optional[float] = None,
        macd: Optional[float] = None,
        macd_signal: Optional[float] = None,
        macd_histogram: Optional[float] = None,
        sma_short: Optional[float] = None,
        sma_long: Optional[float] = None,
        ema_short: Optional[float] = None,
        ema_long: Optional[float] = None,
        indicators_raw: Optional[dict] = None,
    ) -> TechnicalSignal:
        signal = TechnicalSignal(
            symbol=symbol,
            rsi=rsi,
            macd=macd,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            sma_short=sma_short,
            sma_long=sma_long,
            ema_short=ema_short,
            ema_long=ema_long,
            indicators_raw=indicators_raw,
        )
        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        return signal

    def get_latest(self, symbol: str) -> Optional[TechnicalSignal]:
        return (
            self.db.query(TechnicalSignal)
            .filter(TechnicalSignal.symbol == symbol)
            .order_by(TechnicalSignal.computed_at.desc())
            .first()
        )
