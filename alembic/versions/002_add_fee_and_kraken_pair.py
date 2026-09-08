"""add fee to trades + kraken_pair to trading_config

Revision ID: 002
Revises: 001
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Trade.fee — frais Kraken taker pour stats de performance réalistes
    op.add_column("trades", sa.Column("fee", sa.Float(), nullable=False, server_default="0.0"))

    # TradingConfig.kraken_pair — paire de trading (ex: XXBTZUSD)
    op.add_column("trading_config", sa.Column("kraken_pair", sa.String(length=20), nullable=False, server_default="XXBTZUSD"))


def downgrade() -> None:
    op.drop_column("trading_config", "kraken_pair")
    op.drop_column("trades", "fee")
