"""add market scanner fields to trading_config

Revision ID: 003
Revises: 002
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # auto_discover_markets — active la découverte automatique des paires
    op.add_column(
        "trading_config",
        sa.Column("auto_discover_markets", sa.Boolean(), nullable=False, server_default="0"),
    )
    # max_concurrent_positions — nombre max de positions ouvertes simultanément
    op.add_column(
        "trading_config",
        sa.Column("max_concurrent_positions", sa.Integer(), nullable=False, server_default="3"),
    )
    # quote_currency — devise de cotation pour le filtrage (ex: USD, EUR)
    op.add_column(
        "trading_config",
        sa.Column("quote_currency", sa.String(length=10), nullable=False, server_default="USD"),
    )
    # min_volume_24h — volume minimum 24h pour être candidat
    op.add_column(
        "trading_config",
        sa.Column("min_volume_24h", sa.Float(), nullable=False, server_default="10000.0"),
    )
    # scanner_cache_ttl — TTL du cache du scanner en secondes
    op.add_column(
        "trading_config",
        sa.Column("scanner_cache_ttl", sa.Integer(), nullable=False, server_default="300"),
    )


def downgrade() -> None:
    op.drop_column("trading_config", "scanner_cache_ttl")
    op.drop_column("trading_config", "min_volume_24h")
    op.drop_column("trading_config", "quote_currency")
    op.drop_column("trading_config", "max_concurrent_positions")
    op.drop_column("trading_config", "auto_discover_markets")
