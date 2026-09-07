"""Entités tax_tracking — TaxableConversion (RG-11)."""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Index

from app.core.database import Base


class TaxableConversion(Base):
    """Enregistre chaque conversion fiat liée à une vente (RG-11)."""
    __tablename__ = "taxable_conversions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_fiat = Column(Float, nullable=False)
    converted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_taxable_user_date", "user_id", "converted_at"),
    )
