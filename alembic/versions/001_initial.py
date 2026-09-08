"""initial schema — all entities

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Enum("active", "inactive", name="userstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── platform_connections ──
    op.create_table(
        "platform_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("platform_name", sa.String(length=100), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("encrypted_api_secret", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("connected", "disconnected", "error", name="platformconnectionstatus"),
            nullable=True,
        ),
        sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── trading_config ──
    op.create_table(
        "trading_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("gain_limit_pct", sa.Float(), nullable=False),
        sa.Column("loss_limit_pct", sa.Float(), nullable=False),
        sa.Column("capital_pct_per_trade", sa.Float(), nullable=False),
        sa.Column("max_trades_per_month", sa.Integer(), nullable=False),
        sa.Column("min_holding_duration", sa.Integer(), nullable=False),
        sa.Column("tax_alert_threshold", sa.Float(), nullable=False),
        sa.Column("simulation_mode", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # ── bot_state ──
    op.create_table(
        "bot_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "stopped", name="botstatus"),
            nullable=False,
        ),
        sa.Column("last_cycle_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # ── technical_signals ──
    op.create_table(
        "technical_signals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("rsi", sa.Float(), nullable=True),
        sa.Column("macd", sa.Float(), nullable=True),
        sa.Column("macd_signal", sa.Float(), nullable=True),
        sa.Column("macd_histogram", sa.Float(), nullable=True),
        sa.Column("sma_short", sa.Float(), nullable=True),
        sa.Column("sma_long", sa.Float(), nullable=True),
        sa.Column("ema_short", sa.Float(), nullable=True),
        sa.Column("ema_long", sa.Float(), nullable=True),
        sa.Column("indicators_raw", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_technical_signals_symbol", "technical_signals", ["symbol"])

    # ── positions ──
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("open", "closed", name="positionstatus"),
            nullable=False,
        ),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_positions_status", "positions", ["status"])
    op.create_index("ix_positions_symbol", "positions", ["symbol"])
    op.create_index("ix_positions_user_status", "positions", ["user_id", "status"])

    # ── trades ──
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "trade_type",
            sa.Enum("buy", "sell", name="tradetype"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("amount_fiat", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "result",
            sa.Enum("filled", "partially_filled", "cancelled", "failed", "simulated", name="orderresult"),
            nullable=True,
        ),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trades_date", "trades", ["executed_at"])
    op.create_index("ix_trades_simulated", "trades", ["is_simulated"])
    op.create_index("ix_trades_user_date", "trades", ["user_id", "executed_at"])
    op.create_index("ix_trades_idempotency", "trades", ["idempotency_key"], unique=True)

    # ── notifications ──
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "trade_executed", "loss_limit_reached", "gain_limit_reached",
                "monthly_quota_reached", "tax_alert", "bot_stopped",
                "bot_started", "platform_disconnected", "gemini_fallback",
                name="notificationtype",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("in_app", "email", "both", name="notificationchannel"),
            nullable=True,
        ),
        sa.Column("sent", sa.Boolean(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── taxable_conversions ──
    op.create_table(
        "taxable_conversions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trade_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount_fiat", sa.Float(), nullable=False),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_taxable_user_date", "taxable_conversions", ["user_id", "converted_at"])


def downgrade() -> None:
    op.drop_table("taxable_conversions")
    op.drop_table("notifications")
    op.drop_table("trades")
    op.drop_table("positions")
    op.drop_table("technical_signals")
    op.drop_table("bot_state")
    op.drop_table("trading_config")
    op.drop_table("platform_connections")
    op.drop_table("users")
